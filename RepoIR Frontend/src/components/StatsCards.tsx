import { useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  HiOutlinePhotograph,
  HiOutlineDocument,
  HiOutlinePencil,
  HiOutlineCollection,
} from 'react-icons/hi';
import { useApp } from '@/contexts/AppContext';
import { formatFileSize } from '@/lib/api';

export default function StatsCards() {
  const { stats, refreshStats } = useApp();

  useEffect(() => {
    refreshStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cards = [
    {
      key: 'total',
      label: 'Total Files',
      icon: HiOutlineCollection,
      gradient: 'linear-gradient(135deg, hsl(187 92% 45%), hsl(217 91% 55%))',
      count: stats
        ? (stats.document?.count ?? 0) +
        (stats.image?.count ?? 0) +
        (stats.text?.count ?? 0)
        : null,
      size: stats
        ? (stats.document?.total_size_bytes ?? 0) +
        (stats.image?.total_size_bytes ?? 0) +
        (stats.text?.total_size_bytes ?? 0)
        : null,
    },
    {
      key: 'images',
      label: 'Images',
      icon: HiOutlinePhotograph,
      gradient:
        'linear-gradient(135deg, hsl(330 80% 55%), hsl(350 80% 55%))',
      count: stats
        ? (stats.image?.count ?? 0)
        : null,
      size: stats
        ? (stats.image?.total_size_bytes ?? 0)
        : null,
    },
    {
      key: 'documents',
      label: 'Documents',
      icon: HiOutlineDocument,
      gradient: 'linear-gradient(135deg, hsl(35 90% 55%), hsl(20 90% 55%))',
      count: stats
        ? (stats.document?.count ?? 0)
        : null,
      size: stats
        ? (stats.document?.total_size_bytes ?? 0)
        : null,
    },
    {
      key: 'text',
      label: 'Snippets',
      icon: HiOutlinePencil,
      gradient:
        'linear-gradient(135deg, hsl(217 91% 55%), hsl(240 70% 55%))',
      count: stats
        ? (stats.text?.count ?? 0)
        : null,
      size: stats
        ? (stats.text?.total_size_bytes ?? 0)
        : null,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {cards.map((card, index) => {
        const Icon = card.icon;
        return (
          <motion.div
            key={card.key}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className="stat-card"
          >
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center mb-3"
              style={{ background: card.gradient }}
            >
              <Icon className="w-5 h-5 text-white" />
            </div>
            {card.count === null ? (
              <div className="w-8 h-6 animate-pulse rounded bg-muted mb-1" />
            ) : (
              <p className="text-2xl font-bold text-foreground">
                {card.count || 0}
              </p>
            )}
            <p className="text-sm text-muted-foreground">{card.label}</p>
            {card.size !== null && card.size > 0 && (
              <p className="text-xs text-muted-foreground/60 mt-0.5">
                {formatFileSize(card.size)}
              </p>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
