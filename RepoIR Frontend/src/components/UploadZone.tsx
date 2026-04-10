import { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  HiOutlineCloudUpload,
  HiOutlineLink,
  HiOutlinePencilAlt,
  HiOutlineCheck,
  HiOutlineExclamation,
} from 'react-icons/hi';
import { useApp } from '@/contexts/AppContext';
import {
  apiIngestCloud,
  apiIngestUrl,
  apiIngestText,
  apiJobStatus,
  JobStatusResponse,
} from '@/lib/api';

type Tab = 'file' | 'url' | 'text';

interface UploadJob {
  jobId: string;
  name: string;
  status: JobStatusResponse['status'];
  error: string | null;
}

const STATUS_LABELS: Record<JobStatusResponse['status'], string> = {
  pending: 'Queued',
  scanning: 'Scanning',
  uploading: 'Uploading',
  completed: 'Done',
  failed: 'Failed',
};

const STATUS_PROGRESS: Record<JobStatusResponse['status'], number> = {
  pending: 10,
  scanning: 35,
  uploading: 70,
  completed: 100,
  failed: 100,
};

export default function UploadZone() {
  const { vaultPassword, addNotification, refreshFiles, refreshStats } =
    useApp();

  const [activeTab, setActiveTab] = useState<Tab>('file');
  const [isDragging, setIsDragging] = useState(false);
  const [jobs, setJobs] = useState<UploadJob[]>([]);
  const [urlInput, setUrlInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [filenameInput, setFilenameInput] = useState('');
  const [miniIngestLoading, setMiniIngestLoading] = useState(false);
  const [showJobs, setShowJobs] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // ── Helpers ────────────────────────────────────────────────

  const updateJob = (jobId: string, patch: Partial<UploadJob>) => {
    setJobs((prev) =>
      prev.map((j) => (j.jobId === jobId ? { ...j, ...patch } : j))
    );
  };

  const pollJob = (jobId: string, name: string) => {
    let attempts = 0;
    const id = setInterval(async () => {
      attempts++;
      try {
        const res = await apiJobStatus(jobId);
        updateJob(jobId, { status: res.status, error: res.error });
        if (res.status === 'completed' || res.status === 'failed') {
          clearInterval(id);
          if (res.status === 'completed') {
            addNotification(`"${name}" ingested successfully`, 'success');
            refreshFiles();
            refreshStats();
          } else {
            addNotification(`"${name}" failed: ${res.error}`, 'error');
          }
        }
      } catch (err) {
        console.error('Job poll err:', err);
      }
      if (attempts > 120) {
        clearInterval(id);
        updateJob(jobId, { status: 'failed', error: 'Timed out' });
      }
    }, 2000);
  };

  // ── File Upload ────────────────────────────────────────────

  const handleFiles = async (fileList: FileList) => {
    if (!vaultPassword) {
      addNotification(
        'Connect your Vault (Drive) first — enter your Vault Secret in Settings.',
        'error'
      );
      return;
    }
    const filesArray = Array.from(fileList);
    try {
      const res = await apiIngestCloud(filesArray, vaultPassword);
      const newJobs: UploadJob[] = res.job_ids.map((jobId, i) => ({
        jobId,
        name: filesArray[i]?.name || jobId,
        status: 'pending',
        error: null,
      }));
      setJobs((prev) => [...newJobs, ...prev]);
      newJobs.forEach((j) => pollJob(j.jobId, j.name));
    } catch (err: unknown) {
      addNotification(
        `Upload failed: ${err instanceof Error ? err.message : 'Unknown error'}`,
        'error'
      );
    }
  };

  // ── URL Ingest ─────────────────────────────────────────────

  const handleUrlIngest = async () => {
    if (!urlInput.trim()) return;
    setMiniIngestLoading(true);
    try {
      const res = await apiIngestUrl(urlInput.trim());
      const newJob: UploadJob = {
        jobId: res.job_id,
        name: urlInput.trim(),
        status: 'pending',
        error: null,
      };
      setJobs((prev) => [newJob, ...prev]);
      pollJob(res.job_id, urlInput.trim());
      setUrlInput('');
    } catch (err: unknown) {
      addNotification(
        `URL ingest failed: ${err instanceof Error ? err.message : 'Unknown'}`,
        'error'
      );
    } finally {
      setMiniIngestLoading(false);
    }
  };

  // ── Text Ingest ────────────────────────────────────────────

  const handleTextIngest = async () => {
    if (!textInput.trim()) return;
    setMiniIngestLoading(true);
    try {
      const res = await apiIngestText(
        textInput.trim(),
        filenameInput.trim() || 'Pasted_Snippet.txt',
        vaultPassword || undefined
      );
      const name = filenameInput.trim() || 'Pasted_Snippet.txt';
      const newJob: UploadJob = {
        jobId: res.job_id,
        name,
        status: 'pending',
        error: null,
      };
      setJobs((prev) => [newJob, ...prev]);
      pollJob(res.job_id, name);
      setTextInput('');
      setFilenameInput('');
    } catch (err: unknown) {
      addNotification(
        `Text ingest failed: ${err instanceof Error ? err.message : 'Unknown'}`,
        'error'
      );
    } finally {
      setMiniIngestLoading(false);
    }
  };

  // ── Render ─────────────────────────────────────────────────

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    {
      id: 'file',
      label: 'Upload Files',
      icon: <HiOutlineCloudUpload className="w-4 h-4" />,
    },
    {
      id: 'url',
      label: 'Web URL',
      icon: <HiOutlineLink className="w-4 h-4" />,
    },
    {
      id: 'text',
      label: 'Paste Text',
      icon: <HiOutlinePencilAlt className="w-4 h-4" />,
    },
  ];

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 rounded-xl bg-muted w-fit">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === t.id
                ? 'bg-background shadow-sm text-foreground'
                : 'text-muted-foreground hover:text-foreground'
              }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        {activeTab === 'file' && (
          <motion.div
            key="file"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              if (e.dataTransfer.files.length > 0)
                handleFiles(e.dataTransfer.files);
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onClick={() => inputRef.current?.click()}
            className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 ${isDragging
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/50'
              }`}
          >
            <input
              ref={inputRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => e.target.files && handleFiles(e.target.files)}
              id="file-upload-input"
            />
            <div
              className={`w-16 h-16 mx-auto rounded-2xl flex items-center justify-center mb-4 transition-colors ${isDragging
                  ? 'bg-primary/15 text-primary'
                  : 'bg-muted text-muted-foreground'
                }`}
            >
              <HiOutlineCloudUpload className="w-8 h-8" />
            </div>
            <p className="text-lg font-medium mb-1 text-foreground">
              {isDragging
                ? 'Drop files here'
                : 'Drop files here or click to upload'}
            </p>
            <p className="text-sm text-muted-foreground">
              Supports images, PDFs, DOCX, PPTX, XLSX, and text files
            </p>
            {!vaultPassword && (
              <p className="text-xs text-amber-500 mt-3">
                ⚠ Vault Secret not set — files uploaded without Drive backup
              </p>
            )}
          </motion.div>
        )}

        {activeTab === 'url' && (
          <motion.div
            key="url"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
            className="rounded-2xl border border-border bg-card p-6 space-y-4"
          >
            <p className="text-sm text-muted-foreground">
              Paste a public URL and RepoIR will scrape, extract, and embed it.
            </p>
            <div className="flex gap-3">
              <div className="relative flex-1">
                <HiOutlineLink className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="url"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://example.com/article"
                  className="w-full glass-input pl-11 pr-4 py-3 text-foreground placeholder-muted-foreground text-sm"
                  id="url-ingest-input"
                  onKeyDown={(e) => e.key === 'Enter' && handleUrlIngest()}
                />
              </div>
              <button
                onClick={handleUrlIngest}
                disabled={miniIngestLoading || !urlInput.trim()}
                className="btn-primary px-5 disabled:opacity-50 flex items-center gap-2"
                id="url-ingest-btn"
              >
                {miniIngestLoading ? (
                  <svg
                    className="animate-spin w-4 h-4"
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
                  'Ingest'
                )}
              </button>
            </div>
          </motion.div>
        )}

        {activeTab === 'text' && (
          <motion.div
            key="text"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
            className="rounded-2xl border border-border bg-card p-6 space-y-4"
          >
            <p className="text-sm text-muted-foreground">
              Paste any text snippet. RepoIR will embed and index it immediately.
            </p>
            <input
              type="text"
              value={filenameInput}
              onChange={(e) => setFilenameInput(e.target.value)}
              placeholder="Optional filename (e.g. Meeting_Notes.txt)"
              className="w-full glass-input px-4 py-2.5 text-foreground placeholder-muted-foreground text-sm"
              id="text-ingest-filename"
            />
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Paste your text here..."
              rows={5}
              className="w-full glass-input px-4 py-3 text-foreground placeholder-muted-foreground text-sm resize-none"
              id="text-ingest-content"
            />
            <button
              onClick={handleTextIngest}
              disabled={miniIngestLoading || !textInput.trim()}
              className="btn-primary px-6 disabled:opacity-50 flex items-center gap-2"
              id="text-ingest-btn"
            >
              {miniIngestLoading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24">
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
                  Ingesting...
                </span>
              ) : (
                'Save Snippet'
              )}
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Active Jobs */}
      <div className="flex justify-start mt-2">
        {jobs.length > 0 && (
          <button
            onClick={() => setShowJobs(!showJobs)}
            className="text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
          >
            {showJobs ? 'Hide Ingestion Activity' : `Show Ingestion Activity (${jobs.length})`}
          </button>
        )}
      </div>

      <AnimatePresence>
        {jobs.length > 0 && showJobs && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-2 pt-2"
          >
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Ingestion Jobs
            </p>
            {jobs.slice(0, 8).map((job) => {
              const isDone = job.status === 'completed';
              const isFailed = job.status === 'failed';
              const progress = STATUS_PROGRESS[job.status];
              return (
                <motion.div
                  key={job.jobId}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl border border-border bg-card p-3"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span
                      className="text-sm truncate text-foreground max-w-[200px]"
                      title={job.name}
                    >
                      {job.name}
                    </span>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs font-medium ${isFailed
                            ? 'text-destructive'
                            : isDone
                              ? 'text-emerald-500'
                              : 'text-primary'
                          }`}
                      >
                        {STATUS_LABELS[job.status]}
                      </span>
                      {isDone && (
                        <HiOutlineCheck className="w-4 h-4 text-emerald-500" />
                      )}
                      {isFailed && (
                        <HiOutlineExclamation className="w-4 h-4 text-destructive" />
                      )}
                    </div>
                  </div>
                  <div className="h-1.5 rounded-full overflow-hidden bg-muted">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 0.4 }}
                      className={`h-full rounded-full ${isFailed
                          ? 'bg-destructive'
                          : isDone
                            ? 'bg-emerald-500'
                            : ''
                        }`}
                      style={
                        !isFailed && !isDone
                          ? {
                            background:
                              'linear-gradient(90deg, hsl(187 92% 45%), hsl(217 91% 55%))',
                          }
                          : {}
                      }
                    />
                  </div>
                  {isFailed && job.error && (
                    <p className="text-xs text-destructive mt-1 truncate">
                      {job.error}
                    </p>
                  )}
                </motion.div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
