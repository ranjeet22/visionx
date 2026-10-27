import React, { useState } from 'react';
import { Menu, X, ArrowUpRight, ScanLine, LogOut, User as UserIcon } from 'lucide-react';
import { Button } from '../ui/Button';
import { useRouter } from '../../lib/useRouter';
import { useAuth } from '../../context/useAuth';
import './Navbar.css';

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { navigate } = useRouter();
  const { user, isAuthenticated, logout } = useAuth();

  const navLinks = [
    { label: 'The Problem', href: '#problem' },
    { label: 'Demo', href: '#demo' },
    { label: 'Capabilities', href: '#capabilities' },
    { label: 'Architecture', href: '#pipeline' },
    { label: 'AWS & Agents', href: '#aws-agents' },
    { label: 'Tech Stack', href: '#stack' },
  ];

  const handleLinkClick = () => {
    setMobileMenuOpen(false);
  };

  const handleOpenScanner = () => {
    setMobileMenuOpen(false);
    navigate('/scan');
  };

  return (
    <header className="navbar-wrapper">
      <div className="navbar-container">
        <nav className="floating-navbar" aria-label="Main Navigation">
          {/* Brand Logo Mark */}
          <a href="#" className="nav-brand" aria-label="VisionX Home">
            <span className="logo-icon-box">
              <ScanLine size={20} strokeWidth={2.5} />
            </span>
            <span className="logo-text">
              Vision<span className="logo-x">X</span>
            </span>
            <span className="logo-tag">DEV</span>
          </a>

          {/* Desktop Navigation Links */}
          <ul className="nav-links-desktop">
            {navLinks.map((link) => (
              <li key={link.href}>
                <a href={link.href} className="nav-link">
                  {link.label}
                </a>
              </li>
            ))}
          </ul>

          {/* Right Action: Auth-aware */}
          <div className="nav-actions-desktop">
            {isAuthenticated && user ? (
              <div className="nav-auth-group">
                <span className="nav-user-chip" title={user.email}>
                  <UserIcon size={14} strokeWidth={2.5} />
                  <span>{user.user_id}</span>
                </span>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleOpenScanner}
                  icon={<ArrowUpRight size={16} strokeWidth={2.5} />}
                >
                  Scanner
                </Button>
                <button
                  type="button"
                  className="nav-logout-btn"
                  onClick={logout}
                  title="Log out of VisionX"
                  aria-label="Log out"
                >
                  <LogOut size={16} strokeWidth={2.5} />
                </button>
              </div>
            ) : (
              <div className="nav-auth-group">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => navigate('/login')}
                >
                  Log In
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleOpenScanner}
                  icon={<ArrowUpRight size={16} strokeWidth={2.5} />}
                >
                  Launch Scanner
                </Button>
              </div>
            )}
          </div>

          {/* Mobile Hamburger Toggle Button */}
          <button
            type="button"
            className="mobile-toggle-btn"
            aria-label={mobileMenuOpen ? 'Close Navigation Menu' : 'Open Navigation Menu'}
            aria-expanded={mobileMenuOpen}
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X size={22} strokeWidth={2.5} /> : <Menu size={22} strokeWidth={2.5} />}
          </button>
        </nav>
      </div>

      {/* Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div className="mobile-dropdown" role="dialog" aria-modal="true">
          <ul className="mobile-nav-list">
            {navLinks.map((link) => (
              <li key={link.href}>
                <a href={link.href} className="mobile-nav-link" onClick={handleLinkClick}>
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
          <div className="mobile-cta-wrapper">
            {isAuthenticated && user ? (
              <div className="mobile-auth-controls">
                <div className="mobile-user-row">
                  <UserIcon size={16} />
                  <span>Signed in as <strong>{user.user_id}</strong></span>
                </div>
                <Button
                  variant="primary"
                  size="md"
                  onClick={handleOpenScanner}
                  icon={<ArrowUpRight size={18} strokeWidth={2.5} />}
                >
                  Open Scanner
                </Button>
                <Button
                  variant="secondary"
                  size="md"
                  onClick={() => { setMobileMenuOpen(false); logout(); }}
                  icon={<LogOut size={16} />}
                >
                  Log Out
                </Button>
              </div>
            ) : (
              <div className="mobile-auth-controls">
                <Button
                  variant="primary"
                  size="md"
                  onClick={handleOpenScanner}
                  icon={<ArrowUpRight size={18} strokeWidth={2.5} />}
                >
                  Launch Scanner
                </Button>
                <Button
                  variant="secondary"
                  size="md"
                  onClick={() => { setMobileMenuOpen(false); navigate('/login'); }}
                >
                  Log In / Sign Up
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
