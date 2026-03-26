import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { HiOutlineViewGrid, HiOutlineViewList, HiOutlineRefresh } from 'react-icons/hi';
import { useApp } from '@/contexts/AppContext';
import { RepoFile } from '@/lib/api';
import FileCard from './FileCard';
import FilePreviewModal from './FilePreviewModal';

export default function FileGrid() {
  const { files, filesLoading, refreshFiles, addNotification } = useApp();
  const [searchParams, setSearchParams] = useSearchParams();
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [previewFile, setPreviewFile] = useState<RepoFile | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>(searchParams.get('type') || 'all');
  const [extFilter, setExtFilter] = useState<string>('all');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync with URL params
  useEffect(() => {
    const type = searchParams.get('type') || 'all';
    setTypeFilter(type);
    setExtFilter('all');
  }, [searchParams]);

  const setTypeAndUrl = (type: string) => {
    if (type === 'all') {
      const newParams = new URLSearchParams(searchParams);
      newParams.delete('type');
      setSearchParams(newParams);
    } else {
      setSearchParams({ type });
    }
  };

  // Load files on mount
  useEffect(() => {
    refreshFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);



  const typeFilterOptions = [
    { label: 'All', value: 'all' },
    { label: 'Images', value: 'image' },
    { label: 'Documents', value: 'document' },
    { label: 'URLs', value: 'url' },
    { label: 'Snippets', value: 'text' },
  ];

  const getExtOptions = () => {
    if (typeFilter === 'document') return ['docx', 'pdf', 'pptx', 'xlsx'];
    if (typeFilter === 'image') return ['jpg', 'png', 'svg', 'webp'];
    if (typeFilter === 'url') return ['link', 'web'];
    return [];
  };

  const extOptions = getExtOptions();

  const displayedFiles = files.filter((f) => {
    const matchesType = typeFilter === 'all' ? true : f.type === typeFilter;
    if (!matchesType) return false;
    if (extFilter === 'all') return true;
    return f.file_type.toLowerCase().includes(extFilter.toLowerCase());
  });

  const sectionTitle = typeFilter === 'all'
    ? 'Gallery'
    : typeFilterOptions.find(o => o.value === typeFilter)?.label || 'Files';

  const isEmpty = displayedFiles.length === 0 && !filesLoading;

  return (
    <div className="relative">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <h2 className="text-xl font-semibold text-foreground">
          {sectionTitle}
          {displayedFiles.length > 0 && (
            <span className="ml-2 text-base font-normal text-muted-foreground">
              ({displayedFiles.length})
            </span>
          )}
        </h2>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Type filter pills - Show ONLY in Gallery section */}
          {typeFilter === 'all' && (
            <div className="flex items-center gap-1 p-1 rounded-xl bg-muted">
              {typeFilterOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setTypeAndUrl(opt.value)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${typeFilter === opt.value
                    ? 'bg-background shadow-sm text-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                    }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}

          {/* Extension Pills - Show in Category sections */}
          {typeFilter !== 'all' && (
            <div className="flex items-center gap-1 p-1 rounded-xl border border-border">
              <button
                onClick={() => setExtFilter('all')}
                className={`px-2 py-1 rounded-lg text-[10px] font-bold uppercase transition-all ${extFilter === 'all' ? 'bg-primary text-white' : 'text-muted-foreground'}`}
              >
                All
              </button>
              {extOptions.map(ext => (
                <button
                  key={ext}
                  onClick={() => setExtFilter(ext)}
                  className={`px-2 py-1 rounded-lg text-[10px] font-bold uppercase transition-all ${extFilter === ext ? 'bg-primary text-white' : 'text-muted-foreground'}`}
                >
                  {ext}
                </button>
              ))}
            </div>
          )}

          {/* Refresh */}
          <button
            onClick={refreshFiles}
            className="p-2 rounded-xl hover:bg-muted transition-colors text-muted-foreground"
            title="Refresh"
          >
            <HiOutlineRefresh
              className={`w-4 h-4 ${filesLoading ? 'animate-spin' : ''}`}
            />
          </button>

          {/* View toggle */}
          <div className="flex items-center rounded-xl p-1 bg-muted">
            <button
              onClick={() => setView('grid')}
              className={`p-2 rounded-lg transition-colors ${view === 'grid' ? 'bg-background shadow-sm' : ''
                }`}
            >
              <HiOutlineViewGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setView('list')}
              className={`p-2 rounded-lg transition-colors ${view === 'list' ? 'bg-background shadow-sm' : ''
                }`}
            >
              <HiOutlineViewList className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* DASHBOARD VIEW */}
      <>
        {/* Loading skeleton */}
        {filesLoading && files.length === 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="rounded-xl border border-border bg-card/70 p-4 aspect-square animate-pulse"
              >
                <div className="w-full h-full rounded-xl bg-muted" />
              </div>
            ))}
          </div>
        )}

        <AnimatePresence mode="wait">
          {!filesLoading && !isEmpty && (
            <motion.div
              key="files"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className={
                view === 'grid'
                  ? 'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6'
                  : 'space-y-3'
              }
            >
              {displayedFiles.map((file, index) => (
                <FileCard
                  key={file.object_id}
                  file={file}
                  index={index}
                  view={view}
                  onPreview={() => setPreviewFile(file)}
                />
              ))}
            </motion.div>
          )}

          {isEmpty && !filesLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-20 bg-muted/5 rounded-3xl border border-dashed border-border"
            >
              <p className="text-muted-foreground">Your vault is empty. Upload some files to get started.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </>

      <FilePreviewModal
        file={previewFile}
        onClose={() => setPreviewFile(null)}
      />
    </div>
  );
}
