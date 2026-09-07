import { useEffect, useState } from 'react';
import { HiOutlineMail, HiOutlineX, HiOutlineShare } from 'react-icons/hi';
import { RepoFile, apiSearchUsers, apiShareFile, UserSearchResult } from '@/lib/api';

interface ShareModalProps {
  file: RepoFile;
  onClose: () => void;
  onShared: (email: string) => void;
}

export default function ShareModal({ file, onClose, onShared }: ShareModalProps) {
  const [email, setEmail] = useState('');
  const [suggestions, setSuggestions] = useState<UserSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (email.trim().length < 3) {
      setSuggestions([]);
      return;
    }
    const timer = window.setTimeout(() => {
      apiSearchUsers(email.trim()).then(setSuggestions).catch(() => setSuggestions([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [email]);

  const submit = async () => {
    const recipientEmail = email.trim();
    if (!recipientEmail || !recipientEmail.includes('@')) {
      setError('Enter a valid email address.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await apiShareFile(file.object_id, recipientEmail);
      onShared(recipientEmail);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to share this file.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="mb-2 flex items-center gap-2 text-primary"><HiOutlineShare className="h-5 w-5" /><span className="text-sm font-semibold">Share file</span></div>
            <h2 className="text-lg font-semibold text-foreground">Send “{file.source}”</h2>
            <p className="mt-1 text-sm text-muted-foreground">Share a copy with a registered RepoIR email.</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-muted-foreground hover:bg-muted" title="Close"><HiOutlineX className="h-5 w-5" /></button>
        </div>
        <div className="relative mt-6">
          <HiOutlineMail className="absolute left-3 top-3 h-5 w-5 text-muted-foreground" />
          <input autoFocus value={email} onChange={(event) => setEmail(event.target.value)} placeholder="recipient@gmail.com" type="email" className="w-full rounded-xl border border-border bg-background py-3 pl-10 pr-3 text-sm outline-none focus:border-primary" onKeyDown={(event) => { if (event.key === 'Enter') submit(); }} />
          {suggestions.length > 0 && (
            <div className="absolute left-0 right-0 top-full z-10 mt-1 overflow-hidden rounded-xl border border-border bg-card shadow-lg">
              {suggestions.map((suggestion) => <button key={suggestion.user_id} onClick={() => { setEmail(suggestion.email); setSuggestions([]); }} className="block w-full px-3 py-2 text-left text-sm text-foreground hover:bg-muted">{suggestion.email}</button>)}
            </div>
          )}
        </div>
        {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-xl px-4 py-2 text-sm text-muted-foreground hover:bg-muted">Cancel</button>
          <button onClick={submit} disabled={loading} className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50">{loading ? 'Sharing...' : 'Share file'}</button>
        </div>
      </div>
    </div>
  );
}