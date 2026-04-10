import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  HiOutlineHome,
  HiOutlineCog,
  HiOutlineX,
  HiOutlinePhotograph,
  HiOutlineDocument,
  HiOutlinePencil,
  HiOutlineCloudUpload,
  HiOutlineCheck,
  HiOutlineExclamation,
  HiOutlineLockClosed,
  HiOutlineLink,
} from 'react-icons/hi';
import { useApp } from '@/contexts/AppContext';
import { useAuth } from '@/contexts/AuthContext';
import { formatFileSize } from '@/lib/api';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const VAULT_STATUS_CONFIG = {
  valid: {
    label: 'Vault Connected',
    color: 'text-emerald-500',
    icon: HiOutlineCheck,
  },
  not_connected: {
    label: 'Drive Not Connected',
    color: 'text-amber-500',
    icon: HiOutlineExclamation,
  },
  locked: {
    label: 'Vault Locked',
    color: 'text-destructive',
    icon: HiOutlineLockClosed,
  },
  invalid: {
    label: 'Invalid Credentials',
    color: 'text-destructive',
    icon: HiOutlineExclamation,
  },
  checking: {
    label: 'Checking...',
    color: 'text-muted-foreground',
    icon: HiOutlineCloudUpload,
  },
  unknown: {
    label: 'Setup Vault Secret',
    color: 'text-muted-foreground',
    icon: HiOutlineLockClosed,
  },
};

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { stats, vaultStatus } = useApp();
  const { user } = useAuth();

  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 1024);

  useEffect(() => {
    const handleResize = () => setIsDesktop(window.innerWidth >= 1024);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const totalCount = stats
    ? (stats.document?.count ?? 0) +
    (stats.image?.count ?? 0) +
    (stats.text?.count ?? 0)
    : 0;
  const totalSize = stats
    ? (stats.document?.total_size_bytes ?? 0) +
    (stats.image?.total_size_bytes ?? 0) +
    (stats.text?.total_size_bytes ?? 0)
    : 0;

  const vaultCfg = VAULT_STATUS_CONFIG[vaultStatus] || VAULT_STATUS_CONFIG.unknown;
  const VaultIcon = vaultCfg.icon;

  const navItems = [
    {
      label: 'Home',
      path: '/dashboard',
      icon: HiOutlineHome,
    },
    {
      label: 'Settings',
      path: '/settings',
      icon: HiOutlineCog,
    },
  ];

  const typeLinks = [
    {
      label: 'Images',
      type: 'image',
      path: '/dashboard?type=image',
      icon: HiOutlinePhotograph,
      count: stats?.image?.count ?? 0,
      color: 'hsl(330 80% 60%)',
      bg: 'hsl(330 80% 55% / 0.12)',
    },
    {
      label: 'Documents',
      type: 'document',
      path: '/dashboard?type=document',
      icon: HiOutlineDocument,
      count: stats?.document?.count ?? 0,
      color: 'hsl(35 90% 60%)',
      bg: 'hsl(35 90% 55% / 0.12)',
    },
    {
      label: 'Snippets',
      type: 'text',
      path: '/dashboard?type=text',
      icon: HiOutlinePencil,
      count: stats?.text?.count ?? 0,
      color: 'hsl(217 91% 60%)',
      bg: 'hsl(217 91% 55% / 0.12)',
    },
    {
      label: 'URL Collection',
      type: 'url',
      path: '/dashboard?type=url',
      icon: HiOutlineLink,
      count: stats?.url?.count ?? 0,
      color: 'hsl(187 92% 55%)',
      bg: 'hsl(187 92% 55% / 0.12)',
    },
  ];

  const handleNav = (path: string) => {
    navigate(path);
    if (window.innerWidth < 1024) onClose();
  };

  return (
    <>
      {/* Mobile overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="lg:hidden fixed inset-0 z-40 bg-background/60 backdrop-blur-sm"
          />
        )}
      </AnimatePresence>

      <motion.aside
        initial={false}
        animate={{ x: (isDesktop || isOpen) ? 0 : '-100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="fixed lg:sticky top-0 h-screen left-0 z-50 w-72 flex flex-col border-r border-border bg-sidebar lg:translate-x-0"
      >
        {/* Logo */}
        <div className="flex items-center justify-between p-5 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-[88px] h-[88px] flex items-center justify-center flex-shrink-0 overflow-hidden">
              <img src="/logo-no-title.png" alt="RepoIR" className="w-[80px] h-[80px] object-contain translate-y-1" />
            </div>
            <div>
              <span className="text-lg font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500 tracking-tight block leading-tight">
                RepoIR
              </span>
              <span className="text-xs text-muted-foreground">
                The AI Powered Archive
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden text-muted-foreground hover:text-foreground"
          >
            <HiOutlineX className="w-5 h-5" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.path === '/dashboard'
              ? location.pathname === '/dashboard' && !location.search
              : location.pathname === item.path;

            return (
              <div
                key={item.path}
                onClick={() => handleNav(item.path)}
                className={`sidebar-item ${isActive ? 'sidebar-item-active' : ''}`}
              >
                <Icon className="w-5 h-5" />
                <span>{item.label}</span>
              </div>
            );
          })}

          {/* Type filter links */}
          <div className="pt-5 pb-2 px-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Library
            </span>
          </div>

          {typeLinks.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname + location.search === link.path;
            return (
              <div
                key={link.type}
                onClick={() => handleNav(link.path)}
                className={`sidebar-item ${isActive ? 'sidebar-item-active' : ''}`}
              >
                <div
                  className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: link.bg }}
                >
                  <Icon className="w-4 h-4" style={{ color: link.color }} />
                </div>
                <span className="flex-1">{link.label}</span>
                <span
                  className="text-[10px] font-bold px-1.5 py-0.5 rounded-md min-w-[1.5rem] text-center"
                  style={{ background: link.bg, color: link.color }}
                >
                  {link.count}
                </span>
              </div>
            );
          })}
        </nav>

        {/* Vault Status */}
        <div className="p-4 border-t border-border mx-3 my-1 rounded-xl bg-muted/40">
          <div className="flex items-center gap-2 mb-1">
            <VaultIcon
              className={`w-4 h-4 flex-shrink-0 ${vaultCfg.color} ${vaultStatus === 'checking' ? 'animate-pulse' : ''
                }`}
            />
            <span className={`text-xs font-medium ${vaultCfg.color}`}>
              {vaultCfg.label}
            </span>
          </div>
          {totalCount > 0 && (
            <p className="text-xs text-muted-foreground ml-6">
              {totalCount} files · {formatFileSize(totalSize)}
            </p>
          )}
          {(vaultStatus === 'not_connected' || vaultStatus === 'unknown') && (
            <button
              onClick={() => handleNav('/settings')}
              className="ml-6 mt-1 text-xs text-primary hover:underline"
            >
              Setup in Settings →
            </button>
          )}
        </div>

        {/* User profile footer */}
        {user && (
          <div
            className="p-4 border-t border-border flex items-center gap-3 cursor-pointer hover:bg-muted/30 transition-colors"
            onClick={() => handleNav('/profile')}
          >
            <img
              src={user.avatar}
              alt={user.name}
              className="w-9 h-9 rounded-xl flex-shrink-0"
            />
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {user.name}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {user.email}
              </p>
            </div>
          </div>
        )}
      </motion.aside>
    </>
  );
}
