import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FcGoogle } from 'react-icons/fc';
import { FaDropbox } from 'react-icons/fa';
import { HiOutlineCheckCircle, HiOutlineShieldCheck, HiOutlineSparkles, HiOutlineCloud } from 'react-icons/hi';
import { useAuth } from '@/contexts/AuthContext';
import { useApp } from '@/contexts/AppContext';
import { apiGetStorageStatus, apiDropboxConnect, apiOneDriveConnect, StorageStatusResponse } from '@/lib/api';

export default function OnboardingPage() {
  const { clientId, user } = useAuth();
  const { addNotification } = useApp();
  const navigate = useNavigate();

  const [isConnecting, setIsConnecting] = useState(false);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);

  useEffect(() => {
    // Check if user already has a storage connection
    apiGetStorageStatus()
      .then((status: StorageStatusResponse) => {
        if (status.connected) {
          navigate('/dashboard', { replace: true });
        }
      })
      .catch(() => {});
  }, [navigate]);

  const handleConnectDrive = () => {
    setIsConnecting(true);
    setConnectingProvider('google_drive');

    const redirectUri = `${window.location.origin}/auth/callback`;
    const scope = "https://www.googleapis.com/auth/drive.file";
    const oauthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(
      redirectUri
    )}&response_type=code&scope=${encodeURIComponent(scope)}&access_type=offline&prompt=consent`;

    const popup = window.open(oauthUrl, 'gdrive_oauth', 'width=520,height=620,left=200,top=100');

    const handleMsg = (ev: MessageEvent) => {
      if (ev.origin !== window.location.origin) return;
      if (ev.data?.type === 'gdrive_callback') {
        popup?.close();
        window.removeEventListener('message', handleMsg);
        setIsConnecting(false);
        setConnectingProvider(null);

        if (ev.data.success) {
          addNotification('Google Drive connected successfully!', 'success');
          navigate('/dashboard', { replace: true });
        } else {
          addNotification(`Google Drive connection failed: ${ev.data.error}`, 'error');
        }
      }
    };
    window.addEventListener('message', handleMsg);
  };

  const handleConnectDropbox = async () => {
    setIsConnecting(true);
    setConnectingProvider('dropbox');

    try {
      const redirectUri = `${window.location.origin}/storage/dropbox/callback`;
      const res = await apiDropboxConnect(redirectUri);
      const popup = window.open(res.auth_url, 'dropbox_oauth', 'width=520,height=620,left=200,top=100');

      const handleMsg = (ev: MessageEvent) => {
        if (ev.origin !== window.location.origin) return;
        if (ev.data?.type === 'dropbox_callback') {
          popup?.close();
          window.removeEventListener('message', handleMsg);
          setIsConnecting(false);
          setConnectingProvider(null);

          if (ev.data.success) {
            addNotification('Dropbox connected successfully!', 'success');
            navigate('/dashboard', { replace: true });
          } else {
            addNotification(`Dropbox connection failed: ${ev.data.error}`, 'error');
          }
        }
      };
      window.addEventListener('message', handleMsg);
    } catch (err: unknown) {
      setIsConnecting(false);
      setConnectingProvider(null);
      addNotification(`Failed to initiate Dropbox connection: ${err instanceof Error ? err.message : 'Unknown error'}`, 'error');
    }
  };

  const handleConnectOneDrive = async () => {
    setIsConnecting(true);
    setConnectingProvider('onedrive');

    try {
      const redirectUri = `${window.location.origin}/v1/storage/onedrive/callback`;
      const res = await apiOneDriveConnect(redirectUri);
      const popup = window.open(res.auth_url, 'onedrive_oauth', 'width=520,height=620,left=200,top=100');

      const handleMsg = (ev: MessageEvent) => {
        if (ev.origin !== window.location.origin) return;
        if (ev.data?.type === 'onedrive_callback') {
          popup?.close();
          window.removeEventListener('message', handleMsg);
          setIsConnecting(false);
          setConnectingProvider(null);

          if (ev.data.success) {
            addNotification('OneDrive connected successfully!', 'success');
            navigate('/dashboard', { replace: true });
          } else {
            addNotification(`OneDrive connection failed: ${ev.data.error}`, 'error');
          }
        }
      };
      window.addEventListener('message', handleMsg);
    } catch (err: unknown) {
      setIsConnecting(false);
      setConnectingProvider(null);
      addNotification(`Failed to initiate OneDrive connection: ${err instanceof Error ? err.message : 'Unknown error'}`, 'error');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background relative overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-32 -left-32 w-[600px] h-[600px] rounded-full blur-[140px] bg-primary/10" />
        <div className="absolute -bottom-32 -right-32 w-[600px] h-[600px] rounded-full blur-[140px] bg-cyan-500/10" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 25 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-2xl"
      >
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center p-3 bg-primary/10 rounded-2xl mb-4 text-primary ring-1 ring-primary/20">
            <HiOutlineSparkles className="w-8 h-8" />
          </div>
          <h1 className="text-3xl font-extrabold text-foreground tracking-tight mb-2">
            Connect Your Cloud Storage
          </h1>
          <p className="text-muted-foreground max-w-md mx-auto">
            Welcome, <span className="font-semibold text-foreground">{user?.email || 'User'}</span>! Choose your preferred cloud provider to connect to RepoIR.
          </p>
        </div>

        <div className="glass-card p-8 rounded-3xl space-y-6 border border-border/50 shadow-2xl">
          {/* Transparent Security Notice */}
          <div className="bg-card/50 border border-border p-4 rounded-2xl space-y-1">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <HiOutlineShieldCheck className="w-5 h-5 text-emerald-500" />
              <span>Zero-Knowledge Server-Managed Encryption</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              RepoIR automatically secures your OAuth credentials and tokens with AES-256 server encryption. No passwords or secret keys required.
            </p>
          </div>

          {/* Provider Selection Options */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-muted-foreground">Select a Storage Provider</h3>

            {/* Google Drive Option */}
            <motion.div
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              onClick={handleConnectDrive}
              className={`flex items-center justify-between p-5 rounded-2xl border cursor-pointer transition-all ${
                connectingProvider === 'google_drive'
                  ? 'bg-primary/10 border-primary'
                  : 'bg-card/40 border-border/80 hover:border-primary/50 hover:bg-card/80'
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center border border-white/20 shadow-inner">
                  <FcGoogle className="w-7 h-7" />
                </div>
                <div>
                  <h4 className="font-semibold text-foreground text-base">Google Drive</h4>
                  <p className="text-xs text-muted-foreground">Store and index files directly from your Google Drive</p>
                </div>
              </div>
              <button
                disabled={isConnecting}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-md disabled:opacity-50"
              >
                {connectingProvider === 'google_drive' ? 'Connecting...' : 'Connect'}
              </button>
            </motion.div>

            {/* Dropbox Option */}
            <motion.div
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              onClick={handleConnectDropbox}
              className={`flex items-center justify-between p-5 rounded-2xl border cursor-pointer transition-all ${
                connectingProvider === 'dropbox'
                  ? 'bg-primary/10 border-primary'
                  : 'bg-card/40 border-border/80 hover:border-primary/50 hover:bg-card/80'
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-blue-600/20 flex items-center justify-center border border-blue-500/30 text-blue-400 shadow-inner">
                  <FaDropbox className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="font-semibold text-foreground text-base">Dropbox</h4>
                  <p className="text-xs text-muted-foreground">Store and index files directly from your Dropbox account</p>
                </div>
              </div>
              <button
                disabled={isConnecting}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition-colors shadow-md disabled:opacity-50"
              >
                {connectingProvider === 'dropbox' ? 'Connecting...' : 'Connect'}
              </button>
            </motion.div>

            {/* OneDrive Option */}
            <motion.div
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              onClick={handleConnectOneDrive}
              className={`flex items-center justify-between p-5 rounded-2xl border cursor-pointer transition-all ${
                connectingProvider === 'onedrive'
                  ? 'bg-primary/10 border-primary'
                  : 'bg-card/40 border-border/80 hover:border-primary/50 hover:bg-card/80'
              }`}
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-sky-600/20 flex items-center justify-center border border-sky-500/30 text-sky-400 shadow-inner">
                  <HiOutlineCloud className="w-6 h-6 text-[#0078D4]" />
                </div>
                <div>
                  <h4 className="font-semibold text-foreground text-base">Microsoft OneDrive</h4>
                  <p className="text-xs text-muted-foreground">Store and index files directly from Microsoft OneDrive</p>
                </div>
              </div>
              <button
                disabled={isConnecting}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-[#0078D4] text-white hover:bg-[#0078D4]/90 transition-colors shadow-md disabled:opacity-50"
              >
                {connectingProvider === 'onedrive' ? 'Connecting...' : 'Connect'}
              </button>
            </motion.div>
          </div>

          <div className="pt-2 text-center">
            <div className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
              <HiOutlineCheckCircle className="w-4 h-4 text-emerald-500" />
              <span>You can connect multiple cloud providers or disconnect anytime in Settings.</span>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
