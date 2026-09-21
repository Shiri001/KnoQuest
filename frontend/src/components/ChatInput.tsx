import React, { useState, useRef, useEffect } from 'react';
import { Paperclip, Mic, MicOff, Send } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  onOpenUpload: () => void;
  isLoading: boolean;
  isRecording: boolean;
  isTranscribing?: boolean;
  audioLevel?: number;
  onToggleRecording: () => void;
  activeFilename?: string;
  onClearActiveFile?: () => void;
  interimTranscript?: string;
  recordingError?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onOpenUpload,
  isLoading,
  isRecording,
  isTranscribing,
  audioLevel = 0,
  onToggleRecording,
  activeFilename,
  onClearActiveFile,
  interimTranscript,
  recordingError,
}) => {
  const [inputText, setInputText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (interimTranscript) {
      setInputText(interimTranscript);
    }
  }, [interimTranscript]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [inputText]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText);
    setInputText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  return (
    <div className="input-container">
      {isTranscribing && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '0.6rem 1rem',
          marginBottom: '0.6rem',
          borderRadius: '8px',
          background: 'rgba(59, 130, 246, 0.15)',
          border: '1px solid rgba(59, 130, 246, 0.4)',
          color: '#60A5FA',
          fontSize: '0.85rem'
        }}>
          <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⏳</span>
          <strong>Processing with Azure Speech...</strong> Transcribing your voice input.
        </div>
      )}

      {isRecording && !isTranscribing && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.6rem 1rem',
          marginBottom: '0.6rem',
          borderRadius: '8px',
          background: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          color: '#F87171',
          fontSize: '0.85rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{
              display: 'inline-block',
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: '#EF4444',
              boxShadow: '0 0 8px #EF4444'
            }} />
            <span>🎙️ <strong>Listening...</strong> Speak your question</span>
            {/* Live Audio Level Meter */}
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '18px' }} title={`Audio Level: ${Math.round(audioLevel)}%`}>
              {[1, 2, 3, 4, 5].map((bar) => (
                <span
                  key={bar}
                  style={{
                    width: '3px',
                    height: `${Math.max(4, Math.min(18, (audioLevel * (bar * 0.35))))}px`,
                    background: audioLevel > 8 ? '#10B981' : '#F87171',
                    borderRadius: '2px',
                    transition: 'height 0.08s ease'
                  }}
                />
              ))}
            </div>
            {audioLevel <= 4 && (
              <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>(Audio detected: quiet)</span>
            )}
          </div>
          <button
            type="button"
            onClick={onToggleRecording}
            style={{
              background: '#EF4444',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '4px',
              padding: '3px 10px',
              fontSize: '0.75rem',
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            ⏹ Stop & Send
          </button>
        </div>
      )}

      {recordingError && (
        <div style={{
          padding: '0.5rem 0.85rem',
          marginBottom: '0.6rem',
          borderRadius: '8px',
          background: 'rgba(245, 158, 11, 0.12)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          color: '#FBBF24',
          fontSize: '0.8rem'
        }}>
          ⚠️ {recordingError}
        </div>
      )}

      {activeFilename && (
        <div className="active-file-banner" style={{ marginBottom: '0.75rem', margin: 0 }}>
          <span>
            📄 Active Document Context: <strong>{activeFilename}</strong>
          </span>
          <button onClick={onClearActiveFile} title="Remove active document context">
            ✕ Remove
          </button>
        </div>
      )}

      <div className="input-box">
        <button
          type="button"
          className="input-action-btn"
          onClick={onOpenUpload}
          title="Upload policy document (PDF, DOCX, TXT)"
          disabled={isLoading}
        >
          <Paperclip size={18} />
        </button>

        <button
          type="button"
          className={`input-action-btn ${isRecording ? 'active-rec' : ''}`}
          onClick={onToggleRecording}
          title={isRecording ? 'Stop speech recognition' : 'Speak to KnoQuest (Speech-to-Text)'}
          disabled={isLoading}
        >
          {isRecording ? <MicOff size={18} /> : <Mic size={18} />}
        </button>

        <textarea
          ref={textareaRef}
          rows={1}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isRecording ? 'Listening to your microphone...' : 'Ask anything about NovaTech policies, IT tickets, or benefits...'}
          disabled={isLoading}
        />

        <button
          type="button"
          className="send-btn"
          onClick={handleSend}
          disabled={!inputText.trim() || isLoading}
          title="Send question"
        >
          <Send size={18} />
        </button>
      </div>

      <div className="input-footer">
        <span>Grounded Enterprise Knowledge • Zero Fabrication Guardrails</span>
        <span>Press Enter to send, Shift+Enter for new line</span>
      </div>
    </div>
  );
};
