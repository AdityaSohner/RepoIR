import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  HiOutlineSearch,
  HiOutlinePhotograph,
  HiOutlineDocument,
  HiOutlinePencil,
  HiOutlineUser,
  HiOutlineCog,
  HiOutlineCloudUpload,
} from 'react-icons/hi';
import { useApp } from '@/contexts/AppContext';
import { apiSearch, RepoFile } from '@/lib/api';

const quickCommands = [
  {
    id: 'profile',
    name: 'Go to Profile',
    icon: HiOutlineUser,
    path: '/profile',
  },
  {
    id: 'settings',
    name: 'Go to Settings',
    icon: HiOutlineCog,
    path: '/settings',
  },
  {
    id: 'dashboard',
    name: 'Go to Dashboard',
    icon: HiOutlineCloudUpload,
    path: '/dashboard',
  },
];

function getFileIcon(type: string) {
  switch (type) {
    case 'image':
      return HiOutlinePhotograph;
    case 'text':
      return HiOutlinePencil;
    default:
      return HiOutlineDocument;
  }
}

export default function CommandPalette() {
  const { commandPaletteOpen, setCommandPaletteOpen } = useApp();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<RepoFile[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredCommands = query.trim()
    ? quickCommands.filter((c) =>
      c.name.toLowerCase().includes(query.toLowerCase())
    )
    : quickCommands;

  const allItems = [
    ...filteredCommands.map((c) => ({ type: 'command' as const, item: c })),
    ...searchResults.map((f) => ({ type: 'file' as const, item: f })),
  ];

  // Reset on open/close
  useEffect(() => {
    if (!commandPaletteOpen) {
      setQuery('');
      setSearchResults([]);
      setSelectedIndex(0);
    } else {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [commandPaletteOpen]);

  // Reset selectedIndex on query change
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const performSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const res = await apiSearch(q, 5);
      setSearchResults(res.results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  const onQueryChange = (q: string) => {
    setQuery(q);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => performSearch(q), 400);
  };

  const handleSelect = (item: (typeof allItems)[0]) => {
    setCommandPaletteOpen(false);
    if (item.type === 'command') {
      navigate((item.item as (typeof quickCommands)[0]).path);
    }
    // For files, just close (could open preview in future)
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, allItems.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const selected = allItems[selectedIndex];
      if (selected) handleSelect(selected);
    }
  };

  if (!commandPaletteOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={() => setCommandPaletteOpen(false)}
        className="cmd-overlay"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -10 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          onClick={(e) => e.stopPropagation()}
          className="cmd-palette"
        >
          {/* Search input */}
          <div className="flex items-center gap-3 px-5 py-4 border-b border-border">
            {searching ? (
              <svg
                className="animate-spin w-5 h-5 text-primary flex-shrink-0"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            ) : (
              <HiOutlineSearch className="w-5 h-5 text-muted-foreground flex-shrink-0" />
            )}
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search files or type a command..."
              className="flex-1 bg-transparent text-lg outline-none placeholder-muted-foreground"
              id="command-palette-input"
            />
            <kbd className="px-2 py-1 bg-muted rounded text-xs text-muted-foreground">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-96 overflow-y-auto p-2">
            {filteredCommands.length > 0 && (
              <div className="mb-2">
                <p className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase">
                  {query ? 'Commands' : 'Quick Actions'}
                </p>
                {filteredCommands.map((cmd, idx) => {
                  const Icon = cmd.icon;
                  const isSelected = idx === selectedIndex;
                  return (
                    <button
                      key={cmd.id}
                      onClick={() =>
                        handleSelect({ type: 'command', item: cmd })
                      }
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors ${isSelected
                          ? 'bg-cyan-500/10 text-cyan-500'
                          : 'hover:bg-muted'
                        }`}
                    >
                      <Icon className="w-5 h-5" />
                      <span className="text-sm">{cmd.name}</span>
                    </button>
                  );
                })}
              </div>
            )}

            {searchResults.length > 0 && (
              <div>
                <p className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase">
                  Files
                </p>
                {searchResults.map((file, idx) => {
                  const Icon = getFileIcon(file.type);
                  const adjustedIdx = filteredCommands.length + idx;
                  const isSelected = adjustedIdx === selectedIndex;
                  return (
                    <button
                      key={file.object_id}
                      onClick={() =>
                        handleSelect({ type: 'file', item: file })
                      }
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors ${isSelected
                          ? 'bg-cyan-500/10 text-cyan-500'
                          : 'hover:bg-muted'
                        }`}
                    >
                      {file.icon_url ? (
                        <img
                          src={file.icon_url}
                          alt={file.type}
                          className="w-5 h-5 object-contain"
                        />
                      ) : (
                        <Icon className="w-5 h-5" />
                      )}
                      <span className="flex-1 text-sm text-left truncate">
                        {file.source}
                      </span>
                      <span className="tag-badge bg-muted text-muted-foreground">
                        {file.type}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}

            {allItems.length === 0 && query && !searching && (
              <p className="text-center py-8 text-muted-foreground">
                No results found
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center gap-4 px-5 py-3 border-t border-border text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-muted rounded">↑↓</kbd> Navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-muted rounded">↵</kbd> Select
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-muted rounded">ESC</kbd> Close
            </span>
            <span className="ml-auto text-primary/60">AI-powered search</span>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
