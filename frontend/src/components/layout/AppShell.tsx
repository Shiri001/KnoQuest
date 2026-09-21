import React from 'react';
import { Sidebar, type WorkspaceView } from './Sidebar';
import { TopNav } from './TopNav';
import type { EmployeePersona, HealthStatus, UploadedFile } from '../../types/chat';

interface AppShellProps {
  currentView: WorkspaceView;
  onNavigate: (view: WorkspaceView) => void;
  currentUser: EmployeePersona;
  onLogout: () => void;
  health: HealthStatus | null;
  currentLanguage: string;
  onLanguageChange: (lang: string) => void;
  activeUpload: UploadedFile | null;
  onClearUpload?: () => void;
  onOpenUploadModal?: () => void;
  unreadDraftsCount?: number;
  openTicketsCount?: number;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentView,
  onNavigate,
  currentUser,
  onLogout,
  health,
  currentLanguage,
  onLanguageChange,
  activeUpload,
  onClearUpload,
  onOpenUploadModal,
  unreadDraftsCount = 0,
  openTicketsCount = 0,
  children,
}) => {
  return (
    <div className="enterprise-app-shell">
      <Sidebar
        currentView={currentView}
        onNavigate={onNavigate}
        currentUser={currentUser}
        onLogout={onLogout}
        unreadDraftsCount={unreadDraftsCount}
        openTicketsCount={openTicketsCount}
      />
      <div className="enterprise-main-pane">
        <TopNav
          currentView={currentView}
          health={health}
          currentLanguage={currentLanguage}
          onLanguageChange={onLanguageChange}
          activeUpload={activeUpload}
          onClearUpload={onClearUpload}
          onOpenUploadModal={onOpenUploadModal}
        />
        <main className="enterprise-content-viewport">
          {children}
        </main>
      </div>
    </div>
  );
};
