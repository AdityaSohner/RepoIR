// ============================================================
// RepoIR API Service Layer
// Connects to the backend via environment variable (VITE_API_BASE_URL).
// Set VITE_API_BASE_URL in your .env file or in the Render dashboard.
// ============================================================

export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ---- Auth helpers ------------------------------------------

function getToken(): string | null {
  return sessionStorage.getItem('repoir_token');
}

export function setToken(token: string) {
  sessionStorage.setItem('repoir_token', token);
}

export function clearToken() {
  sessionStorage.removeItem('repoir_token');
}

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ---- Generic fetch wrapper ---------------------------------

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const isAuthRoute = path.includes('/auth/');
  const url = `${API_BASE.replace(/\/$/, '')}${path}`;

  console.log(`[RepoIR API] Calling: ${url}`);

  const headers: HeadersInit = {
    ...(options.headers || {}),
  };

  // Only add Authorization if we have a token AND it's not a root auth route (login/signup/google_auth)
  const token = getToken();
  const rootAuthRoutes = ['/v1/auth/google', '/v1/auth/login', '/v1/auth/signup'];
  const needsAuthToken = token && !rootAuthRoutes.includes(path);

  if (needsAuthToken) {
    (headers as any)['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      msg = body.detail || body.message || msg;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }

  return res.json() as Promise<T>;
}

// ============================================================
// 1. Auth Endpoints
// ============================================================

export interface AuthResponse {
  status: string;
  user_id: string;
  token: string;
}

export async function apiSignup(
  email: string,
  password: string
): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/v1/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
}

export async function apiLogin(
  email: string,
  password: string
): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
}

export async function apiGoogleAuth(id_token: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/v1/auth/google', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_token }),
  });
}

export async function apiGetConfig(): Promise<{ client_id: string }> {
  return apiFetch<{ client_id: string }>('/v1/config');
}

// ============================================================
// 2. Google Drive Vault
// ============================================================

export interface VaultStatusResponse {
  status: 'valid' | 'not_connected' | 'locked' | 'invalid';
}

export interface VaultSyncResponse {
  status: string;
  new_files: number;
}

export async function apiGDriveCallback(
  code: string,
  redirect_uri: string,
  vault_password: string
): Promise<{ status: string }> {
  return apiFetch('/v1/auth/gdrive/callback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, redirect_uri, vault_password }),
  });
}

export async function apiVaultStatus(
  password: string
): Promise<VaultStatusResponse> {
  return apiFetch<VaultStatusResponse>('/v1/vault/status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
}

export async function apiVaultSync(
  password: string
): Promise<VaultSyncResponse> {
  return apiFetch<VaultSyncResponse>('/v1/vault/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
}

// ============================================================
// 3. Ingestion
// ============================================================

export interface IngestJobResponse {
  status: string;
  job_ids: string[];
}

export interface JobStatusResponse {
  job_id: string;
  status: 'pending' | 'scanning' | 'uploading' | 'completed' | 'failed';
  error: string | null;
}

export async function apiIngestCloud(
  files: File[],
  password: string
): Promise<IngestJobResponse> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  form.append('password', password);
  return apiFetch<IngestJobResponse>('/v1/ingest/cloud', {
    method: 'POST',
    body: form,
  });
}

export async function apiIngestUrl(url: string): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append('url', url);
  return apiFetch<{ job_id: string }>('/v1/ingest/url', {
    method: 'POST',
    body: form,
  });
}

export async function apiIngestText(
  text: string,
  filename?: string,
  password?: string
): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append('text', text);
  if (filename) form.append('filename', filename);
  if (password) form.append('password', password);
  return apiFetch<{ job_id: string }>('/v1/ingest/text', {
    method: 'POST',
    body: form,
  });
}

export async function apiJobStatus(job_id: string): Promise<JobStatusResponse> {
  return apiFetch<JobStatusResponse>(`/v1/status/${job_id}`);
}

// ============================================================
// 4. Files & Search
// ============================================================

export interface RepoFile {
  object_id: string;
  user_id: string;
  source: string;
  type: 'document' | 'image' | 'text' | 'url';
  file_type: string;
  file_path: string; // Google Drive File ID
  chunk_count: number;
  file_size: number;
  thumbnail_url?: string;
  icon_url?: string;
}

export interface FilesResponse {
  files: RepoFile[];
}

export async function apiGetFiles(): Promise<FilesResponse> {
  return apiFetch<FilesResponse>('/v1/files');
}

export interface SearchResponse {
  results: RepoFile[];
}

export async function apiSearch(
  query: string,
  limit = 10
): Promise<SearchResponse> {
  return apiFetch<SearchResponse>('/v1/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit }),
  });
}

// Build preview URL for a file
export function getPreviewUrl(
  object_id: string,
  vaultPassword: string
): string {
  const token = getToken() || '';
  return `${API_BASE}/v1/files/preview?object_id=${encodeURIComponent(object_id)}&password=${encodeURIComponent(vaultPassword)}&token=${encodeURIComponent(token)}`;
}

// ============================================================
// 5. Analytics
// ============================================================

export interface StatItem {
  count: number;
  total_size_bytes: number;
}

export interface StatsResponse {
  document: StatItem;
  image: StatItem;
  text: StatItem;
  url: StatItem;
}

export interface ActivityItem {
  log_id: number;
  user_id: string;
  action: string;
  details: string;
  timestamp: string;
}

export interface ActivityResponse {
  activity: ActivityItem[];
}

export async function apiGetStats(): Promise<StatsResponse> {
  return apiFetch<StatsResponse>('/v1/analytics/stats');
}

export async function apiGetActivity(): Promise<ActivityResponse> {
  return apiFetch<ActivityResponse>('/v1/analytics/activity');
}

// ============================================================
// Helpers
// ============================================================

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '—';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

// Poll a job until completed/failed, calling onUpdate each tick
export async function pollJob(
  jobId: string,
  onUpdate: (status: JobStatusResponse) => void,
  intervalMs = 800,
  maxAttempts = 120
): Promise<JobStatusResponse> {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const id = setInterval(async () => {
      attempts++;
      try {
        const status = await apiJobStatus(jobId);
        onUpdate(status);
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(id);
          resolve(status);
        }
      } catch (err) {
        clearInterval(id);
        reject(err);
      }
      if (attempts >= maxAttempts) {
        clearInterval(id);
        reject(new Error('Job polling timed out'));
      }
    }, intervalMs);
  });
}
