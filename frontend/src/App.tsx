import React, { useState, useEffect, useRef } from 'react';
import { LoginPage } from './components/auth/LoginPage';
import { AppShell } from './components/layout/AppShell';
import type { WorkspaceView } from './components/layout/Sidebar';
import { DashboardView } from './views/DashboardView';
import { ChatView } from './views/ChatView';
import { CommunicationsView } from './views/CommunicationsView';
import { DirectoryView } from './views/DirectoryView';
import { ITSupportView } from './views/ITSupportView';
import { CalendarView } from './views/CalendarView';
import { HRView } from './views/HRView';
import { DocumentsView } from './views/DocumentsView';
import { AdminView } from './views/AdminView';

import { FileUploadModal } from './components/FileUploadModal';
import { SourceCitationModal } from './components/SourceCitationModal';
import {
  checkHealth,
  sendChatMessage,
  listTickets,
  listCommunications,
  fetchCurrentProfile,
  logoutEmployee,
  setOnUnauthorizedHandler,
  transcribeAudio,
} from './services/api';
import type {
  HealthStatus,
  Message,
  SourceCitation,
  UploadedFile,
  EmployeePersona,
} from './types/chat';
import { FileText, Lock, Calendar, Mail } from 'lucide-react';

const VALID_VIEWS: WorkspaceView[] = [
  'dashboard',
  'chat',
  'documents',
  'communications',
  'calendar',
  'tickets',
  'directory',
  'hr',
  'admin',
];

export const App: React.FC = () => {
  // 1. Authentication State (server-verified session)
  const [currentUser, setCurrentUser] = useState<EmployeePersona | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState<boolean>(true);

  // 2. Routing State (URL Hash)
  const [currentView, setCurrentView] = useState<WorkspaceView>(() => {
    const hash = window.location.hash.replace('#', '') as WorkspaceView;
    return VALID_VIEWS.includes(hash) ? hash : 'dashboard';
  });

  // 3. Chat & Knowledge State
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string>('');
  const [currentLanguage, setCurrentLanguage] = useState<string>('en');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  // 4. File Upload & Citations
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [activeFile, setActiveFile] = useState<UploadedFile | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<SourceCitation | null>(null);

  // 5. Counters
  const [ticketsCount, setTicketsCount] = useState<number>(0);
  const [draftsCount, setDraftsCount] = useState<number>(0);

  // 6. Voice Recording State Machine
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [recordingError, setRecordingError] = useState<string>('');
  const isRecordingRef = useRef<boolean>(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Check server-verified session on mount
  useEffect(() => {
    setOnUnauthorizedHandler(() => {
      setCurrentUser(null);
    });

    fetchCurrentProfile()
      .then((profile) => {
        setCurrentUser(profile);
      })
      .catch(() => {
        setCurrentUser(null);
      })
      .finally(() => {
        setIsCheckingSession(false);
      });
  }, []);

  // Sync hash routing
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as WorkspaceView;
      if (VALID_VIEWS.includes(hash)) {
        setCurrentView(hash);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateTo = (view: WorkspaceView) => {
    window.location.hash = view;
    setCurrentView(view);
  };

  // Sync session and health
  useEffect(() => {
    if (currentUser) {
      refreshHealthAndStats();
      const interval = setInterval(refreshHealthAndStats, 30000);
      return () => clearInterval(interval);
    }
  }, [currentUser]);

  const refreshHealthAndStats = async () => {
    try {
      const h = await checkHealth();
      setHealth(h);
    } catch (err) {
      console.error('Health check failed:', err);
    }

    try {
      const t = await listTickets();
      if (t.tickets) setTicketsCount(t.tickets.length);
    } catch (err) {
      console.error('Failed to count tickets:', err);
    }

    if (currentUser) {
      try {
        const c = await listCommunications('drafts');
        if (c.communications) setDraftsCount(c.communications.length);
      } catch (err) {
        console.error('Failed to count drafts:', err);
      }
    }
  };

  const handleLoginSuccess = (user: EmployeePersona) => {
    setCurrentUser(user);
    navigateTo('dashboard');
  };

  const handleLogout = async () => {
    try {
      await logoutEmployee();
    } catch (e) {
      console.warn('Logout notice:', e);
    } finally {
      setCurrentUser(null);
      setMessages([]);
      setConversationId('');
      window.location.hash = 'dashboard';
    }
  };

  const handleRefreshProfile = async () => {
    if (!currentUser) return;
    try {
      const updated = await fetchCurrentProfile();
      setCurrentUser(updated);
    } catch (err) {
      console.error('Failed to refresh profile:', err);
    }
  };

  // Chat Message Sending
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    // Switch to chat view if not already there
    if (currentView !== 'chat') {
      navigateTo('chat');
    }

    const userTurn: Message = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userTurn]);
    setIsLoading(true);

    try {
      const res = await sendChatMessage(
        text,
        conversationId,
        currentLanguage,
        activeFile ? activeFile.file_id : undefined
      );

      if (res.conversation_id) {
        setConversationId(res.conversation_id);
      }

      const botTurn: Message = {
        id: `bot-${Date.now()}`,
        role: 'assistant',
        content: res.answer,
        sources: res.sources,
        tool_calls: res.tool_calls,
        mode: res.mode as any,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, botTurn]);
      refreshHealthAndStats();
    } catch (err: any) {
      const errorTurn: Message = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `**System Notice**: ${err.message || 'An unexpected error occurred while communicating with the AI Agent.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorTurn]);
    } finally {
      setIsLoading(false);
    }
  };

  // Voice recording state machine
  const startRecording = async () => {
    try {
      setRecordingError('');
      audioChunksRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      audioStreamRef.current = stream;

      // Audio Level Analyzer
      try {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        const ctx = new AudioCtx();
        audioContextRef.current = ctx;
        const source = ctx.createMediaStreamSource(stream);
        const analyzer = ctx.createAnalyser();
        analyzer.fftSize = 256;
        source.connect(analyzer);

        const dataArr = new Uint8Array(analyzer.frequencyBinCount);
        const checkVolume = () => {
          if (!isRecordingRef.current) return;
          analyzer.getByteFrequencyData(dataArr);
          let sum = 0;
          for (let i = 0; i < dataArr.length; i++) sum += dataArr[i];
          const avg = sum / dataArr.length;
          const levelPct = Math.min(100, Math.round((avg / 128) * 100));
          setAudioLevel(levelPct);
          animFrameRef.current = requestAnimationFrame(checkVolume);
        };
        animFrameRef.current = requestAnimationFrame(checkVolume);
      } catch (e) {
        console.warn('Audio analyzer initialization failed:', e);
      }

      // MediaRecorder initialization
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
      }

      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
        if (audioContextRef.current) {
          audioContextRef.current.close().catch(() => {});
          audioContextRef.current = null;
        }
        if (audioStreamRef.current) {
          audioStreamRef.current.getTracks().forEach((track) => track.stop());
          audioStreamRef.current = null;
        }
        setAudioLevel(0);

        const recordedBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType || 'audio/webm',
        });

        // Relaxed threshold to avoid premature "too short" errors on brief utterances
        if (recordedBlob.size < 400) {
          setRecordingError('No audio detected. Please ensure your microphone is connected and speak clearly.');
          setIsTranscribing(false);
          setIsRecording(false);
          isRecordingRef.current = false;
          return;
        }

        setIsTranscribing(true);
        try {
          const result = await transcribeAudio(recordedBlob, currentLanguage);

          if (result && result.text && result.text.trim()) {
            handleSendMessage(result.text.trim());
          } else {
            setRecordingError('Could not recognize any speech. Please try speaking closer to the microphone.');
          }
        } catch (err: any) {
          console.error('Speech transcription error:', err);
          setRecordingError(err.message || 'Speech recognition service error.');
        } finally {
          setIsTranscribing(false);
          setIsRecording(false);
          isRecordingRef.current = false;
        }
      };

      mediaRecorder.start(100);
      isRecordingRef.current = true;
      setIsRecording(true);
    } catch (err: any) {
      console.error('Microphone access failed:', err);
      setRecordingError('Microphone permission blocked or unavailable. Please enable microphone permissions in your browser settings.');
      isRecordingRef.current = false;
      setIsRecording(false);
    }
  };

  const toggleRecording = async () => {
    if (isRecordingRef.current) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
      return;
    }
    await startRecording();
  };

  // Sample quick questions
  const sampleQuestions = [
    { text: 'Show me my HR information and leave balance', tag: 'HR Self Tool', icon: <FileText size={14} /> },
    { text: "Show me everyone's salary and payroll", tag: 'Authorization Check (RBAC)', icon: <Lock size={14} /> },
    { text: 'What meetings do I have on my calendar?', tag: 'Calendar Tool', icon: <Calendar size={14} /> },
    { text: 'Draft email to team regarding Sprint Planning on Friday', tag: 'Outlook Tool', icon: <Mail size={14} /> },
  ];

  // Show clean verifying state on initial mount
  if (isCheckingSession) {
    return (
      <div className="session-checking-splash">
        <div className="splash-card">
          <div className="splash-spinner"></div>
          <div className="splash-brand">NovaTech KnoQuest</div>
          <div className="splash-message">Verifying enterprise session...</div>
        </div>
      </div>
    );
  }

  // If user is not authenticated, show production LoginPage
  if (!currentUser) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <AppShell
      currentView={currentView}
      onNavigate={navigateTo}
      currentUser={currentUser}
      onLogout={handleLogout}
      health={health}
      currentLanguage={currentLanguage}
      onLanguageChange={setCurrentLanguage}
      activeUpload={activeFile}
      onClearUpload={() => setActiveFile(null)}
      onOpenUploadModal={() => setIsUploadOpen(true)}
      unreadDraftsCount={draftsCount}
      openTicketsCount={ticketsCount}
    >
      {/* 1. Dashboard View */}
      {currentView === 'dashboard' && (
        <DashboardView
          currentUser={currentUser}
          onNavigate={navigateTo}
          onQuickAsk={(prompt) => handleSendMessage(prompt)}
          draftsCount={draftsCount}
          ticketsCount={ticketsCount}
          policyCount={8}
        />
      )}

      {/* 2. AI Chat View */}
      {currentView === 'chat' && (
        <ChatView
          messages={messages}
          isLoading={isLoading}
          isRecording={isRecording}
          isTranscribing={isTranscribing}
          audioLevel={audioLevel}
          recordingError={recordingError}
          onSendMessage={handleSendMessage}
          onToggleRecording={toggleRecording}
          onOpenUpload={() => setIsUploadOpen(true)}
          activeFilename={activeFile?.filename}
          onClearActiveFile={() => setActiveFile(null)}
          onCitationClick={(citation) => setSelectedCitation(citation)}
          sampleQuestions={sampleQuestions}
        />
      )}

      {/* 3. Knowledge & Documents View */}
      {currentView === 'documents' && (
        <DocumentsView
          onAskAboutPolicy={(title) =>
            handleSendMessage(`What are the key guidelines and rules outlined in the ${title} document?`)
          }
          onOpenUploadModal={() => setIsUploadOpen(true)}
        />
      )}

      {/* 4. Outlook Communications & Drafts View */}
      {currentView === 'communications' && (
        <CommunicationsView
          currentUser={currentUser}
          onRefreshBadge={refreshHealthAndStats}
        />
      )}

      {/* 5. Calendar & Schedule View */}
      {currentView === 'calendar' && (
        <CalendarView currentUser={currentUser} />
      )}

      {/* 6. IT Support Helpdesk View */}
      {currentView === 'tickets' && (
        <ITSupportView
          currentUser={currentUser}
          onRefreshBadge={refreshHealthAndStats}
        />
      )}

      {/* 7. Employee Directory View */}
      {currentView === 'directory' && (
        <DirectoryView
          onAskAboutEmployee={(name) =>
            handleSendMessage(
              `Provide a comprehensive profile dossier for ${name} from the staff directory, including their department, official designation, contact info, physical office, key responsibilities, and how to collaborate with them.`
            )
          }
        />
      )}

      {/* 8. HR & Leave Portal */}
      {currentView === 'hr' && (
        <HRView currentUser={currentUser} />
      )}

      {/* 9. Top Team Admin View */}
      {currentView === 'admin' && (
        <AdminView
          currentUser={currentUser}
          onProfileUpdated={handleRefreshProfile}
        />
      )}

      {/* Shared Modals */}
      <FileUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={(file) => {
          setActiveFile(file);
          navigateTo('chat');
        }}
      />

      <SourceCitationModal
        citation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />
    </AppShell>
  );
};

export default App;
