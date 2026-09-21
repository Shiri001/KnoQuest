import React from 'react';
import type { EmployeePersona } from '../types/chat';
import type { WorkspaceView } from '../components/layout/Sidebar';

interface DashboardViewProps {
  currentUser: EmployeePersona;
  onNavigate: (view: WorkspaceView) => void;
  onQuickAsk: (prompt: string) => void;
  draftsCount?: number;
  ticketsCount?: number;
  policyCount?: number;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  currentUser,
  onNavigate,
  onQuickAsk,
  draftsCount = 0,
  ticketsCount = 0,
  policyCount = 8,
}) => {
  const currentDateStr = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const quickActions = [
    {
      title: 'Ask AI Agent',
      desc: 'Ground questions against NovaTech policies & records',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      ),
      action: () => onNavigate('chat'),
      variant: 'blue',
    },
    {
      title: 'Corporate Email & Drafts',
      desc: `${draftsCount} pending draft(s) in your Outlook workspace`,
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
          <polyline points="22,6 12,13 2,6"></polyline>
        </svg>
      ),
      action: () => onNavigate('communications'),
      variant: 'cyan',
    },
    {
      title: 'IT Helpdesk & Equipment',
      desc: `${ticketsCount} active IT ticket(s) recorded`,
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
        </svg>
      ),
      action: () => onNavigate('tickets'),
      variant: 'amber',
    },
    {
      title: 'Calendar & Sync',
      desc: 'Check meeting schedules or book a conference room',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
          <line x1="16" y1="2" x2="16" y2="6"></line>
          <line x1="8" y1="2" x2="8" y2="6"></line>
          <line x1="3" y1="10" x2="21" y2="10"></line>
        </svg>
      ),
      action: () => onNavigate('calendar'),
      variant: 'emerald',
    },
  ];

  const suggestedPrompts = [
    { label: 'Check Remote Work Policy', prompt: 'What are the security requirements and core working hours for remote employees?' },
    { label: 'View Leave Entitlement', prompt: 'What is our annual leave policy and how many sick days do we get?' },
    { label: 'Travel Expense Guidelines', prompt: 'What are the daily meal allowances and flight booking rules for domestic business travel?' },
    { label: 'Draft Sprint Update', prompt: 'Draft email to team regarding Sprint Planning on Friday' },
  ];

  return (
    <div className="view-page-container dashboard-view">
      {/* Hero Welcome Banner */}
      <section className="dashboard-hero-card">
        <div className="hero-content">
          <div className="hero-date-badge">{currentDateStr}</div>
          <h1 className="hero-welcome-heading">
            Welcome back, <span className="highlight-name">{currentUser.name}</span>
          </h1>
          <p className="hero-welcome-sub">
            {currentUser.designation} • {currentUser.department} ({currentUser.full_id || currentUser.employee_id})
          </p>
          <p className="hero-intro-text">
            Your enterprise AI workspace is connected to NovaTech internal systems, policy indexes, and MCP service connectors.
          </p>
        </div>
        <div className="hero-stats-row">
          <div className="hero-stat-box">
            <span className="stat-number">{policyCount}</span>
            <span className="stat-label">Active Policies</span>
          </div>
          <div className="hero-stat-box">
            <span className="stat-number">{draftsCount}</span>
            <span className="stat-label">Outlook Drafts</span>
          </div>
          <div className="hero-stat-box">
            <span className="stat-number">{ticketsCount}</span>
            <span className="stat-label">IT Tickets</span>
          </div>
        </div>
      </section>

      {/* Quick Launch Cards */}
      <section className="dashboard-section">
        <h2 className="section-title">Quick Launch Services</h2>
        <div className="quick-actions-grid">
          {quickActions.map((qa, idx) => (
            <button
              key={idx}
              type="button"
              className={`quick-action-card border-accent-${qa.variant}`}
              onClick={qa.action}
            >
              <div className={`action-card-icon bg-accent-${qa.variant}`}>
                {qa.icon}
              </div>
              <div className="action-card-body">
                <div className="action-card-title">{qa.title}</div>
                <div className="action-card-desc">{qa.desc}</div>
              </div>
              <svg className="action-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </button>
          ))}
        </div>
      </section>

      {/* Two Column Grid: Quick AI Prompts & Company Announcements */}
      <div className="dashboard-grid-2col">
        {/* Suggested AI Prompts */}
        <div className="dashboard-card">
          <div className="card-header">
            <div className="card-header-icon blue">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
              </svg>
            </div>
            <h3>Ask KnoQuest AI</h3>
          </div>
          <p className="card-subtext">Click any prompt to launch conversational RAG with verified citations:</p>
          <div className="suggested-prompts-list">
            {suggestedPrompts.map((sp, idx) => (
              <button
                key={idx}
                type="button"
                className="suggested-prompt-btn"
                onClick={() => onQuickAsk(sp.prompt)}
              >
                <span className="prompt-tag">{sp.label}</span>
                <span className="prompt-text">"{sp.prompt}"</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </button>
            ))}
          </div>
        </div>

        {/* Corporate Notice & Identity Profile */}
        <div className="dashboard-card">
          <div className="card-header">
            <div className="card-header-icon emerald">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              </svg>
            </div>
            <h3>Identity & Security Status</h3>
          </div>
          <div className="identity-status-details">
            <div className="detail-row">
              <span className="detail-label">Security Principal:</span>
              <span className="detail-value mono">{currentUser.email}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Company / Tenant:</span>
              <span className="detail-value">{currentUser.company_id || 'NOVA'} (NovaTech Solutions)</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Assigned Role:</span>
              <span className="detail-value badge-role">{currentUser.role}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Active Permissions:</span>
              <div className="permissions-chips-wrap">
                {(currentUser.effective_permissions || []).map((perm) => (
                  <span key={perm} className="perm-chip">{perm}</span>
                ))}
              </div>
            </div>
          </div>
          <div className="notice-banner">
            <div className="notice-icon">ℹ️</div>
            <div className="notice-text">
              <strong>All MCP tool calls are authorized in real-time</strong> on the server. The AI Agent cannot execute actions beyond your assigned permissions.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
