import React, { useState, useEffect } from 'react';
import { X, Mail, FileEdit, Send, Inbox, RefreshCw, Clock } from 'lucide-react';
import { listCommunications } from '../services/api';

interface CommunicationItem {
  comm_id: string;
  comm_type: string;
  sender_id: string;
  recipient: string;
  subject: string;
  body: string;
  status: string;
  timestamp: string;
}

interface CommunicationsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  employeeId: string;
  onSendPrompt?: (prompt: string) => void;
}

export const CommunicationsDrawer: React.FC<CommunicationsDrawerProps> = ({
  isOpen,
  onClose,
  employeeId,
  onSendPrompt,
}) => {
  const [activeTab, setActiveTab] = useState<'drafts' | 'inbox' | 'sent'>('drafts');
  const [messages, setMessages] = useState<CommunicationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadMessages();
    }
  }, [isOpen, activeTab, employeeId]);

  const loadMessages = async () => {
    setLoading(true);
    setError(null);
    try {
      const folderParam = activeTab === 'drafts' ? 'drafts' : activeTab === 'sent' ? 'sent' : undefined;
      const res = await listCommunications(folderParam);
      setMessages(res.communications || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load corporate communications');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="admin-drawer" style={{ maxWidth: '640px' }} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="drawer-header">
          <div className="drawer-title" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #0284C7, #0369A1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFF'
            }}>
              <Mail size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.08rem', color: '#F8FAFC' }}>Microsoft Outlook & Communications</h3>
              <p style={{ fontSize: '0.76rem', color: '#94A3B8', margin: 0 }}>
                Enterprise Mailbox for <code>{employeeId}</code>
              </p>
            </div>
          </div>
          <button className="drawer-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div style={{
          display: 'flex',
          gap: '0.5rem',
          padding: '0.75rem 1.25rem',
          background: 'rgba(15, 23, 42, 0.7)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <button
            className={`comms-tab-btn ${activeTab === 'drafts' ? 'active' : ''}`}
            onClick={() => setActiveTab('drafts')}
          >
            <FileEdit size={14} />
            <span>Drafts</span>
          </button>
          <button
            className={`comms-tab-btn ${activeTab === 'inbox' ? 'active' : ''}`}
            onClick={() => setActiveTab('inbox')}
          >
            <Inbox size={14} />
            <span>Inbox & Announcements</span>
          </button>
          <button
            className={`comms-tab-btn ${activeTab === 'sent' ? 'active' : ''}`}
            onClick={() => setActiveTab('sent')}
          >
            <Send size={14} />
            <span>Sent Items</span>
          </button>
          <button
            onClick={loadMessages}
            title="Refresh"
            style={{
              marginLeft: 'auto',
              background: 'transparent',
              border: 'none',
              color: '#94A3B8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <RefreshCw size={14} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          </button>
        </div>

        {/* Body content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem' }}>
          {error && (
            <div className="drawer-banner error" style={{ borderRadius: '6px', marginBottom: '1rem' }}>
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#94A3B8' }}>
              <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', margin: '0 auto 0.5rem' }} />
              <p>Loading {activeTab}...</p>
            </div>
          ) : messages.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#94A3B8' }}>
              <Mail size={36} style={{ opacity: 0.3, margin: '0 auto 0.75rem' }} />
              <p>No messages in {activeTab}.</p>
              {activeTab === 'drafts' && (
                <p style={{ fontSize: '0.8rem', color: '#64748B' }}>
                  Ask the agent: <code>"Draft email to team regarding sprint sync"</code> to create a draft.
                </p>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {messages.map((m) => (
                <div
                  key={m.comm_id}
                  style={{
                    padding: '1rem',
                    borderRadius: '8px',
                    background: m.status === 'draft' ? 'rgba(245, 158, 11, 0.04)' : 'rgba(255, 255, 255, 0.02)',
                    border: m.status === 'draft' ? '1px solid rgba(245, 158, 11, 0.25)' : '1px solid rgba(255, 255, 255, 0.08)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.45rem'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{
                        fontSize: '0.68rem',
                        fontFamily: 'monospace',
                        color: '#38BDF8',
                        background: 'rgba(56, 189, 248, 0.12)',
                        padding: '0.1rem 0.4rem',
                        borderRadius: '4px'
                      }}>
                        {m.comm_id}
                      </span>
                      <span style={{
                        fontSize: '0.65rem',
                        textTransform: 'uppercase',
                        fontWeight: 700,
                        padding: '0.1rem 0.4rem',
                        borderRadius: '4px',
                        background: m.status === 'draft' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(34, 197, 94, 0.2)',
                        color: m.status === 'draft' ? '#FBBF24' : '#4ADE80'
                      }}>
                        {m.status}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: '#94A3B8' }}>
                        {m.comm_type === 'teams' ? 'Microsoft Teams' : 'Outlook'}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.72rem', color: '#64748B' }}>
                      <Clock size={12} />
                      <span>{m.timestamp}</span>
                    </div>
                  </div>

                  <div style={{ fontSize: '0.92rem', fontWeight: 600, color: '#F8FAFC' }}>
                    {m.subject || '(No Subject)'}
                  </div>

                  <div style={{ fontSize: '0.76rem', color: '#94A3B8' }}>
                    <strong>To:</strong> <code>{m.recipient}</code>
                  </div>

                  <div style={{
                    fontSize: '0.82rem',
                    color: '#CBD5E1',
                    background: 'rgba(0, 0, 0, 0.2)',
                    padding: '0.65rem 0.75rem',
                    borderRadius: '6px',
                    whiteSpace: 'pre-wrap',
                    lineHeight: 1.45
                  }}>
                    {m.body}
                  </div>

                  {m.status === 'draft' && onSendPrompt && (
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.35rem' }}>
                      <button
                        onClick={() => {
                          onClose();
                          onSendPrompt(`Send email to ${m.recipient} with subject "${m.subject}": ${m.body}`);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          background: 'linear-gradient(135deg, #2563EB, #1D4ED8)',
                          color: '#FFF',
                          border: 'none',
                          borderRadius: '6px',
                          padding: '0.35rem 0.75rem',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer'
                        }}
                      >
                        <Send size={12} />
                        <span>Send Draft via Agent</span>
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
