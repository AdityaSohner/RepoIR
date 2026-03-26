import { Link } from 'react-router-dom';

export default function ForgotPasswordPage() {
  return (
    <div className="min-h-screen bg-gradient-auth flex items-center justify-center p-4">
      <div className="glass-card p-8 w-full max-w-md text-center">
        <h1 className="text-2xl font-semibold text-white mb-2">Forgot password</h1>
        <p className="text-slate-400 mb-6">Password recovery can be connected later.</p>
        <Link to="/login" className="btn-primary inline-block">Back to login</Link>
      </div>
    </div>
  );
}
