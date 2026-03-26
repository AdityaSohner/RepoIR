import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  HiOutlineMenu,
  HiOutlineSearch,
  HiOutlineBell,
  HiOutlineMoon,
  HiOutlineSun,
  HiOutlineLogout,
  HiOutlineUser,
  HiOutlineCog,
} from 'react-icons/hi';
import { useAuth } from '@/contexts/AuthContext';
import { useApp } from '@/contexts/AppContext';
import { useNavigate } from 'react-router-dom';

interface TopNavProps {
  onMenuClick: () => void;
}

export default function TopNav({ onMenuClick }: TopNavProps) {
  const { user, logout } = useAuth();
  const {
    theme,
    toggleTheme,
    notifications,
    setCommandPaletteOpen,
    setImmersiveSearchOpen,
    markNotificationRead,
    clearNotifications,
    vaultStatus,
  } = useApp();
  const navigate = useNavigate();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const vaultBadge =
    vaultStatus === 'valid'
      ? { color: 'bg-emerald-500', pulse: false }
      : vaultStatus === 'checking'
        ? { color: 'bg-amber-500', pulse: true }
        : vaultStatus === 'unknown'
          ? null
          : { color: 'bg-destructive', pulse: true };

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur-xl">
      <div className="flex items-center justify-between h-16 px-4 lg:px-6">
        {/* Left */}
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 hover:bg-muted rounded-xl transition-colors"
          >
            <HiOutlineMenu className="w-5 h-5" />
          </button>

          <div className="hidden sm:block">
            <h2 className="text-lg font-semibold text-foreground">
              RepoIR
            </h2>
          </div>
        </div>

        {/* Right */}
        <div className="flex items-center gap-2">
          {/* Global Search Button */}
          <button
            onClick={() => setImmersiveSearchOpen(true)}
            className="p-2.5 hover:bg-muted rounded-xl transition-colors hidden sm:block"
            title="Search Vault (⌘K)"
          >
            <HiOutlineSearch className="w-5 h-5 text-muted-foreground" />
          </button>
          {/* Vault status dot */}
          {vaultBadge && (
            <div
              className={`w-2 h-2 rounded-full ${vaultBadge.color} ${vaultBadge.pulse ? 'animate-pulse' : ''
                }`}
              title={`Vault: ${vaultStatus}`}
            />
          )}

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="p-2.5 hover:bg-muted rounded-xl transition-colors"
            id="theme-toggle-topnav"
          >
            {theme === 'dark' ? (
              <HiOutlineSun className="w-5 h-5 text-yellow-400" />
            ) : (
              <HiOutlineMoon className="w-5 h-5" />
            )}
          </button>

          {/* Notifications */}
          <div className="relative">
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className="relative p-2.5 hover:bg-muted rounded-xl transition-colors"
              id="notifications-btn"
            >
              <HiOutlineBell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full animate-pulse bg-primary" />
              )}
            </button>

            <AnimatePresence>
              {showNotifications && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  className="absolute right-0 top-full mt-2 w-80 rounded-2xl shadow-xl border border-border overflow-hidden bg-card z-50"
                >
                  <div className="flex items-center justify-between p-4 border-b border-border">
                    <h3 className="font-semibold text-foreground">
                      Notifications
                    </h3>
                    {notifications.length > 0 && (
                      <button
                        onClick={clearNotifications}
                        className="text-xs text-muted-foreground hover:text-foreground"
                      >
                        Clear all
                      </button>
                    )}
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {notifications.length === 0 ? (
                      <p className="p-4 text-center text-muted-foreground text-sm">
                        No notifications
                      </p>
                    ) : (
                      notifications.slice(0, 10).map((n) => (
                        <div
                          key={n.id}
                          onClick={() => markNotificationRead(n.id)}
                          className={`p-4 border-b border-border last:border-0 cursor-pointer hover:bg-muted/50 transition-colors ${!n.read ? 'bg-primary/5' : ''
                            }`}
                        >
                          <div className="flex items-start gap-2">
                            <span
                              className={`w-2 h-2 rounded-full flex-shrink-0 mt-1.5 ${n.type === 'success'
                                ? 'bg-emerald-500'
                                : n.type === 'error'
                                  ? 'bg-destructive'
                                  : 'bg-primary'
                                }`}
                            />
                            <div>
                              <p className="text-sm text-foreground">
                                {n.message}
                              </p>
                              <p className="text-xs text-muted-foreground mt-1">
                                {new Date(n.timestamp).toLocaleTimeString()}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Profile dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowProfile(!showProfile)}
              className="flex items-center gap-2 p-1.5 hover:bg-muted rounded-xl transition-colors"
              id="profile-menu-btn"
            >
              {user?.avatar ? (
                <img
                  src={user.avatar}
                  alt={user.name}
                  className="w-8 h-8 rounded-lg"
                />
              ) : (
                <div className="w-8 h-8 bg-muted rounded-lg flex items-center justify-center">
                  <HiOutlineUser className="w-4 h-4" />
                </div>
              )}
            </button>

            <AnimatePresence>
              {showProfile && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  className="absolute right-0 top-full mt-2 w-56 rounded-2xl shadow-xl border border-border overflow-hidden bg-card z-50"
                >
                  <div className="p-4 border-b border-border">
                    <p className="font-medium truncate text-foreground">
                      {user?.name}
                    </p>
                    <p className="text-sm text-muted-foreground truncate">
                      {user?.email}
                    </p>
                  </div>
                  <div className="p-2">
                    <button
                      onClick={() => {
                        navigate('/profile');
                        setShowProfile(false);
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-muted transition-colors text-left"
                    >
                      <HiOutlineUser className="w-4 h-4" />
                      <span className="text-sm">Profile</span>
                    </button>
                    <button
                      onClick={() => {
                        navigate('/settings');
                        setShowProfile(false);
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-muted transition-colors text-left"
                    >
                      <HiOutlineCog className="w-4 h-4" />
                      <span className="text-sm">Settings</span>
                    </button>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-destructive/10 text-destructive transition-colors text-left"
                      id="logout-btn"
                    >
                      <HiOutlineLogout className="w-4 h-4" />
                      <span className="text-sm">Logout</span>
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </header>
  );
}
