import React from 'react';
import type { WorkspaceView } from './Sidebar';
import type { HealthStatus, LanguageOption, UploadedFile } from '../../types/chat';

interface TopNavProps {
  currentView: WorkspaceView;
  health: HealthStatus | null;
  currentLanguage: string;
  onLanguageChange: (lang: string) => void;
  activeUpload: UploadedFile | null;
  onClearUpload?: () => void;
  onOpenUploadModal?: () => void;
}

// Strictly 4 languages: English, Hindi, Spanish, French (Punjabi completely removed)
export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी' },
  { code: 'es', name: 'Spanish', nativeName: 'Español' },
  { code: 'fr', name: 'French', nativeName: 'Français' },
];

const VIEW_TITLES: Record<WorkspaceView, { title: string; subtitle: string }> = {
  dashboard: {
    title: 'Enterprise Dashboard',
    subtitle: 'NovaTech Solutions internal portal & operations center',
  },
  chat: {
    title: 'AI Agent Workspace',
    subtitle: 'Azure Foundry GPT-4.1-mini & Grounded Enterprise RAG Engine',
  },
  documents: {
    title: 'Enterprise Policies & Knowledge',
    subtitle: 'Indexed company documentation, codes of conduct, and guidelines',
  },
  communications: {
    title: 'Corporate Communications & Outlook',
    subtitle: 'Review drafts, send corporate announcements, and track inbox',
  },
  calendar: {
    title: 'Calendar & Meeting Scheduler',
    subtitle: 'Synchronized company schedule and team meeting appointments',
  },
  tickets: {
    title: 'IT Support Helpdesk',
    subtitle: 'Track hardware, access requests, and raise support tickets',
  },
  directory: {
    title: 'Employee Directory',
    subtitle: 'NovaTech team directory, extensions, and department contacts',
  },
  hr: {
    title: 'Human Resources & Time-Off',
    subtitle: 'Leave balances, salary bands, and payroll authorization',
  },
  admin: {
    title: 'Top Team Access Control Console',
    subtitle: 'Enterprise Employee Access Management & Dynamic Permission Overrides',
  },
};

export const TopNav: React.FC<TopNavProps> = ({
  currentView,
  health,
  currentLanguage,
  onLanguageChange,
  activeUpload,
  onClearUpload,
  onOpenUploadModal,
}) => {
  const info = VIEW_TITLES[currentView] || { title: 'Workspace', subtitle: 'NovaTech Portal' };
  const isAzure = health?.mode === 'azure_foundry' || health?.azure_configured;

  return (
    <header className="enterprise-topnav">
      {/* View Title & Breadcrumb */}
      <div className="topnav-title-area">
        <div className="topnav-breadcrumbs">
          <span className="breadcrumb-root">NovaTech</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-current">{info.title}</span>
        </div>
        <div className="topnav-subtitle">{info.subtitle}</div>
      </div>

      {/* Right Actions: Upload badge, Azure status, Language selector */}
      <div className="topnav-actions-area">
        {/* Active Upload Session Badge */}
        {activeUpload && (
          <div className="session-upload-badge" title={`Grounded with session document: ${activeUpload.filename}`}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
            <span className="session-doc-name">{activeUpload.filename}</span>
            {onClearUpload && (
              <button
                type="button"
                className="clear-upload-btn"
                onClick={onClearUpload}
                title="Remove session document"
              >
                ×
              </button>
            )}
          </div>
        )}

        {/* Upload Doc Action Button */}
        {onOpenUploadModal && !activeUpload && (
          <button
            type="button"
            className="topnav-upload-btn"
            onClick={onOpenUploadModal}
            title="Upload document for this chat session"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span>Upload Document</span>
          </button>
        )}

        {/* Azure Foundry Live Indicator */}
        <div className={`azure-status-pill ${isAzure ? 'status-online' : 'status-local'}`}>
          <span className="status-dot"></span>
          <span className="status-label">
            {isAzure ? 'Azure Foundry • GPT-4.1-mini' : 'Local Sandbox Engine'}
          </span>
        </div>

        {/* Language Selector */}
        <div className="language-selector-wrapper">
          <svg className="lang-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="2" y1="12" x2="22" y2="12"></line>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
          </svg>
          <select
            className="language-select"
            value={currentLanguage}
            onChange={(e) => onLanguageChange(e.target.value)}
            title="Select agent interaction language"
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name} ({lang.nativeName})
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
};
