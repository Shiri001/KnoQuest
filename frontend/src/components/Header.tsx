import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, RefreshCw, Wrench, Users, Shield, ChevronDown, Check, UserCircle, Mail } from 'lucide-react';
import type { HealthStatus, LanguageOption, EmployeePersona } from '../types/chat';

interface HeaderProps {
  health: HealthStatus | null;
  currentLanguage: string;
  onLanguageChange: (lang: string) => void;
  onResetConversation: () => void;
  onOpenTickets: () => void;
  onOpenDirectory: () => void;
  onOpenCommunications: () => void;
  onOpenAdmin: () => void;
  ticketsCount?: number;
  currentEmployee: EmployeePersona | null;
  availablePersonas: EmployeePersona[];
  onSelectPersona: (emp: EmployeePersona) => void;
}

export const LANGUAGES: LanguageOption[] = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी' },
  { code: 'pa', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ' },
  { code: 'es', name: 'Spanish', nativeName: 'Español' },
  { code: 'fr', name: 'French', nativeName: 'Français' },
];

export const Header: React.FC<HeaderProps> = ({
  health,
  currentLanguage,
  onLanguageChange,
  onResetConversation,
  onOpenTickets,
  onOpenDirectory,
  onOpenCommunications,
  onOpenAdmin,
  ticketsCount = 0,
  currentEmployee,
  availablePersonas,
  onSelectPersona,
}) => {
  const [isPersonaMenuOpen, setIsPersonaMenuOpen] = useState(false);
  const personaMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (personaMenuRef.current && !personaMenuRef.current.contains(event.target as Node)) {
        setIsPersonaMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const hasAdminPermission = currentEmployee?.effective_permissions?.includes('admin.manage_employees') || currentEmployee?.role === 'Admin';

  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-logo-badge" title="KnoQuest — Enterprise Knowledge & Employee Agent">
          <Sparkles size={22} />
        </div>
        <div className="brand-info">
          <h1>KnoQuest</h1>
          <p>
            Enterprise Knowledge Agent
            <span className="company-tag">NovaTech Solutions</span>
          </p>
        </div>
      </div>

      <div className="header-actions">
        {health ? (
          <div className="status-badge" title={`Mode: ${health.mode} | Loaded: ${health.enterprise_docs_loaded} chunks`}>
            <span className="pulse-dot" />
            <span>
              {health.azure_configured ? 'Azure Foundry Connected' : `Enterprise Sandbox (${health.enterprise_docs_loaded} Chunks)`}
            </span>
          </div>
        ) : (
          <div className="status-badge" style={{ borderColor: '#6B7280', color: '#9CA3AF' }}>
            <span>Connecting...</span>
          </div>
        )}

        <button
          className="header-tool-btn"
          onClick={onOpenTickets}
          title="Open IT Support Tickets Helpdesk"
        >
          <Wrench size={15} />
          <span>IT Tickets</span>
          {ticketsCount > 0 && <span className="header-badge-count">{ticketsCount}</span>}
        </button>

        <button
          className="header-tool-btn"
          onClick={onOpenDirectory}
          title="Search NovaTech Employee Directory"
        >
          <Users size={15} />
          <span>Directory</span>
        </button>

        <button
          className="header-tool-btn"
          onClick={onOpenCommunications}
          title="Open Microsoft Outlook (Inbox, Drafts, Sent)"
        >
          <Mail size={15} />
          <span>Outlook</span>
        </button>

        {/* Top Team Admin Button */}
        <button
          className={`header-tool-btn admin-btn ${hasAdminPermission ? 'highlight' : ''}`}
          onClick={onOpenAdmin}
          title="Open Top Team / Admin Access & Permissions Console"
        >
          <Shield size={15} />
          <span>Admin Console</span>
        </button>

        <div className="language-select-wrapper">
          <select
            className="language-select"
            value={currentLanguage}
            onChange={(e) => onLanguageChange(e.target.value)}
            title="Select interaction language"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name} ({lang.nativeName})
              </option>
            ))}
          </select>
        </div>

        {/* Authenticated Employee Badge & Persona Switcher */}
        {currentEmployee && (
          <div className="persona-switcher-wrapper" ref={personaMenuRef}>
            <div
              className="user-identity-card"
              onClick={() => setIsPersonaMenuOpen(!isPersonaMenuOpen)}
              title="Click to switch employee identity & test permissions"
            >
              <div className="user-avatar-small">
                <UserCircle size={20} />
              </div>
              <div className="user-info-text">
                <div className="user-name-line">
                  <span className="user-name">{currentEmployee.name}</span>
                  <ChevronDown size={13} className={`chevron-icon ${isPersonaMenuOpen ? 'rotated' : ''}`} />
                </div>
                <div className="user-meta-line">
                  <span className="user-emp-id">{currentEmployee.employee_id}</span>
                  <span className="user-dept-role">• {currentEmployee.department} ({currentEmployee.role})</span>
                </div>
              </div>
            </div>

            {/* Persona Switcher Dropdown */}
            {isPersonaMenuOpen && (
              <div className="persona-dropdown-menu">
                <div className="dropdown-header">
                  <span>Switch Employee Persona</span>
                  <span className="demo-tag">Prototype IAM</span>
                </div>
                <div className="persona-dropdown-list">
                  {availablePersonas.map((persona) => {
                    const isCurrent = persona.employee_id === currentEmployee.employee_id;
                    return (
                      <div
                        key={persona.employee_id}
                        className={`persona-item ${isCurrent ? 'active' : ''}`}
                        onClick={() => {
                          onSelectPersona(persona);
                          setIsPersonaMenuOpen(false);
                        }}
                      >
                        <div className="persona-item-info">
                          <div className="persona-item-name">
                            <span>{persona.name}</span>
                            <span className={`role-badge role-${persona.role.toLowerCase()}`}>{persona.role}</span>
                          </div>
                          <div className="persona-item-sub">
                            <span>{persona.full_id}</span> • <span>{persona.department}</span>
                          </div>
                          <div className="persona-item-desig">{persona.designation}</div>
                        </div>
                        {isCurrent && <Check size={16} className="persona-check-icon" />}
                      </div>
                    );
                  })}
                </div>
                <div className="dropdown-footer">
                  <span>Switching persona re-authenticates the agent session with that user's exact permissions.</span>
                </div>
              </div>
            )}
          </div>
        )}

        <button
          className="icon-btn"
          onClick={onResetConversation}
          title="New Conversation (Reset Context)"
        >
          <RefreshCw size={16} />
        </button>
      </div>
    </header>
  );
};
