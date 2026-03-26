import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiGDriveCallback } from '@/lib/api';

/**
 * /auth/callback — landing page after Google OAuth redirect.
 * 
 * This page receives the OAuth code from Google, calls the backend
 * /v1/auth/gdrive/callback to exchange it, then posts a message back
 * to the opener window and closes itself.
 */
export default function OAuthCallbackPage() {
    const [searchParams] = useSearchParams();

    useEffect(() => {
        const code = searchParams.get('code');
        const vaultPassword = sessionStorage.getItem('repoir_vault_password') || '';
        const redirectUri = `${window.location.origin}/auth/callback`;

        if (!code) {
            window.opener?.postMessage(
                { type: 'gdrive_callback', success: false, error: 'No code returned' },
                window.location.origin
            );
            window.close();
            return;
        }

        // Exchange the code with the backend
        apiGDriveCallback(code, redirectUri, vaultPassword)
            .then(() => {
                window.opener?.postMessage(
                    { type: 'gdrive_callback', success: true },
                    window.location.origin
                );
            })
            .catch((err: Error) => {
                window.opener?.postMessage(
                    { type: 'gdrive_callback', success: false, error: err.message },
                    window.location.origin
                );
            })
            .finally(() => {
                window.close();
            });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-background gap-4">
            <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-2"
                style={{
                    background:
                        'linear-gradient(135deg, hsl(187 92% 45%), hsl(217 91% 55%))',
                }}
            >
                <span className="text-2xl font-bold text-white">R</span>
            </div>
            <div className="flex items-center gap-3">
                <svg
                    className="animate-spin w-6 h-6 text-primary"
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
                <p className="text-foreground font-medium">
                    Completing Drive connection…
                </p>
            </div>
            <p className="text-sm text-muted-foreground">
                This window will close automatically.
            </p>
        </div>
    );
}
