import React, { useState } from 'react';
import { ScanLine, ArrowLeft, ArrowRight, Eye, EyeOff, AlertCircle, Check, X } from 'lucide-react';
import { useRouter } from '../lib/useRouter';
import { useAuth } from '../context/useAuth';
import { Button } from '../components/ui/Button';
import './RegisterPage.css';

export const RegisterPage: React.FC = () => {
  const { navigate } = useRouter();
  const { register, isAuthenticated } = useAuth();

  const [userId, setUserId] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Password rules validation
  const hasMinLength = password.length >= 8;
  const hasLetter = /[a-zA-Z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  // If already authenticated, redirect
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/scan');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Frontend validations
    const cleanUserId = userId.trim();
    const cleanEmail = email.trim().toLowerCase();

    if (!cleanUserId || !cleanEmail || !password || !confirmPassword) {
      setError('All fields are required.');
      return;
    }

    if (cleanUserId.length < 3 || cleanUserId.length > 32) {
      setError('User ID must be between 3 and 32 characters.');
      return;
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(cleanUserId)) {
      setError('User ID can only contain letters, numbers, underscores, or hyphens.');
      return;
    }

    if (!hasMinLength || !hasLetter || !hasNumber) {
      setError('Password must be at least 8 characters long and contain both letters and numbers.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);

    try {
      const res = await register({
        user_id: cleanUserId,
        email: cleanEmail,
        password,
        confirm_password: confirmPassword,
      });

      if (res.success) {
        // Transition directly to OTP verification screen
        navigate('/verify-otp', {
          identifier: cleanEmail,
          userId: cleanUserId,
          maskedEmail: res.masked_email,
          cooldownSeconds: res.cooldown_seconds || 60,
          devOtp: res.email_delivery?.dev_otp,
          smtpConfigured: res.email_delivery?.smtp_configured,
        });
      } else {
        setError(res.error || 'Registration failed. Please check your inputs.');
      }
    } catch (err: any) {
      setError(err.message || 'Unable to connect to registration server.');
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

      {/* Main Registration Card */}
      <main className="auth-main-container">
        <div className="auth-card register-card">
          <div className="auth-card-badge">
            <span>GET STARTED</span>
          </div>

          <h1 className="auth-card-title">Create Account</h1>
          <p className="auth-card-subtitle">
            Join VisionX to classify waste, identify materials, and get real-time disposal guidance.
          </p>

          {error && (
            <div className="auth-alert alert-error">
              <AlertCircle size={18} strokeWidth={2.5} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form" noValidate>
            {/* User ID */}
            <div className="auth-form-group">
              <label htmlFor="reg-userid" className="auth-label">
                User ID <span className="label-hint">(unique username)</span>
              </label>
              <input
                id="reg-userid"
                type="text"
                className="auth-input"
                placeholder="e.g. eco_warrior"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                disabled={isLoading}
                autoComplete="username"
                required
              />
            </div>

            {/* Email Address */}
            <div className="auth-form-group">
              <label htmlFor="reg-email" className="auth-label">
                Email Address <span className="label-hint">(for OTP verification)</span>
              </label>
              <input
                id="reg-email"
                type="email"
                className="auth-input"
                placeholder="you@domain.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
                autoComplete="email"
                required
              />
            </div>

            {/* Password */}
            <div className="auth-form-group">
              <label htmlFor="reg-password" className="auth-label">
                Password
              </label>
              <div className="auth-input-password-wrapper">
                <input
                  id="reg-password"
                  type={showPassword ? 'text' : 'password'}
                  className="auth-input input-with-toggle"
                  placeholder="At least 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  autoComplete="new-password"
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

            {/* Confirm Password */}
            <div className="auth-form-group">
              <label htmlFor="reg-confirm-password" className="auth-label">
                Confirm Password
              </label>
              <div className="auth-input-password-wrapper">
                <input
                  id="reg-confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  className="auth-input input-with-toggle"
                  placeholder="Re-enter your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isLoading}
                  autoComplete="new-password"
                  required
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                >
                  {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Live Password Requirements Checklist */}
            <div className="password-checklist">
              <div className={`checklist-item ${hasMinLength ? 'item-pass' : ''}`}>
                {hasMinLength ? <Check size={14} strokeWidth={3} /> : <X size={14} strokeWidth={3} />}
                <span>8+ characters</span>
              </div>
              <div className={`checklist-item ${hasLetter && hasNumber ? 'item-pass' : ''}`}>
                {hasLetter && hasNumber ? <Check size={14} strokeWidth={3} /> : <X size={14} strokeWidth={3} />}
                <span>Letters & numbers</span>
              </div>
              <div className={`checklist-item ${passwordsMatch ? 'item-pass' : ''}`}>
                {passwordsMatch ? <Check size={14} strokeWidth={3} /> : <X size={14} strokeWidth={3} />}
                <span>Passwords match</span>
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
              {isLoading ? 'Creating Account & Sending OTP...' : 'Send Verification OTP'}
            </Button>
          </form>

          {/* Footer Navigation */}
          <div className="auth-card-footer">
            <span>Already have an account?</span>
            <button
              type="button"
              className="auth-link-btn"
              onClick={() => navigate('/login')}
            >
              Log In
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};
