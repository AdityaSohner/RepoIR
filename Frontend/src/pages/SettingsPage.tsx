import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  HiOutlineLockClosed,
  HiOutlineEye,
  HiOutlineEyeOff,
  HiOutlineCheck,
  HiOutlineRefresh,
  HiOutlineCloudUpload,
  HiOutlineExclamation,
  HiOutlineLink,
} from 'react-icons/hi';
import { FcGoogle } from 'react-icons/fc';
import { useApp } from '@/contexts/AppContext';
import { useAuth } from '@/contexts/AuthContext';
import { apiVaultSync } from '@/lib/api';

const STATUS_CONFIG = {
  valid: {
    label: 'Vault Connected & Ready',
    color: 'text-emerald-500',
    bg: 'bg-emerald-500/10 border-emerald-500/20',
    icon: HiOutlineCheck,
  },
  not_connected: {
    label: 'Drive Not Connected',
    color: 'text-amber-500',
    bg: 'bg-amber-500/10 border-amber-500/20',
    icon: HiOutlineExclamation,
  },
  locked: {
    label: 'Vault Locked — Wrong Password',
    color: 'text-destructive',
    bg: 'bg-destructive/10 border-destructive/20',
    icon: HiOutlineLockClosed,
  },
  invalid: {
    label: 'Invalid Vault Credentials',
    color: 'text-destructive',
    bg: 'bg-destructive/10 border-destructive/20',
    icon: HiOutlineExclamation,
  },
  checking: {
    label: 'Checking status...',
    color: 'text-muted-foreground',
    bg: 'bg-muted/50 border-border',
    icon: HiOutlineRefresh,
  },
  unknown: {
    label: 'Enter your Vault Secret to check',
    color: 'text-muted-foreground',
    bg: 'bg-muted/50 border-border',
    icon: HiOutlineLockClosed,
  },
};

export default function SettingsPage() {
  const {
    vaultPassword,
    setVaultPassword,
    vaultStatus,
    recheckVaultStatus,
    addNotification,
    theme,
    toggleTheme,
  } = useApp();

  const { clientId } = useAuth();

  const [passwordDraft, setPasswordDraft] = useState(vaultPassword);
  const [showPassword, setShowPassword] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const navigate = useNavigate();
  const prevStatus = useRef(vaultStatus);

  useEffect(() => {
    // Only redirect to dashboard when transitioning from a genuinely disconnected
    // state → 'valid'. Do NOT redirect if previous state was 'checking' (which
    // happens on every settings page mount when the vault is already connected).
    const wasDisconnected = ['not_connected', 'invalid', 'locked'].includes(
      prevStatus.current as string
    );
    if (wasDisconnected && vaultStatus === 'valid') {
      navigate('/dashboard');
    }
    prevStatus.current = vaultStatus;
  }, [vaultStatus, navigate]);

  // When the draft changes, update the context
  const applyPassword = () => {
    setVaultPassword(passwordDraft);
    recheckVaultStatus();
  };

  useEffect(() => {
    if (vaultPassword) {
      recheckVaultStatus();
    }
  }, [vaultPassword, recheckVaultStatus]);

  const handleSync = async () => {
    if (!vaultPassword) {
      addNotification('Set your Vault Secret first.', 'error');
      return;
    }
    setSyncing(true);
    try {
      const res = await apiVaultSync(vaultPassword);
      addNotification(
        `Sync complete — ${res.new_files} new file(s) discovered`,
        'success'
      );
    } catch (err: unknown) {
      addNotification(
        `Sync failed: ${err instanceof Error ? err.message : 'Unknown'}`,
        'error'
      );
    } finally {
      setSyncing(false);
    }
  };

  // Open Google OAuth popup to connect Drive
  const handleConnectDrive = () => {
    if (!vaultPassword) {
      addNotification(
        'Set your Vault Secret first, then connect Drive.',
        'error'
      );
      return;
    }

    // Build Google OAuth URL directly (matching repoir-hub logic)
    const redirectUri = `${window.location.origin}/auth/callback`;
    const scope = "https://www.googleapis.com/auth/drive.file";
    // Encode the vault password in the OAuth `state` param — the only reliable
    // way to pass data to the popup since sessionStorage is NOT shared between windows.
    const state = btoa(JSON.stringify({ vaultPassword }));
    const oauthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(
      redirectUri
    )}&response_type=code&scope=${encodeURIComponent(scope)}&access_type=offline&prompt=consent&state=${encodeURIComponent(state)}`;

    // Open in a popup window
    const popup = window.open(
      oauthUrl,
      'gdrive_oauth',
      'width=500,height=600,left=200,top=100'
    );

    // Listen for a message from the popup (set by the redirect page)
    const handleMsg = (ev: MessageEvent) => {
      if (ev.origin !== window.location.origin) return;
      if (ev.data?.type === 'gdrive_callback') {
        popup?.close();
        window.removeEventListener('message', handleMsg);
        if (ev.data.success) {
          recheckVaultStatus();
          addNotification('Google Drive connected successfully!', 'success');
        } else {
          addNotification(`Drive connection failed: ${ev.data.error}`, 'error');
        }
      }
    };
    window.addEventListener('message', handleMsg);
  };

  const statusCfg = STATUS_CONFIG[vaultStatus] || STATUS_CONFIG.unknown;
  const StatusIcon = statusCfg.icon;
  const isConnected = vaultStatus === 'valid';

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold mb-2 text-foreground">Settings</h1>
        <p className="text-muted-foreground">
          Configure your RepoIR vault and preferences
        </p>
      </motion.div>

      {/* ── Vault / Drive Connection ───────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="rounded-2xl border border-border p-6 bg-card space-y-5"
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{
              background:
                'linear-gradient(135deg, hsl(187 92% 45%), hsl(217 91% 55%))',
            }}
          >
            <HiOutlineCloudUpload className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Google Drive Vault</h3>
            <p className="text-sm text-muted-foreground">
              Securely connect your encrypted RepoIR Google Drive storage
            </p>
          </div>
        </div>

        {/* Status badge */}
        <AnimatePresence mode="wait">
          <motion.div
            key={vaultStatus}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={`flex items-center gap-2 px-4 py-3 rounded-xl border ${statusCfg.bg}`}
          >
            <StatusIcon
              className={`w-4 h-4 flex-shrink-0 ${statusCfg.color} ${vaultStatus === 'checking' ? 'animate-spin' : ''
                }`}
            />
            <span className={`text-sm font-medium ${statusCfg.color}`}>
              {statusCfg.label}
            </span>
          </motion.div>
        </AnimatePresence>

        {/* Vault Secret input */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">
            Vault Secret (encryption key)
          </label>
          <p className="text-xs text-muted-foreground/70">
            Stored only in memory for this session — never saved to disk.
          </p>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <HiOutlineLockClosed className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={passwordDraft}
                onChange={(e) => setPasswordDraft(e.target.value)}
                placeholder="Enter your Vault Secret..."
                className="w-full glass-input pl-11 pr-11 py-3 text-foreground placeholder-muted-foreground text-sm"
                id="vault-secret-input"
                onKeyDown={(e) => e.key === 'Enter' && applyPassword()}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showPassword ? (
                  <HiOutlineEyeOff className="w-4 h-4" />
                ) : (
                  <HiOutlineEye className="w-4 h-4" />
                )}
              </button>
            </div>
            <button
              onClick={applyPassword}
              className="btn-primary px-4"
              id="vault-secret-apply"
            >
              Apply
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Connect Drive */}
          <button
            onClick={handleConnectDrive}
            className="flex items-center justify-center gap-3 px-4 py-3 rounded-xl border border-border bg-muted/50 hover:bg-muted transition-all font-medium text-sm"
            id="connect-drive-btn"
          >
            <FcGoogle className="w-5 h-5" />
            {isConnected ? 'Reconnect Drive' : 'Connect Google Drive'}
          </button>

          {/* Sync Vault */}
          <button
            onClick={handleSync}
            disabled={syncing || !vaultPassword}
            className="flex items-center justify-center gap-2 btn-primary py-3 disabled:opacity-50"
            id="sync-vault-btn"
          >
            <HiOutlineRefresh
              className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`}
            />
            {syncing ? 'Syncing...' : 'Sync Vault'}
          </button>
        </div>

        {/* Recheck status */}
        <button
          onClick={recheckVaultStatus}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          id="recheck-vault-btn"
        >
          <HiOutlineRefresh className="w-4 h-4" />
          Recheck Vault Status
        </button>
      </motion.div>

      {/* ── How the Vault Works ───────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="rounded-2xl border border-border p-6 bg-card space-y-4"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-primary/10">
            <HiOutlineLink className="w-5 h-5 text-primary" />
          </div>
          <h3 className="font-semibold text-foreground">
            How the Vault Works
          </h3>
        </div>
        <ol className="space-y-3 text-sm text-muted-foreground list-none">
          {[
            'Enter your Vault Secret — this key encrypts your Google Drive OAuth token at rest.',
            'Click "Connect Google Drive" to link your account. A popup will guide you through Google permissions.',
            'Once connected, upload files via the Dashboard and they\'ll be encrypted and stored in your private "RepoIR_Vault" Drive folder.',
            'Click "Sync Vault" at any time to discover files already in your Drive vault and add them to the search index.',
          ].map((step, i) => (
            <li key={i} className="flex gap-3">
              <span
                className="flex-shrink-0 w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center text-primary-foreground"
                style={{
                  background:
                    'linear-gradient(135deg, hsl(187 92% 45%), hsl(217 91% 55%))',
                }}
              >
                {i + 1}
              </span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </motion.div>

      {/* ── Appearance ───────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="rounded-2xl border border-border p-6 bg-card"
      >
        <h3 className="font-semibold text-foreground mb-4">Appearance</h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-foreground">Theme</p>
            <p className="text-xs text-muted-foreground">
              Currently: {theme === 'dark' ? 'Dark' : 'Light'} mode
            </p>
          </div>
          <button
            onClick={toggleTheme}
            className={`relative w-14 h-7 rounded-full transition-all duration-300 ${theme === 'dark' ? 'bg-primary' : 'bg-muted'
              }`}
            id="theme-toggle"
          >
            <motion.span
              layout
              className="absolute top-1 w-5 h-5 rounded-full bg-white shadow-sm"
              animate={{ left: theme === 'dark' ? 30 : 4 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            />
          </button>
        </div>
      </motion.div>
    </div>
  );
}
