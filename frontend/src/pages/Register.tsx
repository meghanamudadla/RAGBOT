import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useRegister, useGoogleAuthStatus } from '../hooks/useAuth';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const registerMutation = useRegister();
  const { data: googleStatus } = useGoogleAuthStatus();
  const googleConfigured = googleStatus?.configured === true;
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    registerMutation.mutate(
      { email, password },
      {
        onSuccess: () => navigate('/'),
        onError: (err: any) => {
          let msg = err.response?.data?.detail || 'Registration failed';
          if (Array.isArray(msg)) msg = msg[0]?.msg || msg;
          setError(msg);
        },
      }
    );
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="w-full max-w-md p-8 rounded-xl bg-slate-900 border border-slate-800 shadow-xl">
        <h2 className="text-3xl font-bold text-white mb-6 text-center">Create Account</h2>
        {error && (
          <div className="bg-red-900/30 border border-red-500/50 text-red-500 p-3 rounded-md mb-4 text-sm font-medium">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-md outline-none focus:border-blue-500 text-white transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-md outline-none focus:border-blue-500 text-white transition-colors"
              placeholder="Minimum 8 characters"
            />
          </div>
          <button
            type="submit"
            disabled={registerMutation.isPending}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-md transition-colors disabled:opacity-50"
          >
            {registerMutation.isPending ? 'Creating Account...' : 'Register'}
          </button>
        </form>

        {googleConfigured && (
          <>
            <div className="flex items-center gap-3 my-6">
              <div className="flex-1 h-px bg-slate-800" />
              <span className="text-xs text-slate-500">or</span>
              <div className="flex-1 h-px bg-slate-800" />
            </div>

            <a
              href="/api/v1/auth/google/login"
              className="w-full flex items-center justify-center gap-3 bg-white hover:bg-slate-100 text-slate-800 font-semibold py-2.5 rounded-md transition-colors"
            >
              <GoogleIcon />
              Continue with Google
            </a>
          </>
        )}

        <p className="mt-6 text-center text-sm text-slate-400">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-500 hover:text-blue-400 hover:underline">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}