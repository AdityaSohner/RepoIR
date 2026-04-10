import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';
import {
  RepoFile,
  StatsResponse,
  ActivityItem,
  apiGetFiles,
  apiGetStats,
  apiGetActivity,
  apiVaultStatus,
} from '@/lib/api';

// ── Notification ─────────────────────────────────────────────

export interface Notification {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
  timestamp: Date;
  read: boolean;
}

// ── Context type ─────────────────────────────────────────────

interface AppContextType {
  // Files from API
  files: RepoFile[];
  refreshFiles: () => Promise<void>;
  filesLoading: boolean;

  // Stats from API
  stats: StatsResponse | null;
  refreshStats: () => Promise<void>;

  // Activity feed
  activity: ActivityItem[];
  refreshActivity: () => Promise<void>;

  // Vault / Drive connection
  vaultPassword: string;
  setVaultPassword: (pw: string) => void;
  vaultStatus: 'valid' | 'not_connected' | 'locked' | 'invalid' | 'checking' | 'unknown';
  recheckVaultStatus: () => Promise<void>;

  // Notifications
  notifications: Notification[];
  addNotification: (message: string, type: Notification['type']) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;

  // Theme
  theme: 'light' | 'dark';
  toggleTheme: () => void;

  // Modals
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
  immersiveSearchOpen: boolean;
  setImmersiveSearchOpen: (open: boolean) => void;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [files, setFiles] = useState<RepoFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [immersiveSearchOpen, setImmersiveSearchOpen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('repoir_theme') as 'light' | 'dark') || 'dark';
  });

  // Vault password stored ONLY in sessionStorage (transient)
  const [vaultPassword, _setVaultPasswordState] = useState<string>(() => {
    return sessionStorage.getItem('repoir_vault_password') || '';
  });
  const [vaultStatus, setVaultStatus] = useState<AppContextType['vaultStatus']>('unknown');

  // ── Theme ──
  useEffect(() => {
    localStorage.setItem('repoir_theme', theme);
  }, [theme]);

  // ── Keyboard shortcut for command palette ──
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setImmersiveSearchOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setCommandPaletteOpen(false);
        setImmersiveSearchOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const setVaultPassword = useCallback((pw: string) => {
    _setVaultPasswordState(pw);
    // Store in sessionStorage — NOT localStorage
    sessionStorage.setItem('repoir_vault_password', pw);
  }, []);

  // ── API refresh functions ──

  const refreshFiles = useCallback(async () => {
    // Only fetch if a token exists (user logged in)
    const token = sessionStorage.getItem('repoir_token');
    if (!token) return;
    setFilesLoading(true);
    try {
      const res = await apiGetFiles();
      setFiles(res.files);
    } catch (err) {
      console.error('Failed to load files:', err);
    } finally {
      setFilesLoading(false);
    }
  }, []);

  const refreshStats = useCallback(async () => {
    const token = sessionStorage.getItem('repoir_token');
    if (!token) return;
    try {
      const res = await apiGetStats();
      setStats(res);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }, []);

  const refreshActivity = useCallback(async () => {
    const token = sessionStorage.getItem('repoir_token');
    if (!token) return;
    try {
      const res = await apiGetActivity();
      setActivity(res.activity);
    } catch (err) {
      console.error('Failed to load activity:', err);
    }
  }, []);

  const recheckVaultStatus = useCallback(async () => {
    // If no password, we definitely can't check/unlock.
    if (!vaultPassword) {
      setVaultStatus('not_connected');
      return;
    }

    setVaultStatus('checking');
    try {
      const res = await apiVaultStatus(vaultPassword);
      setVaultStatus(res.status);

      // If valid, proactively refresh files and stats to ensure dashboard is ready
      if (res.status === 'valid') {
        refreshFiles();
        refreshStats();
      }
    } catch (err) {
      // Distinguish between a network/server error (backend unreachable or sleeping)
      // and an actual invalid-credentials response. The API returns a non-ok response
      // with a message for bad credentials; a fetch() rejection means network failure.
      const message = err instanceof Error ? err.message.toLowerCase() : '';
      const isCredentialsError =
        message.includes('invalid') ||
        message.includes('unauthorized') ||
        message.includes('403') ||
        message.includes('401');

      console.error('Vault status check failed:', err);
      setVaultStatus(isCredentialsError ? 'invalid' : 'not_connected');
    }
  }, [vaultPassword, refreshFiles, refreshStats]);

  // ── Notifications ──

  const addNotification = useCallback(
    (message: string, type: Notification['type']) => {
      const notif: Notification = {
        id: crypto.randomUUID(),
        message,
        type,
        timestamp: new Date(),
        read: false,
      };
      setNotifications((prev) => [notif, ...prev].slice(0, 20));
    },
    []
  );

  const markNotificationRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const clearNotifications = useCallback(() => setNotifications([]), []);
  const toggleTheme = useCallback(
    () => setTheme((t) => (t === 'light' ? 'dark' : 'light')),
    []
  );

  return (
    <AppContext.Provider
      value={{
        files,
        refreshFiles,
        filesLoading,
        stats,
        refreshStats,
        activity,
        refreshActivity,
        vaultPassword,
        setVaultPassword,
        vaultStatus,
        recheckVaultStatus,
        notifications,
        addNotification,
        markNotificationRead,
        clearNotifications,
        theme,
        toggleTheme,
        commandPaletteOpen,
        setCommandPaletteOpen,
        immersiveSearchOpen,
        setImmersiveSearchOpen,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
