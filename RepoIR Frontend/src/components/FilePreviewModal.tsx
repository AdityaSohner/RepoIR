import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  HiOutlineX,
  HiOutlineExternalLink,
  HiOutlinePhotograph,
  HiOutlineDocument,
  HiOutlinePencil,
  HiOutlineLink,
} from 'react-icons/hi';
import { RepoFile, getPreviewUrl, formatFileSize } from '@/lib/api';
import { useApp } from '@/contexts/AppContext';

interface FilePreviewModalProps {
  file: RepoFile | null;
  onClose: () => void;
}

// Office formats that need Google Drive viewer
const OFFICE_TYPES = ['.docx', '.pptx', '.xlsx', '.doc', '.ppt', '.xls'];
const IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'];

export default function FilePreviewModal({
  file,
  onClose,
}: FilePreviewModalProps) {
  const { vaultPassword } = useApp();

  if (!file) return null;

  const fileType = file.file_type?.toLowerCase() || '';
  const isImage = IMAGE_TYPES.includes(fileType) || file.type === 'image';
  const isPDF = fileType === '.pdf';
  const isOffice = OFFICE_TYPES.includes(fileType);
  const isText = file.type === 'text';
  const isUrl = file.type === 'url';
  const hasGDrivePath = Boolean(file.file_path);

  const previewUrl = getPreviewUrl(file.object_id, vaultPassword);
  const driveEmbedUrl = hasGDrivePath
    ? `https://drive.google.com/file/d/${file.file_path}/preview`
    : null;

  const openInDrive = () => {
    if (file.file_path) {
      window.open(
        `https://drive.google.com/file/d/${file.file_path}/view`,
        '_blank'
      );
    }
  };

  const [textContent, setTextContent] = useState<string | null>(null);
  const [loadingText, setLoadingText] = useState(false);

  useEffect(() => {
    if (isText && file) {
      setLoadingText(true);
      fetch(previewUrl)
        .then(res => res.text())
        .then(text => {
          setTextContent(text);
          setLoadingText(false);
        })
        .catch(err => {
          console.error('Failed to fetch snippet:', err);
          setLoadingText(false);
        });
    } else {
      setTextContent(null);
    }
  }, [file, isText, previewUrl]);

  const renderPreviewContent = () => {
    // ─ Content Loading ──────────────────────
    if (loadingText) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[40vh]">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-muted-foreground animate-pulse">Retreiving snippet content...</p>
        </div>
      );
    }

    // ─ Images ───────────────────────────────────────────────
    if (isImage) {
      return (
        <div className="flex items-center justify-center h-full bg-muted/20 rounded-xl overflow-hidden animate-in fade-in zoom-in duration-300">
          <img
            src={previewUrl}
            alt={file.source}
            className="max-w-full max-h-[70vh] object-contain shadow-2xl rounded-lg"
            onError={(e) => {
              (e.target as HTMLImageElement).src = file.thumbnail_url || '';
            }}
          />
        </div>
      );
    }

    // ─ PDFs & Office ──────────────────────────────────────────
    if (isPDF || isOffice) {
      const sourceUrl = isOffice && driveEmbedUrl ? driveEmbedUrl : previewUrl;
      return (
        <div className="h-[75vh] w-full rounded-xl overflow-hidden border border-border shadow-inner bg-card">
          <iframe
            src={sourceUrl}
            title={file.source}
            className="w-full h-full border-none"
            allow="autoplay; encrypted-media"
          />
        </div>
      );
    }

    // ─ Snippets (Text) ──────────────────────────────────────
    if (isText && textContent !== null) {
      return (
        <div className="w-full max-h-[70vh] bg-muted/30 rounded-xl border border-border p-6 overflow-auto font-mono text-sm leading-relaxed text-foreground whitespace-pre-wrap select-text selection:bg-primary/20">
          {textContent}
        </div>
      );
    }

    // ─ URL Collection ───────────────────────────────────────
    if (isUrl) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[50vh] bg-muted/20 rounded-2xl border border-border p-8 text-center">
          <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
            <HiOutlineLink className="w-10 h-10 text-primary" />
          </div>
          <h3 className="text-xl font-bold text-foreground mb-2 truncate max-w-lg">{file.source}</h3>
          <p className="text-muted-foreground max-w-sm mx-auto mb-8 break-all">
            {file.file_path || 'No URL specified'}
          </p>
          <a
            href={file.file_path}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary px-8 py-3 flex items-center gap-2"
          >
            <HiOutlineExternalLink className="w-5 h-5" />
            Open Link
          </a>
        </div>
      );
    }

    // ─ Fallback ───────────────────────────────────────
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] bg-muted/20 rounded-2xl border border-dashed border-border p-8 text-center animate-in slide-in-from-bottom-4">
        <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
          <HiOutlineDocument className="w-10 h-10 text-primary" />
        </div>
        <h3 className="text-xl font-bold text-foreground mb-2 truncate max-w-lg">{file.source}</h3>
        <p className="text-muted-foreground max-w-xs mx-auto mb-8">
          This file format ({fileType.toUpperCase() || 'UNKNOWN'}) is securely stored.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {hasGDrivePath && (
            <button
              onClick={openInDrive}
              className="px-6 py-3 rounded-xl bg-primary text-primary-foreground font-semibold hover:opacity-90 transition-all flex items-center gap-2"
            >
              <HiOutlineExternalLink className="w-5 h-5" />
              View in Google Drive
            </button>
          )}
        </div>
      </div>
    );
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-background/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-card rounded-2xl shadow-2xl border border-border w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-border flex-shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              {file.icon_url ? (
                <img
                  src={file.icon_url}
                  alt={file.type}
                  className="w-8 h-8 object-contain flex-shrink-0"
                />
              ) : (
                <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-primary/10 flex-shrink-0">
                  {isImage ? (
                    <HiOutlinePhotograph className="w-5 h-5 text-primary" />
                  ) : isUrl ? (
                    <HiOutlineLink className="w-5 h-5 text-primary" />
                  ) : (
                    <HiOutlineDocument className="w-5 h-5 text-primary" />
                  )}
                </div>
              )}
              <div className="min-w-0">
                <h2 className="font-semibold truncate text-foreground">
                  {file.source}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {formatFileSize(file.file_size)}
                  {fileType && ` · ${fileType.toUpperCase().replace('.', '')}`}
                  {file.chunk_count > 0 && ` · ${file.chunk_count} chunks`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {hasGDrivePath && (
                <button
                  onClick={openInDrive}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border hover:bg-muted transition-colors text-sm text-muted-foreground"
                  title="Open in Google Drive"
                >
                  <HiOutlineExternalLink className="w-4 h-4" />
                  <span className="hidden sm:inline">Drive</span>
                </button>
              )}
              <button
                onClick={onClose}
                className="p-2 hover:bg-muted rounded-xl transition-colors"
                id="close-preview-btn"
              >
                <HiOutlineX className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Preview area */}
          <div className="flex-1 p-5 overflow-auto bg-muted/5">
            {renderPreviewContent()}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
