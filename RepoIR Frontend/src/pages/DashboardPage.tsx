import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate, useSearchParams, Navigate } from 'react-router-dom';
import { HiOutlineExclamation, HiOutlineCog, HiOutlineSearch } from 'react-icons/hi';
import { useAuth } from '@/contexts/AuthContext';
import { useApp } from '@/contexts/AppContext';
import StatsCards from '@/components/StatsCards';
import UploadZone from '@/components/UploadZone';
import FileGrid from '@/components/FileGrid';

export default function DashboardPage() {
  const { user } = useAuth();
  const { vaultStatus, recheckVaultStatus, vaultPassword, refreshStats, refreshActivity, setImmersiveSearchOpen } =
    useApp();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const getGreeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 18) return 'Good afternoon';
    return 'Good evening';
  };

  // Load data when dashboard mounts
  useEffect(() => {
    if (vaultPassword) recheckVaultStatus();
    refreshStats();
    refreshActivity();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const showVaultAlert =
    vaultStatus === 'not_connected' ||
    vaultStatus === 'unknown' ||
    vaultStatus === 'invalid' ||
    vaultStatus === 'locked';

  useEffect(() => {
    if (showVaultAlert) {
      navigate('/settings', { replace: true });
    }
  }, [showVaultAlert, navigate]);

  if (showVaultAlert) {
    return null;
  }

  const activeType = searchParams.get('type');
  const isHome = !activeType || activeType === 'all';

  return (
    <div className="space-y-6">
      {/* Greeting and Big Search - Only on Home */}
      {isHome && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center justify-center py-12 px-4 text-center">
          <h1 className="text-3xl lg:text-5xl font-extrabold text-foreground mb-4 tracking-tight">
            {getGreeting()},{' '}
            <span
              style={{
                background:
                  'linear-gradient(90deg, hsl(187 92% 55%), hsl(217 91% 65%))',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              {user?.name}
            </span>
          </h1>
          <p className="text-lg text-muted-foreground mb-10 max-w-2xl">
            Welcome to RepoIR. Your entire knowledge base is indexed, semantically searchable, and readily available. Just ask your AI.
          </p>
          
          <button
            onClick={() => setImmersiveSearchOpen(true)}
            className="flex items-center gap-4 px-6 py-5 w-full max-w-3xl rounded-3xl border border-border/50 bg-card/80 backdrop-blur-md hover:bg-muted/80 hover:border-primary/40 transition-all duration-300 shadow-xl group cursor-text"
          >
            <HiOutlineSearch className="w-8 h-8 text-primary/70 group-hover:text-primary transition-colors" />
            <span className="text-xl text-muted-foreground font-medium text-left flex-1">
              Ask AI to find anything in your repository...
            </span>
            <div className="hidden sm:flex items-center gap-2 opacity-50">
              <kbd className="px-3 py-1.5 rounded-lg text-sm font-bold bg-background border border-border shadow-sm">
                ⌘
              </kbd>
              <kbd className="px-3 py-1.5 rounded-lg text-sm font-bold bg-background border border-border shadow-sm">
                K
              </kbd>
            </div>
          </button>
        </motion.div>
      )}

      {/* Stats - Only on Home */}
      {isHome && <StatsCards />}

      {/* Upload Zone - Only on Home */}
      {isHome && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl p-6 border border-border bg-card"
        >
          <h3 className="font-semibold text-foreground mb-4">Add to Vault</h3>
          <UploadZone />
        </motion.div>
      )}

      {/* File Library / Gallery */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className={`rounded-2xl p-6 border border-border bg-card ${!isHome ? 'min-h-[70vh]' : ''}`}
      >
        <FileGrid />
      </motion.div>
    </div>
  );
}
