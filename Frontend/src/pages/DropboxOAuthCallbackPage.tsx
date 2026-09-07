import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { API_BASE } from '@/lib/api';

/**
 * /storage/dropbox/callback — Landing page after Dropbox OAuth redirect.
 * Reads code and state, invokes backend endpoint, and notifies parent window.
 */
export default function DropboxOAuthCallbackPage() {
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');

    if (error || !code || !state) {
      window.opener?.postMessage(
        { type: 'dropbox_callback', success: false, error: error || 'Missing authorization code or state' },
        window.location.origin
      );
      window.close();
      return;
    }

    const redirectUri = `${window.location.origin}/storage/dropbox/callback`;
    const token = sessionStorage.getItem('repoir_token') || '';

    fetch(`${API_BASE}/v1/storage/dropbox/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}&redirect_uri=${encodeURIComponent(redirectUri)}`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `HTTP ${res.status}`);
        }
        return res.json();
      })
      .then(() => {
        window.opener?.postMessage(
          { type: 'dropbox_callback', success: true },
          window.location.origin
        );
      })
      .catch((err: Error) => {
        window.opener?.postMessage(
          { type: 'dropbox_callback', success: false, error: err.message },
          window.location.origin
        );
      })
      .finally(() => {
        window.close();
      });
  }, [searchParams]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background gap-4">
      <div
        className="w-14 h-14 rounded-2xl flex items-center justify-center mb-2"
        style={{
          background: 'linear-gradient(135deg, #0061FE, #0045B5)',
        }}
      >
        <span className="text-2xl font-bold text-white">D</span>
      </div>
      <div className="flex items-center gap-3">
        <svg className="animate-spin w-6 h-6 text-primary" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <p className="text-foreground font-medium">Completing Dropbox connection…</p>
      </div>
      <p className="text-sm text-muted-foreground">This window will close automatically.</p>
    </div>
  );
}
