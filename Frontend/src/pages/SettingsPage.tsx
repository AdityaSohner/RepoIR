import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  HiOutlineCheck,
  HiOutlineCloudUpload,
  HiOutlineLink,
} from 'react-icons/hi';
import { FcGoogle } from 'react-icons/fc';
import { FaDropbox } from 'react-icons/fa';
import { useApp } from '@/contexts/AppContext';
import { useAuth } from '@/contexts/AuthContext';
import {
  apiDropboxConnect,
  apiOneDriveConnect,
  apiGetStorageStatus,
  apiDisconnectStorage,
  StorageStatusResponse
} from '@/lib/api';

export default function SettingsPage() {
  const { addNotification, theme, toggleTheme } = useApp();
  const { clientId } = useAuth();
  const [storageStatus, setStorageStatus] = useState<StorageStatusResponse | null>(null);

  const fetchStorageInfo = async () => {
    try {
      const res = await apiGetStorageStatus();
      setStorageStatus(res);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchStorageInfo();
  }, []);

  const isProviderConnected = (provider: string): boolean => {
    if (!storageStatus) return false;
    const providers = (storageStatus as any).providers;
    if (providers && providers[provider]) {
      return providers[provider].connected;
    }
    return storageStatus.connected && storageStatus.provider === provider;
  };

  const handleConnectDrive = () => {
    const redirectUri = `${window.location.origin}/auth/callback`;
    const scope = "https://www.googleapis.com/auth/drive.file";
    const oauthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(
      redirectUri
    )}&response_type=code&scope=${encodeURIComponent(scope)}&access_type=offline&prompt=consent`;

    const popup = window.open(
      oauthUrl,
      'gdrive_oauth',
      'width=500,height=600,left=200,top=100'
    );

    const handleMsg = (ev: MessageEvent) => {
      if (ev.origin !== window.location.origin) return;
      if (ev.data?.type === 'gdrive_callback') {
        popup?.close();
        window.removeEventListener('message', handleMsg);
        if (ev.data.success) {
          fetchStorageInfo();
          addNotification('Google Drive connected successfully!', 'success');
        } else {
          addNotification(`Drive connection failed: ${ev.data.error}`, 'error');
        }
      }
    };
    window.addEventListener('message', handleMsg);
  };

  const handleConnectDropbox = async () => {
    try {
      const redirectUri = `${window.location.origin}/storage/dropbox/callback`;
      const res = await apiDropboxConnect(redirectUri);
      const popup = window.open(res.auth_url, 'dropbox_oauth', 'width=500,height=600,left=200,top=100');

      const handleMsg = (ev: MessageEvent) => {
        if (ev.origin !== window.location.origin) return;
        if (ev.data?.type === 'dropbox_callback') {
          popup?.close();
          window.removeEventListener('message', handleMsg);
          if (ev.data.success) {
            fetchStorageInfo();
            addNotification('Dropbox connected successfully!', 'success');
          } else {
            addNotification(`Dropbox connection failed: ${ev.data.error}`, 'error');
          }
        }
      };
      window.addEventListener('message', handleMsg);
    } catch (err: unknown) {
      addNotification(`Dropbox error: ${err instanceof Error ? err.message : 'Unknown'}`, 'error');
    }
  };

  const handleConnectOneDrive = async () => {
    try {
      const redirectUri = `${window.location.origin}/storage/onedrive/callback`;
      const res = await apiOneDriveConnect(redirectUri);
      const popup = window.open(res.auth_url, 'onedrive_oauth', 'width=500,height=600,left=200,top=100');

      const handleMsg = (ev: MessageEvent) => {
        if (ev.origin !== window.location.origin) return;
        if (ev.data?.type === 'onedrive_callback') {
          popup?.close();
          window.removeEventListener('message', handleMsg);
          if (ev.data.success) {
            fetchStorageInfo();
            addNotification('OneDrive connected successfully!', 'success');
          } else {
            addNotification(`OneDrive connection failed: ${ev.data.error}`, 'error');
          }
        }
      };
      window.addEventListener('message', handleMsg);
    } catch (err: unknown) {
      addNotification(`OneDrive error: ${err instanceof Error ? err.message : 'Unknown'}`, 'error');
    }
  };

  const handleDisconnectStorage = async (provider: string) => {
    try {
      await apiDisconnectStorage(provider);
      fetchStorageInfo();
      addNotification(`${provider.replace('_', ' ')} disconnected.`, 'success');
    } catch (err: unknown) {
      addNotification(`Disconnect failed: ${err instanceof Error ? err.message : 'Unknown'}`, 'error');
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold mb-2 text-foreground">Settings</h1>
        <p className="text-muted-foreground">
          Manage your cloud storage connections and application preferences
        </p>
      </motion.div>

      {/* ── Storage Providers ─────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="rounded-2xl border border-border p-6 bg-card space-y-5"
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, hsl(187 92% 45%), hsl(217 91% 55%))' }}
          >
            <HiOutlineCloudUpload className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Cloud Storage Connections</h3>
            <p className="text-sm text-muted-foreground">
              Connect your cloud storage providers to automatically index and search your files
            </p>
          </div>
        </div>

        {/* Provider Cards List */}
        <div className="grid grid-cols-1 gap-4">
          {/* Google Drive */}
          <div className={`flex items-center justify-between p-4 rounded-xl border transition-all ${
            isProviderConnected('google_drive') ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-border bg-muted/20'
          }`}>
            <div className="flex items-center gap-3">
              <FcGoogle className="w-7 h-7" />
              <div>
                <p className="text-sm font-medium text-foreground">Google Drive</p>
                <p className="text-xs text-muted-foreground">OAuth connected & encrypted automatically</p>
              </div>
            </div>
            {isProviderConnected('google_drive') ? (
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-emerald-500 bg-emerald-500/10 px-3 py-1 rounded-full flex items-center gap-1">
                  <HiOutlineCheck className="w-3.5 h-3.5" /> Connected
                </span>
                <button
                  onClick={() => handleDisconnectStorage('google_drive')}
                  className="text-xs text-muted-foreground hover:text-destructive px-2 py-1 transition-colors"
                  id="disconnect-gdrive-btn"
                >
                  Disconnect
                </button>
              </div>
            ) : (
              <button
                onClick={handleConnectDrive}
                className="text-xs font-medium px-4 py-2 rounded-lg btn-primary"
                id="connect-drive-btn"
              >
                Connect
              </button>
            )}
          </div>

          {/* Dropbox */}
          <div className={`flex items-center justify-between p-4 rounded-xl border transition-all ${
            isProviderConnected('dropbox') ? 'border-[#0061FE]/30 bg-[#0061FE]/5' : 'border-border bg-muted/20'
          }`}>
            <div className="flex items-center gap-3">
              <FaDropbox className="w-7 h-7 text-[#0061FE]" />
              <div>
                <p className="text-sm font-medium text-foreground">Dropbox</p>
                <p className="text-xs text-muted-foreground">OAuth connected & encrypted automatically</p>
              </div>
            </div>
            {isProviderConnected('dropbox') ? (
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-[#0061FE] bg-[#0061FE]/10 px-3 py-1 rounded-full flex items-center gap-1">
                  <HiOutlineCheck className="w-3.5 h-3.5" /> Connected
                </span>
                <button
                  onClick={() => handleDisconnectStorage('dropbox')}
                  className="text-xs text-muted-foreground hover:text-destructive px-2 py-1 transition-colors"
                  id="disconnect-dropbox-btn"
                >
                  Disconnect
                </button>
              </div>
            ) : (
              <button
                onClick={handleConnectDropbox}
                className="text-xs font-medium px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors"
                id="connect-dropbox-btn"
              >
                Connect
              </button>
            )}
          </div>

          {/* OneDrive */}
          <div className={`flex items-center justify-between p-4 rounded-xl border transition-all ${
            isProviderConnected('onedrive') ? 'border-[#0078D4]/30 bg-[#0078D4]/5' : 'border-border bg-muted/20'
          }`}>
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-lg bg-[#0078D4] flex items-center justify-center">
                <span className="text-white text-xs font-bold">O</span>
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">OneDrive</p>
                <p className="text-xs text-muted-foreground">Microsoft OAuth connected & encrypted automatically</p>
              </div>
            </div>
            {isProviderConnected('onedrive') ? (
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-[#0078D4] bg-[#0078D4]/10 px-3 py-1 rounded-full flex items-center gap-1">
                  <HiOutlineCheck className="w-3.5 h-3.5" /> Connected
                </span>
                <button
                  onClick={() => handleDisconnectStorage('onedrive')}
                  className="text-xs text-muted-foreground hover:text-destructive px-2 py-1 transition-colors"
                  id="disconnect-onedrive-btn"
                >
                  Disconnect
                </button>
              </div>
            ) : (
              <button
                onClick={handleConnectOneDrive}
                className="text-xs font-medium px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors"
                id="connect-onedrive-btn"
              >
                Connect
              </button>
            )}
          </div>
        </div>
      </motion.div>

      {/* ── Security Information ──────────────────────────── */}
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
            Automatic Zero-Knowledge Protection
          </h3>
        </div>
        <ol className="space-y-3 text-sm text-muted-foreground list-none">
          {[
            'Select any storage provider and authorize with OAuth in one click.',
            'RepoIR automatically generates and manages AES-256 encryption keys server-side.',
            'Your OAuth credentials and tokens are encrypted at rest with zero manual password entry.',
            'You can connect multiple cloud providers to the same RepoIR account seamlessly.',
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
