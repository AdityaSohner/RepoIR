import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';
import {
  apiLogin,
  apiSignup,
  apiGoogleAuth,
  apiGetConfig,
  setToken,
  clearToken,
  AuthResponse,
} from '@/lib/api';

// ── Google Client ID ─────────────────────────────────────────
// This is the public client ID used ONLY to initiate the Google
// Sign-In popup for ID-token retrieval. No secret is exposed here.
const DEFAULT_GOOGLE_CLIENT_ID =
  '431198643697-t8iv17kng6cjqdm173tliajok3aukb5b.apps.googleusercontent.com';

export interface User {
  id: string;
  email: string;
  avatar: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<boolean>;
  signup: (email: string, password: string) => Promise<boolean>;
  loginWithGoogle: (containerId: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  clientId: string;
}

const AuthContext = createContext<AuthContextType | null>(null);

// ── Google Identity Services loader ──────────────────────────
function loadGIS(): Promise<typeof window.google> {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts) {
      resolve(window.google);
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve(window.google);
    script.onerror = () => reject(new Error('Failed to load Google GIS'));
    document.head.appendChild(script);
  });
}

function hydrateUser(res: AuthResponse, email: string): User {
  return {
    id: res.user_id,
    email,
    name: email.split('@')[0],
    avatar: `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(
      email.split('@')[0]
    )}&backgroundColor=0ea5e9`,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [clientId, setClientId] = useState(DEFAULT_GOOGLE_CLIENT_ID);

  // Fetch true client ID from server on mount
  useEffect(() => {
    apiGetConfig()
      .then(cfg => {
        if (cfg.client_id) setClientId(cfg.client_id);
      })
      .catch(err => console.error("Failed to fetch Google Client ID from server:", err));
  }, []);

  // Restore session from sessionStorage on mount
  useEffect(() => {
    const stored = sessionStorage.getItem('repoir_user');
    if (stored) {
      try {
        setUser(JSON.parse(stored));
      } catch {
        // ignore malformed data
      }
    }
    setIsLoading(false);
  }, []);

  const persistUser = (u: User) => {
    setUser(u);
    // sessionStorage — clears on tab close; never persists vault secret here
    sessionStorage.setItem('repoir_user', JSON.stringify(u));
  };

  const login = useCallback(
    async (email: string, password: string): Promise<boolean> => {
      const res = await apiLogin(email, password);
      setToken(res.token);
      persistUser(hydrateUser(res, email));
      return true;
    },
    []
  );

  const signup = useCallback(
    async (email: string, password: string): Promise<boolean> => {
      const res = await apiSignup(email, password);
      setToken(res.token);
      persistUser(hydrateUser(res, email));
      return true;
    },
    []
  );

  const loginWithGoogle = useCallback(async (containerId: string): Promise<void> => {
    const google = await loadGIS();

    // Setup the global callback the declarative HTML uses
    (window as any).handleGoogleResponse = async (response: { credential: string }) => {
      try {
        const res = await apiGoogleAuth(response.credential);
        setToken(res.token);

        // Match the hub's hydration style: id comes from user_id
        const [, payloadB64] = response.credential.split('.');
        const payload = JSON.parse(atob(payloadB64));
        const email: string = payload.email || res.user_id;
        const name: string = payload.name || email.split('@')[0];
        const picture: string = payload.picture || `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(name)}&backgroundColor=0ea5e9`;

        const u: User = { id: res.user_id, email, name, avatar: picture };
        persistUser(u);
        window.dispatchEvent(new Event('google-login-success'));
      } catch (err) {
        console.error('Google Auth Failed:', err);
        window.dispatchEvent(new CustomEvent('google-login-error', { detail: err }));
      }
    };

    google.accounts.id.initialize({
      client_id: clientId,
      callback: (window as any).handleGoogleResponse,
      ux_mode: 'popup',
      context: 'signin',
      auto_prompt: false,
    });

    const accountsId = google.accounts.id as any;

    accountsId.renderButton(document.getElementById(containerId), {
      theme: 'outline',
      size: 'large',
      width: '380',
      text: 'signin_with',
      shape: 'rectangular',
      logo_alignment: 'left'
    });

    accountsId.prompt();
  }, [clientId]);

  const logout = useCallback(() => {
    setUser(null);
    clearToken();
    sessionStorage.removeItem('repoir_user');
    sessionStorage.removeItem('repoir_vault_password');
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, login, signup, loginWithGoogle, logout, isLoading, clientId }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

// Extend window for GIS typings (minimal)
declare global {
  interface Window {
    google: {
      accounts: {
        id: {
          initialize: (config: object) => void;
          prompt: (cb: (n: { isNotDisplayed(): boolean; isSkippedMoment(): boolean }) => void) => void;
        };
        oauth2: {
          initCodeClient: (config: object) => { requestCode: () => void };
        };
      };
    };
  }
}
