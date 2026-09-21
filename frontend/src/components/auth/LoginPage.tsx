import React, { useState } from 'react';
import type { EmployeePersona } from '../../types/chat';
import { loginEmployee } from '../../services/api';
import { Shield, Building2, Eye, EyeOff, KeyRound, CheckCircle2, AlertTriangle, X, Lock, ArrowRight } from 'lucide-react';

interface LoginPageProps {
  onLoginSuccess: (user: EmployeePersona) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [companyId, setCompanyId] = useState('NOVA');
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForgotModal, setShowForgotModal] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanComp = companyId.trim().toUpperCase();
    const cleanId = identifier.trim();
    const cleanPw = password;

    if (!cleanComp) {
      setError('Please enter your Company Code.');
      return;
    }
    if (!cleanId) {
      setError('Please enter your Employee ID or corporate email address.');
      return;
    }
    if (!cleanPw) {
      setError('Please enter your password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await loginEmployee(cleanComp, cleanId, cleanPw);
      onLoginSuccess(response.employee);
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-split-page">
      {/* Background Ambience */}
      <div className="login-ambient-orb orb-1"></div>
      <div className="login-ambient-orb orb-2"></div>

      <div className="login-split-card">
        {/* Left Hero Brand Panel */}
        <div className="login-hero-panel">
          <div className="hero-brand-header">
            <div className="hero-logo-box">
              <Building2 className="hero-logo-icon" size={28} />
            </div>
            <div className="hero-brand-meta">
              <span className="hero-company-name">NovaTech Solutions</span>
              <h1 className="hero-app-title">KnoQuest</h1>
            </div>
          </div>

          <div className="hero-tagline-block">
            <span className="hero-badge">ENTERPRISE COGNITIVE WORKSPACE</span>
            <h2 className="hero-heading">
              Secure, grounded employee intelligence powered by Azure Foundry.
            </h2>
            <p className="hero-description">
              Access your personalized workspace with role-governed internal knowledge,
              corporate tools, IT support, calendar sync, and Microsoft Outlook integration.
            </p>
          </div>

          <div className="hero-features-list">
            <div className="hero-feature-item">
              <div className="feature-icon-box">
                <Shield size={18} />
              </div>
              <div className="feature-text">
                <strong>Zero-Trust Perimeter & RBAC</strong>
                <span>Server-enforced authorization and Argon2id session security</span>
              </div>
            </div>

            <div className="hero-feature-item">
              <div className="feature-icon-box">
                <CheckCircle2 size={18} />
              </div>
              <div className="feature-text">
                <strong>Model-Context-Protocol (MCP)</strong>
                <span>Direct authorized tools for Calendar, Mail, IT Tickets, and HR Records</span>
              </div>
            </div>

            <div className="hero-feature-item">
              <div className="feature-icon-box">
                <KeyRound size={18} />
              </div>
              <div className="feature-text">
                <strong>Strict Session Guarding</strong>
                <span>HttpOnly tamper-proof tokens with automated lockout defense</span>
              </div>
            </div>
          </div>

          <div className="hero-footer-meta">
            <span className="security-tag">
              <Shield size={13} />
              SOC2 Type II • NIST-Compliant Hashing
            </span>
            <span className="version-tag">KnoQuest v2.0 Enterprise</span>
          </div>
        </div>

        {/* Right Form Panel */}
        <div className="login-form-panel">
          <div className="form-panel-header">
            <h3 className="form-panel-title">Employee Portal Sign-In</h3>
            <p className="form-panel-subtitle">
              Enter your corporate credentials to verify identity and authenticate.
            </p>
          </div>

          {error && (
            <div className="login-alert-banner" role="alert">
              <AlertTriangle size={18} className="alert-icon" />
              <div className="alert-message">{error}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="login-enterprise-form">
            {/* Company ID Input */}
            <div className="form-group">
              <label htmlFor="companyId" className="form-label">Company Code</label>
              <div className="form-input-container">
                <input
                  id="companyId"
                  type="text"
                  className="form-input text-uppercase"
                  placeholder="e.g. NOVA"
                  value={companyId}
                  onChange={(e) => setCompanyId(e.target.value.toUpperCase())}
                  disabled={loading}
                  maxLength={10}
                  required
                />
              </div>
            </div>

            {/* Employee ID or Corporate Email */}
            <div className="form-group">
              <label htmlFor="identifier" className="form-label">Employee ID or Corporate Email</label>
              <div className="form-input-container">
                <input
                  id="identifier"
                  type="text"
                  className="form-input"
                  placeholder="e.g. EMP001 or rahul.sharma@novatech.com"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  disabled={loading}
                  autoComplete="username"
                  autoFocus
                  required
                />
              </div>
            </div>

            {/* Password Input */}
            <div className="form-group">
              <div className="label-with-action">
                <label htmlFor="password" className="form-label">Password</label>
                <button
                  type="button"
                  className="forgot-link-btn"
                  onClick={() => setShowForgotModal(true)}
                  tabIndex={-1}
                >
                  Forgot password?
                </button>
              </div>
              <div className="form-input-container">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className="form-input has-eye-toggle"
                  placeholder="Enter corporate password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="input-eye-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button type="submit" className="login-action-btn" disabled={loading}>
              {loading ? (
                <>
                  <span className="btn-spinner"></span>
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <span>Authenticate & Launch Workspace</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div className="login-security-notice">
            <Lock size={12} />
            <span>
              Sessions are cryptographically signed with Argon2id and stored in protected HttpOnly cookies.
              Five consecutive failed attempts trigger an automated 15-minute security lockout.
            </span>
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className="modal-backdrop-overlay" onClick={() => setShowForgotModal(false)}>
          <div className="forgot-password-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-icon-badge">
                <KeyRound size={22} />
              </div>
              <div className="modal-title-group">
                <h3>Enterprise Credential Recovery</h3>
                <p>NovaTech Security & IT Administration Policy</p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowForgotModal(false)}
                aria-label="Close dialog"
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <p>
                In compliance with NovaTech Zero-Trust Security Policies, self-service employee
                password resets are disabled.
              </p>
              <div className="recovery-contacts-card">
                <h4>Contact Authorized Administration:</h4>
                <ul>
                  <li>
                    <strong>IT Operations Tier-1 Helpdesk</strong>
                    <span>Extension: 4220 • Email: <code>it-support@novatech.com</code></span>
                  </li>
                  <li>
                    <strong>Human Resources & People Ops</strong>
                    <span>Extension: 4101 • Email: <code>hr@novatech.com</code></span>
                  </li>
                  <li>
                    <strong>Security Operations / Top Team</strong>
                    <span>Chief Information Security Officer: <code>ciso@novatech.com</code></span>
                  </li>
                </ul>
              </div>
              <p className="modal-note">
                Please have your Government ID or Employee Badge ready for identity verification
                before your temporary access token is issued.
              </p>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="modal-dismiss-btn"
                onClick={() => setShowForgotModal(false)}
              >
                Understood, Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
