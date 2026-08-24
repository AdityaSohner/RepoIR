import { useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  HiOutlineMail,
  HiOutlinePhotograph,
  HiOutlineDocument,
  HiOutlinePencil,
  HiOutlineCloudUpload,
  HiOutlineCalendar,
  HiOutlineCollection,
} from 'react-icons/hi';
import { useAuth } from '@/contexts/AuthContext';
import { useApp } from '@/contexts/AppContext';
import { formatFileSize } from '@/lib/api';

export default function ProfilePage() {
  const { user } = useAuth();
  const { stats, activity, refreshStats, refreshActivity } = useApp();

  useEffect(() => {
    refreshStats();
    refreshActivity();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const categoryItems = [
    {
      label: 'Total',
      count: totalCount,
      size: totalSize,
      icon: HiOutlineCollection,
      color: 'hsl(187 92% 55%)',
    },
    {
      label: 'Images',
      count: stats?.image?.count ?? 0,
      size: stats?.image?.total_size_bytes ?? 0,
      icon: HiOutlinePhotograph,
      color: 'hsl(330 80% 55%)',
    },
    {
      label: 'Documents',
      count: stats?.document?.count ?? 0,
      size: stats?.document?.total_size_bytes ?? 0,
      icon: HiOutlineDocument,
      color: 'hsl(35 90% 55%)',
    },
    {
      label: 'Snippets',
      count: stats?.text?.count ?? 0,
      size: stats?.text?.total_size_bytes ?? 0,
      icon: HiOutlinePencil,
      color: 'hsl(217 91% 55%)',
    },
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold mb-2 text-foreground">Profile</h1>
        <p className="text-muted-foreground">
          Manage your account and view your activity
        </p>
      </motion.div>

      {/* Profile Card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="rounded-2xl border border-border p-8 bg-card"
      >
        <div className="flex flex-col sm:flex-row sm:items-start gap-6">
          <div className="relative">
            <img
              src={user?.avatar}
              alt={user?.name}
              className="w-24 h-24 rounded-2xl ring-2 ring-primary/20"
            />
            <div
              className="absolute -bottom-2 -right-2 w-7 h-7 rounded-full flex items-center justify-center"
              style={{
                background:
                  'linear-gradient(135deg, hsl(187 92% 45%), hsl(217 91% 55%))',
              }}
            >
              <span className="text-xs font-bold text-white">✓</span>
            </div>
          </div>
          <div className="flex-1">
            <h2 className="text-2xl font-semibold mb-1 text-foreground">
              {user?.name}
            </h2>
            <p className="text-muted-foreground flex items-center gap-2 mb-1">
              <HiOutlineMail className="w-4 h-4" />
              {user?.email}
            </p>
            <p className="text-muted-foreground flex items-center gap-2 text-sm">
              <HiOutlineCalendar className="w-4 h-4" />
              Member since{' '}
              {new Date().toLocaleDateString('en-US', {
                month: 'long',
                year: 'numeric',
              })}
            </p>
          </div>
        </div>
      </motion.div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {categoryItems.map((item, i) => {
          const Icon = item.icon;
          return (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.04 }}
              className="stat-card text-center"
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3"
                style={{ background: `${item.color}20`, color: item.color }}
              >
                <Icon className="w-5 h-5" />
              </div>
              {stats ? (
                <p className="text-2xl font-bold text-foreground">
                  {item.count}
                </p>
              ) : (
                <div className="w-10 h-7 animate-pulse rounded bg-muted mx-auto mb-1" />
              )}
              <p className="text-xs text-muted-foreground mt-0.5">
                {item.label}
              </p>
              {item.size > 0 && (
                <p className="text-xs text-muted-foreground/60 mt-0.5">
                  {formatFileSize(item.size)}
                </p>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Storage + Activity */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Storage breakdown */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl border border-border p-6 bg-card"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-primary/10 text-primary">
              <HiOutlineCloudUpload className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Storage</h3>
              <p className="text-sm text-muted-foreground">
                {formatFileSize(totalSize)} total
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {categoryItems.slice(1).map((item) => {
              const pct =
                totalSize > 0
                  ? Math.round((item.size / totalSize) * 100)
                  : 0;
              return (
                <div key={item.label}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ background: item.color }}
                      />
                      <span className="text-muted-foreground">
                        {item.label}
                      </span>
                    </div>
                    <span className="text-foreground font-medium">
                      {formatFileSize(item.size)}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.8, delay: 0.3 }}
                      className="h-full rounded-full"
                      style={{ background: item.color }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>

        {/* Activity feed */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="rounded-2xl border border-border p-6 bg-card"
        >
          <h3 className="font-semibold text-foreground mb-4">
            Recent Activity
          </h3>
          {activity.length > 0 ? (
            <div className="space-y-3">
              {activity.slice(0, 8).map((item) => (
                <div
                  key={item.log_id}
                  className="flex items-start gap-3 p-2 rounded-xl hover:bg-muted/50 transition-colors"
                >
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-primary/10 text-primary flex-shrink-0 mt-0.5">
                    <HiOutlineCloudUpload className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate text-foreground">
                      {item.details}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {item.action} ·{' '}
                      {new Date(item.timestamp).toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center py-8">
              {activity.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center">
                  No activity yet. Upload some files to get started!
                </p>
              ) : (
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              )}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
