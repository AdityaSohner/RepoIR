import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  HiOutlineMail,
  HiOutlineLockClosed,
  HiOutlineEye,
  HiOutlineEyeOff,
  HiOutlineUser,
} from 'react-icons/hi';
import { useAuth } from '@/contexts/AuthContext';
import { useApp } from '@/contexts/AppContext';

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const { signup, loginWithGoogle, user } = useAuth();
  const { refreshFiles, refreshStats, refreshActivity, vaultPassword } = useApp();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      if (!vaultPassword) {
        navigate('/settings', { replace: true });
      } else {
        navigate('/dashboard', { replace: true });
      }
    }
  }, [user, vaultPassword, navigate]);

  const afterSignup = useCallback(async () => {
    refreshFiles();
    refreshStats();
    refreshActivity();
  }, [refreshFiles, refreshStats, refreshActivity]);

  useEffect(() => {
    // Initialize Google button on mount
    loginWithGoogle('google-signup-btn');

    const handleSuccess = () => afterSignup();
    const handleError = (e: any) => setError(e.detail?.message || 'Google Auth Failed');

    window.addEventListener('google-login-success', handleSuccess);
    window.addEventListener('google-login-error', handleError);

    return () => {
      window.removeEventListener('google-login-success', handleSuccess);
      window.removeEventListener('google-login-error', handleError);
    };
  }, [loginWithGoogle, afterSignup]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      await signup(email, password);
      await afterSignup();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Signup failed');
    } finally {
      setIsLoading(false);
    }
  };

  const avatarUrl = email
    ? `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(
      email.split('@')[0]
    )}&backgroundColor=0ea5e9`
    : null;

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 right-1/4 w-[500px] h-[500px] rounded-full blur-[120px] bg-primary/5" />
        <div className="absolute bottom-1/4 left-1/4 w-[500px] h-[500px] rounded-full blur-[120px] bg-accent/5" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-md"
      >
        <div className="text-center mb-8">
          <div
            className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
            style={{
              background:
                'linear-gradient(135deg, hsl(187 92% 45%), hsl(217 91% 55%))',
            }}
          >
            <span className="text-2xl font-bold text-white">R</span>
          </div>
          <h1 className="text-3xl font-bold text-foreground mb-2">RepoIR</h1>
          <p className="text-muted-foreground">AI Knowledge Repository</p>
        </div>

        <div className="glass-card p-8">
          <div className="flex flex-col items-center mb-6">
            {avatarUrl ? (
              <motion.img
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                src={avatarUrl}
                alt="Avatar"
                className="w-20 h-20 rounded-full mb-4 ring-4 ring-primary/30"
              />
            ) : (
              <div className="w-20 h-20 rounded-full flex items-center justify-center mb-4 bg-muted ring-4 ring-border">
                <HiOutlineUser className="w-10 h-10 text-muted-foreground" />
              </div>
            )}
            <h2 className="text-2xl font-semibold text-foreground">
              Create account
            </h2>
          </div>

          {error && (
            <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-xl mb-6 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="relative">
              <HiOutlineMail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email address"
                className="w-full glass-input pl-12 pr-4 py-3.5 text-foreground placeholder-muted-foreground"
                required
                id="signup-email"
              />
            </div>

            <div className="relative">
              <HiOutlineLockClosed className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password (min 6 chars)"
                className="w-full glass-input pl-12 pr-12 py-3.5 text-foreground placeholder-muted-foreground"
                required
                minLength={6}
                id="signup-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                {showPassword ? (
                  <HiOutlineEyeOff className="w-5 h-5" />
                ) : (
                  <HiOutlineEye className="w-5 h-5" />
                )}
              </button>
            </div>

            <motion.button
              type="submit"
              disabled={isLoading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full btn-primary py-3.5 disabled:opacity-50"
              id="signup-submit"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
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
                  Creating account...
                </span>
              ) : (
                'Create account'
              )}
            </motion.button>
          </form>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-card text-muted-foreground">
                Or continue with
              </span>
            </div>
          </div>

          <div id="google-signup-btn" className="w-full flex justify-center py-2 min-h-[40px]"></div>

          <p className="text-center text-muted-foreground mt-6 text-sm">
            Already have an account?{' '}
            <Link
              to="/login"
              className="text-primary hover:text-primary/80 font-medium transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
