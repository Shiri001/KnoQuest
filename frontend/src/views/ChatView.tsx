import React, { useRef, useEffect } from 'react';
import type { Message, SourceCitation } from '../types/chat';
import { MessageBubble } from '../components/MessageBubble';
import { ChatInput } from '../components/ChatInput';

interface ChatViewProps {
  messages: Message[];
  isLoading: boolean;
  isRecording: boolean;
  isTranscribing: boolean;
  audioLevel: number;
  recordingError: string;
  onSendMessage: (message: string) => void;
  onToggleRecording: () => void;
  onOpenUpload: () => void;
  activeFilename?: string;
  onClearActiveFile?: () => void;
  onCitationClick: (citation: SourceCitation) => void;
  sampleQuestions: { text: string; tag: string; icon?: React.ReactNode }[];
}

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  isLoading,
  isRecording,
  isTranscribing,
  audioLevel,
  recordingError,
  onSendMessage,
  onToggleRecording,
  onOpenUpload,
  activeFilename,
  onClearActiveFile,
  onCitationClick,
  sampleQuestions,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, isTranscribing]);

  return (
    <div className="chat-view-layout">
      {/* Scrollable Messages Area */}
      <div className="chat-messages-scroll-pane">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <div className="empty-state-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                <path d="M9.5 9h.01"></path>
                <path d="M14.5 9h.01"></path>
              </svg>
            </div>
            <h2>NovaTech AI Assistant</h2>
            <p className="empty-sub">
              Ask anything about enterprise HR policies, IT equipment, travel allowances, or request actions like scheduling meetings, creating IT tickets, and drafting emails.
            </p>

            <div className="empty-quick-prompts-grid">
              {sampleQuestions.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="empty-prompt-card"
                  onClick={() => onSendMessage(q.text)}
                >
                  <div className="prompt-header">
                    <span className="prompt-badge">{q.tag}</span>
                    {q.icon}
                  </div>
                  <div className="prompt-question">"{q.text}"</div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="chat-messages-list">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onCitationClick={onCitationClick}
              />
            ))}

            {isLoading && (
              <div className="agent-thinking-indicator">
                <div className="agent-avatar-badge">K</div>
                <div className="thinking-bubble">
                  <div className="dot-flashing"></div>
                  <span>Grounded reasoning & tool orchestration in progress...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Fixed Chat Composer Bar */}
      <div className="chat-composer-bar">
        <ChatInput
          onSendMessage={onSendMessage}
          onOpenUpload={onOpenUpload}
          isLoading={isLoading}
          isRecording={isRecording}
          isTranscribing={isTranscribing}
          audioLevel={audioLevel}
          onToggleRecording={onToggleRecording}
          activeFilename={activeFilename}
          onClearActiveFile={onClearActiveFile}
          recordingError={recordingError}
        />
      </div>
    </div>
  );
};
