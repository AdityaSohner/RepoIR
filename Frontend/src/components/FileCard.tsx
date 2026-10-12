import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  HiOutlinePhotograph,
  HiOutlineDocument,
  HiOutlinePencil,
  HiOutlineLink,
  HiOutlineExternalLink,
  HiOutlineVolumeUp,
  HiOutlineVideoCamera,
  HiDotsVertical,
  HiOutlineShare,
  HiOutlineTrash,
} from 'react-icons/hi';
import { RepoFile, formatFileSize } from '@/lib/api';

interface FileCardProps {
  file: RepoFile;
  onPreview: () => void;
  onDelete?: (file: RepoFile) => void;
  onShare?: (file: RepoFile) => void;
  index: number;
  view?: 'grid' | 'list';
}

// Map backend "type" to icon + color
const typeStyles: Record<
  string,
  { icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>; bg: string; color: string }
> = {
  image: {
    icon: HiOutlinePhotograph,
    bg: 'hsl(330 80% 55% / 0.12)',
    color: 'hsl(330 80% 60%)',
  },
  document: {
    icon: HiOutlineDocument,
    bg: 'hsl(35 90% 55% / 0.12)',
    color: 'hsl(35 90% 60%)',
  },
  text: {
    icon: HiOutlinePencil,
    bg: 'hsl(217 91% 55% / 0.12)',
    color: 'hsl(217 91% 60%)',
  },
  url: {
    icon: HiOutlineLink,
    bg: 'hsl(187 92% 55% / 0.12)',
    color: 'hsl(187 92% 55%)',
  },
  audio: {
    icon: HiOutlineVolumeUp,
    bg: 'hsl(262 83% 58% / 0.12)',
    color: 'hsl(262 83% 60%)',
  },
  video: {
    icon: HiOutlineVideoCamera,
    bg: 'hsl(187 92% 55% / 0.12)',
    color: 'hsl(187 92% 55%)',
  },
};

export default function FileCard({ file, onPreview, onDelete, onShare, index, view = 'grid' }: FileCardProps) {
  const style = typeStyles[file.type] || typeStyles.document;
  const Icon = style.icon;

  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [menuOpen]);

  const handleCardClick = () => {
    if (file.type === 'url' && file.file_path) {
      window.open(file.file_path, '_blank');
    } else {
      onPreview();
    }
  };

  const openInCloud = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (file.type === 'url') {
      const raw = file.source || file.web_url || file.file_path || '';
      const urlToOpen = raw ? (/^https?:\/\//i.test(raw) ? raw : `https://${raw}`) : '';
      if (urlToOpen) window.open(urlToOpen, '_blank');
      return;
    }
    const provider = file.provider || 'google_drive';
    let url = file.web_url;

    // Dropbox always uses exact filename path structure to prevent redirect loops
    if (provider === 'dropbox') {
      const fname = (file.file_path || file.source || '').split('/').pop()?.split('\\').pop();
      if (fname) {
        url = `https://www.dropbox.com/preview/Apps/RepoIR_Vault/RepoIR_Vault/${fname}?role=personal`;
      }
    }

    if (!url && file.file_path) {
      if (provider === 'onedrive') {
        url = 'https://onedrive.live.com';
      } else {
        url = `https://drive.google.com/file/d/${file.file_path}/view`;
      }
    }
    if (url) window.open(url, '_blank');
  };

  const renderActionMenu = () => (
    <div className="relative z-50" ref={menuRef}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setMenuOpen(!menuOpen);
        }}
        className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-muted text-muted-foreground hover:text-foreground focus:opacity-100"
        title="More actions"
      >
        <HiDotsVertical className="w-4 h-4" />
      </button>

      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -5 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -5 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 bottom-full mb-1 w-44 rounded-xl bg-card border border-border shadow-2xl z-50 py-1 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 1. Open in new tab (Drive-dependent preview redirect) */}
            <button
              onClick={(e) => {
                setMenuOpen(false);
                openInCloud(e);
              }}
              className="w-full px-3 py-2 text-xs font-medium flex items-center gap-2.5 text-foreground hover:bg-muted transition-colors text-left"
            >
              <HiOutlineExternalLink className="w-4 h-4 text-muted-foreground" />
              <span>Open in new tab</span>
            </button>

            {/* 2. Share */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen(false);
                if (onShare) onShare(file);
              }}
              className="w-full px-3 py-2 text-xs font-medium flex items-center gap-2.5 text-foreground hover:bg-muted transition-colors text-left"
            >
              <HiOutlineShare className="w-4 h-4 text-muted-foreground" />
              <span>Share</span>
            </button>

            <div className="my-1 border-t border-border/60" />

            {/* 3. Delete */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen(false);
                if (onDelete) onDelete(file);
              }}
              className="w-full px-3 py-2 text-xs font-medium flex items-center gap-2.5 text-red-500 hover:bg-red-500/10 transition-colors text-left"
            >
              <HiOutlineTrash className="w-4 h-4 text-red-500" />
              <span>Delete</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );

  if (view === 'list') {
    return (
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: index * 0.02 }}
        className={`flex items-center gap-4 p-3 rounded-xl border border-border bg-card/60 hover:bg-muted/50 hover:border-primary/40 transition-all cursor-pointer group relative ${menuOpen ? 'z-50' : 'z-0'}`}
        onClick={handleCardClick}
      >
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: style.bg }}
        >
          {file.icon_url ? (
            <img src={file.icon_url} alt={file.type} className="w-5 h-5 object-contain" />
          ) : (
            <Icon className="w-5 h-5" style={{ color: style.color }} />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium truncate text-foreground">{file.source}</h3>
          <p className="text-xs text-muted-foreground">
            {formatFileSize(file.file_size)} • {file.file_type.replace('.', '').toUpperCase()}
          </p>
        </div>

        <div className="flex items-center gap-3 pr-2">
          <span className="tag-badge hidden sm:inline-block" style={{ background: style.bg, color: style.color }}>
            {file.type}
          </span>
          {renderActionMenu()}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className={`file-card group relative ${menuOpen ? 'z-50' : 'z-0'}`}
      onClick={handleCardClick}
    >
      {/* Square Thumbnail/Icon area (1:1) */}
      <div className="w-full aspect-square rounded-xl overflow-hidden mb-4 bg-muted/40 relative group-hover:bg-muted/60 transition-all duration-300">
        {/* Fallback Icon (Z-index 0) */}
        <div className="w-full h-full flex flex-col items-center justify-center gap-2 absolute inset-0 z-0">
          {file.icon_url ? (
            <img
              src={file.icon_url}
              alt={file.type}
              className="w-12 h-12 object-contain"
            />
          ) : (
            <Icon className="w-12 h-12" style={{ color: style.color }} />
          )}
          <span className="text-[10px] font-bold uppercase tracking-wider opacity-40" style={{ color: style.color }}>
            {file.file_type.replace('.', '')}
          </span>
        </div>

        {/* Thumbnail Content (Z-index 10) */}
        {(file.thumbnail_url || (file.file_path && file.type !== 'url')) && (
          <div className="absolute inset-0 z-10 bg-white overflow-hidden rounded-xl transition-transform duration-500 group-hover:scale-105 pointer-events-none">
            {file.thumbnail_url ? (
              <img
                src={file.thumbnail_url}
                alt={file.source}
                className="w-full h-full object-cover"
                loading="lazy"
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                }}
              />
            ) : (file.type === 'document' && file.provider === 'google_drive' && file.file_path) ? (
              // Only embed GDrive preview for GDrive-stored files
              <iframe
                src={`https://drive.google.com/file/d/${file.file_path}/preview`}
                className="border-0 bg-white absolute"
                style={{
                  width: '300%',
                  height: '300%',
                  transform: 'scale(0.333)',
                  transformOrigin: '0 0',
                  top: '-18px'
                }}
                scrolling="no"
                tabIndex={-1}
              />
            ) : null}
          </div>
        )}
      </div>

      <h3
        className="font-medium truncate mb-1 text-foreground"
        title={file.source}
      >
        {file.source}
      </h3>

      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
        <span>{formatFileSize(file.file_size)}</span>
        <span>•</span>
        <span className="uppercase text-xs">{file.file_type.replace('.', '')}</span>
      </div>

      <div className="flex items-center justify-between">
        <span
          className="tag-badge"
          style={{ background: style.bg, color: style.color }}
        >
          {file.type}
        </span>
        {renderActionMenu()}
      </div>
    </motion.div>
  );
}
