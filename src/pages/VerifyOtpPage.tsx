import React, { useState, useEffect, useRef } from 'react';
import { ScanLine, ArrowLeft, CheckCircle2, AlertCircle, RefreshCw, Mail, ArrowRight } from 'lucide-react';
import { useRouter } from '../lib/useRouter';
import { useAuth } from '../context/useAuth';
import { Button } from '../components/ui/Button';
import './VerifyOtpPage.css';

export const VerifyOtpPage: React.FC = () => {
  const { navigate, routeState } = useRouter();
  const { verifyOtp, resendOtp, isAuthenticated } = useAuth();

  const identifier = routeState?.identifier || '';
  const maskedEmail = routeState?.maskedEmail || identifier || 'your email';

  // 6 separate digit slots for tactile neo-brutalist interaction
  const [digits, setDigits] = useState<string[]>(['', '', '', '', '', '']);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendSuccess, setResendSuccess] = useState<string | null>(null);
  const [devOtp, setDevOtp] = useState<string | null>(routeState?.devOtp || null);

  // 60-second cooldown timer
  const [cooldown, setCooldown] = useState<number>(routeState?.cooldownSeconds || 60);

  // If already authenticated, redirect
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/scan');
    }
  }, [isAuthenticated, navigate]);

  // Countdown timer effect
  useEffect(() => {
    if (cooldown <= 0) return;
    const interval = setInterval(() => {
      setCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldown]);

  // Auto-focus first digit on load
  useEffect(() => {
    if (inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, []);

  const handleDigitChange = (index: number, val: string) => {
    // Only accept numeric characters
    const cleanChar = val.replace(/\D/g, '').slice(-1);
    const newDigits = [...digits];
    newDigits[index] = cleanChar;
    setDigits(newDigits);
    setError(null);

    // Auto-advance focus to next input
    if (cleanChar && index < 5 && inputRefs.current[index + 1]) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      if (!digits[index] && index > 0 && inputRefs.current[index - 1]) {
        const newDigits = [...digits];
        newDigits[index - 1] = '';
        setDigits(newDigits);
        inputRefs.current[index - 1]?.focus();
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pastedData) return;

    const newDigits = [...digits];
    for (let i = 0; i < 6; i++) {
      newDigits[i] = pastedData[i] || '';
    }
    setDigits(newDigits);

    // Focus last filled or 6th input
    const nextIdx = Math.min(pastedData.length, 5);
    inputRefs.current[nextIdx]?.focus();
  };

  const fullOtp = digits.join('');

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (fullOtp.length !== 6) {
      setError('Please enter all 6 digits of your verification code.');
      return;
    }

    if (!identifier) {
      setError('Missing session identifier. Please return to the registration screen.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const res = await verifyOtp(identifier, fullOtp);
      if (res.success) {
        navigate('/scan');
      } else {
        setError(res.error || 'Verification failed. Please check the code.');
      }
    } catch (err: any) {
      setError(err.message || 'Unable to connect to verification server.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0 || isResending) return;
    if (!identifier) {
      setError('Missing account identifier. Please return to registration.');
      return;
    }

    setIsResending(true);
    setError(null);
    setResendSuccess(null);

    try {
      const res = await resendOtp(identifier);
      if (res.success) {
        setResendSuccess('A new 6-digit OTP code has been dispatched.');
        if (res.email_delivery?.dev_otp) {
          setDevOtp(res.email_delivery.dev_otp);
        }
        setCooldown(60);
      } else {
        setError(res.error || 'Failed to resend code. Please try again.');
      }
    } catch (err: any) {
      setError(err.message || 'Error communicating with server.');
    } finally {
      setIsResending(false);
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
            onClick={() => navigate('/register')}
            aria-label="Back to registration"
          >
            <ArrowLeft size={18} strokeWidth={2.5} />
            <span>Sign Up</span>
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

      {/* Main OTP Card */}
      <main className="auth-main-container">
        <div className="auth-card otp-card">
          <div className="auth-card-badge">
            <span>EMAIL VERIFICATION</span>
          </div>

          <h1 className="auth-card-title">Check Your Inbox</h1>
          <p className="auth-card-subtitle">
            We sent a time-limited 6-digit verification code to:
          </p>

          <div className="otp-email-chip">
            <Mail size={16} strokeWidth={2.5} />
            <span className="otp-email-text">{maskedEmail}</span>
          </div>

          {devOtp && (
            <div className="auth-alert alert-dev-otp">
              <div className="dev-otp-header">
                <span className="dev-tag">LOCAL DEV OTP</span>
                <span className="dev-hint">SMTP not configured in .env</span>
              </div>
              <div className="dev-otp-content">
                <span>Enter this code below:</span>
                <strong className="dev-code-highlight">{devOtp}</strong>
              </div>
            </div>
          )}

          {routeState?.notice && (
            <div className="auth-alert alert-info">
              <span>{routeState.notice}</span>
            </div>
          )}

          {resendSuccess && (
            <div className="auth-alert alert-success">
              <CheckCircle2 size={18} strokeWidth={2.5} />
              <span>{resendSuccess}</span>
            </div>
          )}

          {error && (
            <div className="auth-alert alert-error">
              <AlertCircle size={18} strokeWidth={2.5} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleVerify} className="otp-form" noValidate>
            {/* 6 Digit Input Group */}
            <div className="otp-digits-row" onPaste={handlePaste}>
              {digits.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => { inputRefs.current[idx] = el; }}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={1}
                  className={`otp-digit-box ${digit ? 'digit-filled' : ''}`}
                  value={digit}
                  onChange={(e) => handleDigitChange(idx, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(idx, e)}
                  disabled={isLoading}
                  autoComplete="one-time-code"
                  aria-label={`Digit ${idx + 1}`}
                />
              ))}
            </div>

            <p className="otp-expiry-hint">
              Code expires in <strong>5 minutes</strong>.
            </p>

            {/* Verify Button */}
            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="auth-submit-btn"
              disabled={isLoading || fullOtp.length !== 6}
              icon={<ArrowRight size={18} strokeWidth={2.5} />}
            >
              {isLoading ? 'Verifying Code...' : 'Verify & Activate Account'}
            </Button>
          </form>

          {/* Resend Cooldown Section */}
          <div className="otp-resend-section">
            <button
              type="button"
              className="resend-otp-btn"
              onClick={handleResend}
              disabled={cooldown > 0 || isResending}
            >
              <RefreshCw size={15} className={isResending ? 'spin-icon' : ''} />
              {cooldown > 0
                ? `Resend Code in ${cooldown}s`
                : isResending
                ? 'Sending Code...'
                : 'Resend Verification Code'}
            </button>
          </div>

          {/* Footer Back Link */}
          <div className="auth-card-footer">
            <span>Wrong email address?</span>
            <button
              type="button"
              className="auth-link-btn"
              onClick={() => navigate('/register')}
            >
              Return to Registration
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};
