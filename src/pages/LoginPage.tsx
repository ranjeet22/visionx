import React, { useState } from 'react';
import { ScanLine, ArrowLeft, ArrowRight, Eye, EyeOff, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useRouter } from '../lib/useRouter';
import { useAuth } from '../context/useAuth';
import { Button } from '../components/ui/Button';
import './LoginPage.css';

export const LoginPage: React.FC = () => {
  const { navigate, routeState } = useRouter();
  const { login, isAuthenticated } = useAuth();

  const [identifier, setIdentifier] = useState(routeState?.identifier || '');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If already authenticated, redirect to /scan or intended page
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/scan');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setError('Please provide your User ID or Email, and your password.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const res = await login({ identifier: identifier.trim(), password });
      if (res.success) {
        navigate('/scan');
      } else if (res.requires_verification) {
        // Account unverified: navigate to OTP verification screen
        navigate('/verify-otp', {
          identifier: res.user?.email || identifier,
          maskedEmail: res.masked_email,
          notice: 'Your account requires email verification before logging in.',
        });
      } else {
        setError(res.error || 'Invalid credentials. Please verify your details.');
      }
    } catch (err: any) {
      setError(err.message || 'Unable to connect to authentication server.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page-wrapper">
      {/* Top Bar */}
      <header className="auth-top-bar">
        <div className="auth-nav-inner">
          <button
            type="button"
            className="auth-back-btn"
            onClick={() => navigate('/')}
            aria-label="Back to home"
          >
            <ArrowLeft size={18} strokeWidth={2.5} />
            <span>Home</span>
          </button>

          <a href="#" onClick={(e) => { e.preventDefault(); navigate('/'); }} className="auth-brand">
            <span className="auth-logo-box">
              <ScanLine size={18} strokeWidth={2.5} />
            </span>
            <span className="auth-logo-text">
              Vision<span className="auth-logo-x">X</span>
            </span>
          </a>

          <div style={{ width: 80 }} />
        </div>
      </header>

      {/* Main Login Card */}
      <main className="auth-main-container">
        <div className="auth-card">
          <div className="auth-card-badge">
            <span>SECURE ACCESS</span>
          </div>

          <h1 className="auth-card-title">Welcome Back</h1>
          <p className="auth-card-subtitle">
            Log in with your User ID or email to access the VisionX vision scanner & assistant.
          </p>

          {routeState?.successMessage && (
            <div className="auth-alert alert-success">
              <CheckCircle2 size={18} strokeWidth={2.5} />
              <span>{routeState.successMessage}</span>
            </div>
          )}

          {error && (
            <div className="auth-alert alert-error">
              <AlertCircle size={18} strokeWidth={2.5} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form" noValidate>
            {/* Identifier (User ID or Email) */}
            <div className="auth-form-group">
              <label htmlFor="login-identifier" className="auth-label">
                User ID or Email Address
              </label>
              <input
                id="login-identifier"
                type="text"
                className="auth-input"
                placeholder="e.g. eco_warrior or user@domain.com"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                disabled={isLoading}
                autoComplete="username"
                required
              />
            </div>

            {/* Password */}
            <div className="auth-form-group">
              <div className="auth-label-row">
                <label htmlFor="login-password" className="auth-label">
                  Password
                </label>
              </div>
              <div className="auth-input-password-wrapper">
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  className="auth-input input-with-toggle"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="auth-submit-btn"
              disabled={isLoading}
              icon={<ArrowRight size={18} strokeWidth={2.5} />}
            >
              {isLoading ? 'Verifying Credentials...' : 'Log In to VisionX'}
            </Button>
          </form>

          {/* Footer Navigation */}
          <div className="auth-card-footer">
            <span>Don't have an account yet?</span>
            <button
              type="button"
              className="auth-link-btn"
              onClick={() => navigate('/register')}
            >
              Sign Up for Free
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};
