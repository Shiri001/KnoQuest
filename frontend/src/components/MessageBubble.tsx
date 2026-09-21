import React, { useState, useEffect, useRef } from 'react';
import { User, Bot, FileText, ChevronDown, ChevronUp, Wrench, Volume2, VolumeX, Loader2 } from 'lucide-react';
import type { Message, SourceCitation } from '../types/chat';
import { synthesizeSpeech } from '../services/api';

interface MessageBubbleProps {
  message: Message;
  onCitationClick?: (citation: SourceCitation) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onCitationClick }) => {
  const isUser = message.role === 'user';
  const [showSources, setShowSources] = useState<boolean>(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState<boolean>(false);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    return () => {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current = null;
      }
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handleToggleSpeech = async () => {
    // 1. If currently playing, stop immediately
    if (isPlayingAudio) {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current = null;
      }
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      setIsPlayingAudio(false);
      setIsLoadingAudio(false);
      return;
    }

    const cleanText = message.content
      .replace(/\*\*/g, '')
      .replace(/•/g, '')
      .replace(/\[.*?\]/g, '')
      .replace(/#{1,6}\s/g, '')
      .trim();

    if (!cleanText) return;

    // Detect language
    let lang = 'en';
    if (/[\u0900-\u097F]/.test(cleanText)) {
      lang = 'hi';
    } else if (/[¿¡]/.test(cleanText) || /\b(política|días|empleados|beneficios|vacaciones|trabajo)\b/i.test(cleanText)) {
      lang = 'es';
    } else if (/\b(politique|jours|employés|avantages|congés|télétravail)\b/i.test(cleanText)) {
      lang = 'fr';
    }

    setIsLoadingAudio(true);

    // 2. Attempt Azure Cognitive Services Neural Text-to-Speech (High Fidelity)
    try {
      const res = await synthesizeSpeech(cleanText, lang);
      if (res && res.audio_base64) {
        const audio = new Audio(`data:audio/wav;base64,${res.audio_base64}`);
        audioPlayerRef.current = audio;

        audio.onended = () => {
          setIsPlayingAudio(false);
          audioPlayerRef.current = null;
        };
        audio.onerror = () => {
          setIsPlayingAudio(false);
          audioPlayerRef.current = null;
        };

        await audio.play();
        setIsLoadingAudio(false);
        setIsPlayingAudio(true);
        return;
      }
    } catch (azureErr) {
      console.warn('Azure Neural TTS notice, falling back to browser synthesis:', azureErr);
    }

    // 3. Fallback: Native Browser SpeechSynthesis
    setIsLoadingAudio(false);
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(cleanText);

      const langMap: Record<string, string> = {
        hi: 'hi-IN',
        es: 'es-ES',
        fr: 'fr-FR',
        en: 'en-US',
      };
      utterance.lang = langMap[lang] || 'en-US';
      utterance.rate = 1.0;

      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);

      setIsPlayingAudio(true);
      window.speechSynthesis.speak(utterance);
    } else {
      alert('Audio playback is not supported in this browser.');
    }
  };

  // Simple Markdown parser for bolding and bullet lines
  const renderFormattedContent = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, idx) => {
      // Parse **bold** within line
      const parts = line.split(/(\*\*.*?\*\*)/g);
      const formattedParts = parts.map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={pIdx} style={{ color: '#F8FAFC' }}>{part.slice(2, -2)}</strong>;
        }
        return part;
      });

      if (line.startsWith('• ') || line.startsWith('- ')) {
        return (
          <div key={idx} style={{ paddingLeft: '1rem', marginTop: '0.2rem', marginBottom: '0.2rem' }}>
            {formattedParts}
          </div>
        );
      }

      return (
        <React.Fragment key={idx}>
          {formattedParts}
          {idx < lines.length - 1 && <br />}
        </React.Fragment>
      );
    });
  };

  return (
    <div className={`message-row ${message.role}`}>
      <div className={`message-avatar ${message.role}`}>
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      <div className="message-content-wrapper">
        <div className="message-bubble">
          {renderFormattedContent(message.content)}

          {/* Tool Calls Executed */}
          {message.tool_calls && message.tool_calls.length > 0 && (
            <div style={{ marginTop: '0.65rem' }}>
              {message.tool_calls.map((tc, idx) => (
                <div key={idx} className="tool-badge">
                  <Wrench size={13} />
                  <span>
                    MCP Tool Executed: <strong>{tc.tool_name}</strong>
                    {tc.result.ticket_id && ` (${tc.result.ticket_id})`}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Source Citations */}
          {message.sources && message.sources.length > 0 && (
            <div className="sources-container">
              <div
                className="sources-header"
                style={{ cursor: 'pointer', userSelect: 'none' }}
                onClick={() => setShowSources(!showSources)}
              >
                <FileText size={13} />
                <span>Verified Sources ({message.sources.length})</span>
                {showSources ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              </div>

              {showSources && (
                <div className="citation-list">
                  {message.sources.map((src, sIdx) => (
                    <div
                      key={sIdx}
                      className="citation-item"
                      onClick={() => onCitationClick && onCitationClick(src)}
                    >
                      <div className="citation-title">
                        <FileText size={12} style={{ color: '#60A5FA' }} />
                        <span>{src.source}</span>
                      </div>
                      {src.section && (
                        <div className="citation-section">{src.section}</div>
                      )}
                      {src.snippet && (
                        <div className="citation-snippet">{src.snippet}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="message-meta">
          <span>{message.timestamp}</span>
          {!isUser && (
            <>
              {message.mode && (
                <span>• {message.mode === 'azure_foundry' ? 'Azure Foundry' : 'Enterprise Sandbox'}</span>
              )}
              <button
                className={`tts-read-btn ${isPlayingAudio ? 'playing' : ''}`}
                onClick={handleToggleSpeech}
                disabled={isLoadingAudio}
                title={isPlayingAudio ? 'Stop reading' : 'Read aloud with Azure Neural Speech'}
              >
                {isLoadingAudio ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : isPlayingAudio ? <VolumeX size={13} /> : <Volume2 size={13} />}
                <span>{isLoadingAudio ? 'Synthesizing...' : isPlayingAudio ? 'Stop' : 'Read Aloud'}</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
