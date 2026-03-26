import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { HiOutlineSearch, HiOutlineX } from 'react-icons/hi';
import { useApp } from '@/contexts/AppContext';
import { RepoFile, apiSearch } from '@/lib/api';
import FileCard from './FileCard';
import FilePreviewModal from './FilePreviewModal';

export default function ImmersiveSearch() {
    const { immersiveSearchOpen, setImmersiveSearchOpen, addNotification } = useApp();
    const [query, setQuery] = useState('');
    const [results, setSearchResults] = useState<RepoFile[] | null>(null);
    const [searching, setSearching] = useState(false);
    const [previewFile, setPreviewFile] = useState<RepoFile | null>(null);
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Reset when closed
    useEffect(() => {
        if (!immersiveSearchOpen) {
            setQuery('');
            setSearchResults(null);
        } else {
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    }, [immersiveSearchOpen]);

    const handleSearch = useCallback(
        async (q: string) => {
            if (!q.trim()) {
                setSearchResults(null);
                return;
            }
            setSearching(true);
            try {
                const res = await apiSearch(q.trim(), 20);
                setSearchResults(res.results);
            } catch (err: unknown) {
                addNotification(
                    `Search failed: ${err instanceof Error ? err.message : 'Unknown'}`,
                    'error'
                );
                setSearchResults([]);
            } finally {
                setSearching(false);
            }
        },
        [addNotification]
    );

    const onQueryChange = (q: string) => {
        setQuery(q);
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => handleSearch(q), 500);
    };

    if (!immersiveSearchOpen) return null;

    return (
        <>
            <AnimatePresence>
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="search-mode-active"
                >
                    <button
                        onClick={() => setImmersiveSearchOpen(false)}
                        className="fixed top-8 right-8 p-3 rounded-full hover:bg-muted transition-colors text-muted-foreground z-[110] bg-background/50 backdrop-blur-md border border-border"
                    >
                        <HiOutlineX className="w-6 h-6" />
                    </button>

                    <div className="relative group w-full max-w-2xl mx-auto pt-20">
                        <div className="absolute inset-x-0 -top-20 h-96 bg-primary/20 blur-[100px] rounded-full opacity-0 group-focus-within:opacity-100 transition-opacity pointer-events-none" />
                        <div className={`relative flex items-center gap-4 px-6 py-5 rounded-2xl border transition-all duration-500 ${query.trim()
                            ? 'bg-card border-primary/50 shadow-[0_0_50px_-12px_rgba(0,0,0,0.5)] scale-110'
                            : 'bg-muted/50 border-border hover:bg-muted focus-within:bg-card focus-within:border-primary/50'
                            }`}>
                            {searching ? (
                                <svg className="animate-spin w-6 h-6 text-primary flex-shrink-0" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                </svg>
                            ) : (
                                <HiOutlineSearch className="w-6 h-6 text-muted-foreground flex-shrink-0 group-focus-within:text-primary" />
                            )}
                            <input
                                ref={inputRef}
                                type="text"
                                value={query}
                                onChange={(e) => onQueryChange(e.target.value)}
                                placeholder="Ask anything about your files..."
                                className="flex-1 bg-transparent text-xl outline-none text-foreground placeholder-muted-foreground"
                            />
                        </div>

                        {!query.trim() && (
                            <p className="text-center text-sm text-muted-foreground/60 mt-8 animate-pulse">
                                Try "recent legal docs" or "project images"
                            </p>
                        )}
                    </div>

                    {/* RESULTS AREA */}
                    <div className="w-full max-w-6xl mx-auto mt-12 overflow-y-auto max-h-[60vh] pb-20 custom-scrollbar px-4">
                        <AnimatePresence mode="wait">
                            {results && results.length > 0 ? (
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
                                >
                                    {results.map((file, index) => (
                                        <FileCard
                                            key={file.object_id}
                                            file={file}
                                            index={index}
                                            onPreview={() => setPreviewFile(file)}
                                        />
                                    ))}
                                </motion.div>
                            ) : results && !searching && (
                                <div className="text-center text-muted-foreground py-20 bg-muted/10 rounded-3xl border border-dashed border-border">
                                    <p className="text-lg font-medium text-foreground">No matches found for your query.</p>
                                    <p className="text-sm mt-1">Try different keywords or check your spelling.</p>
                                </div>
                            )}
                        </AnimatePresence>
                    </div>
                </motion.div>
            </AnimatePresence>

            <FilePreviewModal
                file={previewFile}
                onClose={() => setPreviewFile(null)}
            />
        </>
    );
}
