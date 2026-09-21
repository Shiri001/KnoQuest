import React from 'react';
import type { EmployeePersona } from '../../types/chat';

export type WorkspaceView =
  | 'dashboard'
  | 'chat'
  | 'documents'
  | 'communications'
  | 'calendar'
  | 'tickets'
  | 'directory'
  | 'hr'
  | 'admin';

interface SidebarProps {
  currentView: WorkspaceView;
  onNavigate: (view: WorkspaceView) => void;
  currentUser: EmployeePersona;
  onLogout: () => void;
  unreadDraftsCount?: number;
  openTicketsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onNavigate,
  currentUser,
  onLogout,
  unreadDraftsCount = 0,
  openTicketsCount = 0,
}) => {
  const perms = currentUser.effective_permissions || [];
  const isAdmin = currentUser.role === 'Admin' || perms.includes('admin.access') || perms.includes('role.manage');
  const hasHrAccess = perms.includes('hr.self') || perms.includes('hr.team') || perms.includes('hr.all');

  const navItems: {
    id: WorkspaceView;
    label: string;
    icon: React.ReactNode;
    badge?: number | string;
    badgeVariant?: 'blue' | 'amber' | 'emerald';
    visible: boolean;
  }[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7"></rect>
          <rect x="14" y="3" width="7" height="7"></rect>
          <rect x="14" y="14" width="7" height="7"></rect>
          <rect x="3" y="14" width="7" height="7"></rect>
        </svg>
      ),
      visible: true,
    },
    {
      id: 'chat',
      label: 'AI Agent Workspace',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          <path d="M9.5 9h.01"></path>
          <path d="M14.5 9h.01"></path>
        </svg>
      ),
      badge: 'Live',
      badgeVariant: 'emerald',
      visible: true,
    },
    {
      id: 'documents',
      label: 'Knowledge & Policies',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
        </svg>
      ),
      visible: true,
    },
    {
      id: 'communications',
      label: 'Outlook & Drafts',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
          <polyline points="22,6 12,13 2,6"></polyline>
        </svg>
      ),
      badge: unreadDraftsCount > 0 ? `${unreadDraftsCount} drafts` : undefined,
      badgeVariant: 'blue',
      visible: true,
    },
    {
      id: 'calendar',
      label: 'Calendar & Sync',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
          <line x1="16" y1="2" x2="16" y2="6"></line>
          <line x1="8" y1="2" x2="8" y2="6"></line>
          <line x1="3" y1="10" x2="21" y2="10"></line>
        </svg>
      ),
      visible: true,
    },
    {
      id: 'tickets',
      label: 'IT Support Helpdesk',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
        </svg>
      ),
      badge: openTicketsCount > 0 ? `${openTicketsCount} tickets` : undefined,
      badgeVariant: 'amber',
      visible: true,
    },
    {
      id: 'directory',
      label: 'Staff Directory',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
          <circle cx="9" cy="7" r="4"></circle>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
          <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
        </svg>
      ),
      visible: true,
    },
    {
      id: 'hr',
      label: 'HR & Time-off',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
        </svg>
      ),
      visible: hasHrAccess,
    },
    {
      id: 'admin',
      label: 'Admin & Access Control',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          <circle cx="12" cy="11" r="3"></circle>
        </svg>
      ),
      badge: 'Top Team',
      badgeVariant: 'amber',
      visible: isAdmin,
    },
  ];

  return (
    <aside className="enterprise-sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="sidebar-logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
            <line x1="8" y1="21" x2="16" y2="21"></line>
            <line x1="12" y1="17" x2="12" y2="21"></line>
          </svg>
        </div>
        <div className="sidebar-brand-title">
          <div className="brand-name">KnoQuest</div>
          <div className="brand-sub">NovaTech Workspace</div>
        </div>
      </div>

      {/* Navigation Groups */}
      <nav className="sidebar-nav">
        <div className="nav-group-label">WORKSPACE VIEWS</div>
        <div className="nav-items-list">
          {navItems.filter((i) => i.visible).map((item) => {
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`sidebar-nav-btn ${isActive ? 'active' : ''}`}
                onClick={() => onNavigate(item.id)}
              >
                <span className="nav-btn-icon">{item.icon}</span>
                <span className="nav-btn-label">{item.label}</span>
                {item.badge && (
                  <span className={`nav-btn-badge badge-${item.badgeVariant || 'blue'}`}>
                    {item.badge}
                  </span>
                )}
                {isActive && <div className="nav-btn-indicator" />}
              </button>
            );
          })}
        </div>
      </nav>

      {/* User Profile Card & Logout */}
      <div className="sidebar-user-footer">
        <div className="user-profile-card">
          <div className="user-avatar-badge">
            {currentUser.name.charAt(0)}
          </div>
          <div className="user-profile-details">
            <div className="user-profile-name" title={currentUser.name}>{currentUser.name}</div>
            <div className="user-profile-role" title={`${currentUser.designation} • ${currentUser.department}`}>
              {currentUser.designation || currentUser.role}
            </div>
            <div className="user-profile-id-row">
              <span className="user-id-chip">{currentUser.full_id || currentUser.employee_id}</span>
              <span className="user-dept-chip">{currentUser.department}</span>
            </div>
          </div>
        </div>

        <button
          type="button"
          className="sidebar-logout-btn"
          onClick={onLogout}
          title="Sign out of NovaTech Workspace"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
