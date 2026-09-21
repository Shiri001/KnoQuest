import React, { useState, useEffect } from 'react';
import type { EmployeePersona } from '../types/chat';
import {
  listCommunications,
  sendDirectCommunication,
  draftDirectCommunication,
  deleteCommunication,
} from '../services/api';
import { ConfirmationModal } from '../components/common/ConfirmationModal';
import { ActionFeedbackToast } from '../components/common/ActionFeedbackToast';

interface CommunicationsViewProps {
  currentUser: EmployeePersona;
  onRefreshBadge?: () => void;
}

interface CommunicationItem {
  id: number;
  comm_id: string;
  comm_type: string;
  company_id: string;
  sender_id: string;
  recipient: string;
  subject: string;
  body: string;
  status: 'draft' | 'sent' | 'read';
  timestamp: string;
}

const QUICK_CONTACTS = [
  { name: 'All Staff', email: 'team@novatech.com' },
  { name: 'Sarah Jenkins (HR)', email: 'sarah.jenkins@novatech.com' },
  { name: 'Marcus Vance (IT)', email: 'marcus.vance@novatech.com' },
  { name: 'Elena Rostova (Travel)', email: 'elena.rostova@novatech.com' },
  { name: 'David Kumar (CISO)', email: 'david.kumar@novatech.com' },
];

export const CommunicationsView: React.FC<CommunicationsViewProps> = ({
  currentUser: _currentUser,
  onRefreshBadge,
}) => {
  const [folder, setFolder] = useState<'drafts' | 'inbox' | 'sent'>('drafts');
  const [items, setItems] = useState<CommunicationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedItem, setSelectedItem] = useState<CommunicationItem | null>(null);
  const [isComposing, setIsComposing] = useState<boolean>(false);
  const [counts, setCounts] = useState<{ drafts: number; inbox: number; sent: number }>({
    drafts: 0,
    inbox: 0,
    sent: 0,
  });

  // Editor form state
  const [editRecipient, setEditRecipient] = useState('');
  const [editSubject, setEditSubject] = useState('');
  const [editBody, setEditBody] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Professional 5-second Feedback Toast state
  const [toast, setToast] = useState<{
    message: string | null;
    type: 'success' | 'error' | 'info';
    title?: string;
  }>({ message: null, type: 'success' });

  // Enterprise Confirmation Modal state
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    details?: { label: string; value: string }[];
    confirmText?: string;
    cancelText?: string;
    isDanger?: boolean;
    iconType?: 'send' | 'calendar' | 'ticket' | 'delete' | 'general';
    onConfirm: () => void;
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
  });

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'success', title?: string) => {
    setToast({ message, type, title });
  };

  const refreshCounts = async () => {
    try {
      const [dRes, iRes, sRes] = await Promise.all([
        listCommunications('drafts').catch(() => ({ communications: [], count: 0 })),
        listCommunications('inbox').catch(() => ({ communications: [], count: 0 })),
        listCommunications('sent').catch(() => ({ communications: [], count: 0 })),
      ]);
      setCounts({
        drafts: dRes.count ?? dRes.communications?.length ?? 0,
        inbox: iRes.count ?? iRes.communications?.length ?? 0,
        sent: sRes.count ?? sRes.communications?.length ?? 0,
      });
    } catch (err) {
      console.error('Failed to load folder counts:', err);
    }
  };

  const fetchItems = async (targetFolder = folder, preserveSelectionId?: string) => {
    setLoading(true);
    try {
      const [res] = await Promise.all([
        listCommunications(targetFolder),
        refreshCounts(),
      ]);
      const list: CommunicationItem[] = res.communications || [];
      setItems(list);

      if (preserveSelectionId) {
        const found = list.find((it) => it.comm_id === preserveSelectionId);
        if (found) {
          selectItem(found);
          return;
        }
      }

      if (list.length > 0 && !selectedItem && !isComposing) {
        selectItem(list[0]);
      } else if (list.length === 0 && !isComposing) {
        setSelectedItem(null);
      }
    } catch (err: any) {
      console.error('Failed to load communications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems(folder);
  }, [folder]);

  const selectItem = (item: CommunicationItem) => {
    setIsComposing(false);
    setSelectedItem(item);
    setEditRecipient(item.recipient || '');
    setEditSubject(item.subject || '');
    setEditBody(item.body || '');
  };

  const handleStartCompose = () => {
    setIsComposing(true);
    setSelectedItem(null);
    setEditRecipient('');
    setEditSubject('');
    setEditBody('');
  };

  // 1. Send via Outlook: Ask first before proceeding
  const promptSendDraft = () => {
    if (!editRecipient.trim() || !editBody.trim()) {
      showToast('Recipient email address and message body are required.', 'error', 'Missing Information');
      return;
    }

    setConfirmModal({
      isOpen: true,
      title: 'Confirm Sending Email',
      message: 'Are you sure you want to proceed with transmitting this email via Microsoft Outlook Exchange?',
      details: [
        { label: 'Recipient', value: editRecipient.trim() },
        { label: 'Subject', value: editSubject.trim() || '(No Subject)' },
        { label: 'Mail Server', value: 'Microsoft Outlook (NovaTech Exchange)' },
      ],
      confirmText: 'Proceed & Send',
      iconType: 'send',
      onConfirm: async () => {
        setConfirmModal((prev) => ({ ...prev, isOpen: false }));
        await executeSendDraft();
      },
    });
  };

  const executeSendDraft = async () => {
    setSubmitting(true);
    try {
      const draftIdToSend = (selectedItem && selectedItem.status === 'draft') ? selectedItem.comm_id : undefined;
      const sendRes = await sendDirectCommunication({
        recipient: editRecipient.trim(),
        subject: editSubject.trim() || 'No Subject',
        body: editBody.trim(),
        channel: 'email',
        draft_id: draftIdToSend,
      });

      const sentCommId = sendRes.comm_id || draftIdToSend;
      showToast(`Message sent successfully via Microsoft Outlook to ${editRecipient.trim()}`, 'success', 'Email Delivered');
      setIsComposing(false);
      onRefreshBadge?.();

      setFolder('sent');
      await fetchItems('sent', sentCommId);
    } catch (err: any) {
      showToast(`Error sending message: ${err.message}`, 'error', 'Transmission Failed');
    } finally {
      setSubmitting(false);
    }
  };

  // 2. Save Draft: Ask first before proceeding
  const promptSaveDraft = () => {
    if (!editRecipient.trim() || !editBody.trim()) {
      showToast('Recipient and message body are required to save a draft.', 'error', 'Missing Information');
      return;
    }

    setConfirmModal({
      isOpen: true,
      title: isComposing ? 'Confirm Save New Draft' : 'Confirm Update Draft',
      message: 'Are you sure you want to proceed with saving these changes to your Drafts folder?',
      details: [
        { label: 'Recipient', value: editRecipient.trim() },
        { label: 'Subject', value: editSubject.trim() || '(No Subject)' },
      ],
      confirmText: isComposing ? 'Proceed & Save' : 'Proceed & Update',
      iconType: 'send',
      onConfirm: async () => {
        setConfirmModal((prev) => ({ ...prev, isOpen: false }));
        await executeSaveDraft();
      },
    });
  };

  const executeSaveDraft = async () => {
    setSubmitting(true);
    try {
      const draftIdToUpdate = (selectedItem && selectedItem.status === 'draft') ? selectedItem.comm_id : undefined;
      const res = await draftDirectCommunication({
        recipient: editRecipient.trim(),
        subject: editSubject.trim() || 'Enterprise Draft',
        body: editBody.trim(),
        draft_id: draftIdToUpdate,
      });

      const savedId = res.draft_id || res.comm_id;
      showToast(`Draft ${savedId} saved successfully! Showing in Drafts panel on the left.`, 'success', 'Draft Saved');
      onRefreshBadge?.();

      setFolder('drafts');
      await fetchItems('drafts', savedId);
    } catch (err: any) {
      showToast(`Error saving draft: ${err.message}`, 'error', 'Draft Save Failed');
    } finally {
      setSubmitting(false);
    }
  };

  // 3. Discard Draft: Ask first before proceeding
  const promptDeleteDraft = (commId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    setConfirmModal({
      isOpen: true,
      title: 'Confirm Discard Draft',
      message: `Are you sure you want to discard draft ${commId}? This message will be permanently removed from your enterprise mailbox.`,
      details: [
        { label: 'Draft ID', value: commId },
        { label: 'Warning', value: 'This action is irreversible.' },
      ],
      confirmText: 'Discard Draft',
      isDanger: true,
      iconType: 'delete',
      onConfirm: async () => {
        setConfirmModal((prev) => ({ ...prev, isOpen: false }));
        await executeDeleteDraft(commId);
      },
    });
  };

  const executeDeleteDraft = async (commId: string) => {
    try {
      await deleteCommunication(commId);
      showToast(`Draft ${commId} permanently discarded.`, 'info', 'Draft Discarded');
      if (selectedItem?.comm_id === commId) {
        setSelectedItem(null);
        setIsComposing(false);
        setEditRecipient('');
        setEditSubject('');
        setEditBody('');
      }
      onRefreshBadge?.();
      await fetchItems(folder);
    } catch (err: any) {
      showToast(`Error discarding draft: ${err.message}`, 'error', 'Discard Failed');
    }
  };

  const isEditorMode = isComposing || (selectedItem && selectedItem.status === 'draft');

  return (
    <div className="view-page-container communications-view">
      {/* Comms Layout: Sidebar + List + Detail */}
      <div className="comms-layout-container">
        {/* Left Comms Folder Navigation */}
        <div className="comms-folder-nav">
          <button
            type="button"
            className="compose-action-btn"
            onClick={handleStartCompose}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
            <span>New Email</span>
          </button>

          <div className="comms-folder-list">
            <button
              type="button"
              className={`folder-item ${folder === 'drafts' ? 'active' : ''}`}
              onClick={() => { setFolder('drafts'); setIsComposing(false); }}
            >
              <div className="folder-item-left">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <span>Drafts</span>
              </div>
              <span className="folder-badge badge-drafts">{counts.drafts}</span>
            </button>

            <button
              type="button"
              className={`folder-item ${folder === 'inbox' ? 'active' : ''}`}
              onClick={() => { setFolder('inbox'); setIsComposing(false); }}
            >
              <div className="folder-item-left">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"></polyline>
                  <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path>
                </svg>
                <span>Inbox</span>
              </div>
              <span className="folder-badge badge-inbox">{counts.inbox}</span>
            </button>

            <button
              type="button"
              className={`folder-item ${folder === 'sent' ? 'active' : ''}`}
              onClick={() => { setFolder('sent'); setIsComposing(false); }}
            >
              <div className="folder-item-left">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
                <span>Sent Items</span>
              </div>
              <span className="folder-badge badge-sent">{counts.sent}</span>
            </button>
          </div>

          <div className="outlook-sync-indicator">
            <div className="sync-dot"></div>
            <span>Connected to Microsoft Outlook (NovaTech Exchange)</span>
          </div>
        </div>

        {/* Middle Item List */}
        <div className="comms-items-list-pane">
          <div className="list-pane-header">
            <h3 className="folder-title">
              {folder === 'drafts' ? 'Draft Emails' : folder === 'inbox' ? 'Corporate Inbox' : 'Sent Messages'}
            </h3>
            <span className="items-count">{items.length} item(s)</span>
          </div>

          {loading ? (
            <div className="comms-loading-state">
              <span className="spinner-icon"></span>
              <span>Loading messages...</span>
            </div>
          ) : items.length === 0 ? (
            <div className="comms-empty-folder">
              <p>No messages in {folder}</p>
              {folder === 'drafts' && (
                <button
                  type="button"
                  onClick={handleStartCompose}
                  style={{
                    marginTop: '0.75rem',
                    background: '#2563EB',
                    color: '#FFF',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '0.45rem 0.9rem',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                  }}
                >
                  Create New Draft
                </button>
              )}
            </div>
          ) : (
            <div className="comms-items-scroll">
              {items.map((item) => {
                const isSelected = selectedItem?.comm_id === item.comm_id && !isComposing;
                return (
                  <div
                    key={item.comm_id}
                    className={`comm-item-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => selectItem(item)}
                  >
                    <div className="comm-item-top">
                      <span className="comm-recipient" title={item.recipient}>
                        {folder === 'inbox' ? `From: ${item.sender_id}` : `To: ${item.recipient}`}
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className={`status-tag status-${item.status}`}>{item.status}</span>
                        {item.status === 'draft' && (
                          <button
                            type="button"
                            title="Discard draft"
                            onClick={(e) => promptDeleteDraft(item.comm_id, e)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: '#94A3B8',
                              cursor: 'pointer',
                              padding: '2px',
                              display: 'flex',
                              alignItems: 'center',
                            }}
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="comm-item-subject">{item.subject || '(No Subject)'}</div>
                    <div className="comm-item-snippet">{item.body.slice(0, 75)}...</div>
                    <div className="comm-item-footer">
                      <span className="comm-time">{item.timestamp}</span>
                      <span className="comm-id-pill">{item.comm_id}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Reader / Editor Pane */}
        <div className="comms-detail-pane">

          {isEditorMode ? (
            /* Unified Editor for New Email or Editing Existing Draft */
            <div className="compose-editor-box">
              <div className="editor-header">
                <div>
                  <h3>
                    {isComposing
                      ? 'Compose Corporate Email'
                      : `Draft Message: ${selectedItem?.comm_id}`}
                  </h3>
                  <span className="subtext">
                    {isComposing
                      ? 'Create a new corporate email draft or send immediately via Outlook'
                      : `Created / Updated on ${selectedItem?.timestamp}`}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn-send-email"
                    onClick={promptSendDraft}
                    disabled={submitting}
                    style={{ padding: '0.45rem 0.9rem', fontSize: '0.8rem' }}
                    title="Send message immediately through Microsoft Outlook"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="22" y1="2" x2="11" y2="13"></line>
                      <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                    <span>{submitting ? 'Sending...' : 'Send via Outlook'}</span>
                  </button>

                  <button
                    type="button"
                    className="btn-save-draft"
                    onClick={promptSaveDraft}
                    disabled={submitting}
                    style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem' }}
                    title="Save changes to your drafts folder"
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '4px' }}>
                      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                      <polyline points="17 21 17 13 7 13 7 21"></polyline>
                      <polyline points="7 3 7 8 15 8"></polyline>
                    </svg>
                    <span>{submitting ? 'Saving...' : isComposing ? 'Save Draft' : 'Update Draft'}</span>
                  </button>

                  {isComposing && (
                    <button
                      type="button"
                      onClick={() => {
                        setIsComposing(false);
                        if (items.length > 0) selectItem(items[0]);
                      }}
                      style={{
                        background: 'transparent',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#94A3B8',
                        borderRadius: '6px',
                        padding: '0.45rem 0.75rem',
                        fontSize: '0.8rem',
                        cursor: 'pointer',
                      }}
                    >
                      Cancel
                    </button>
                  )}

                  {!isComposing && selectedItem?.status === 'draft' && (
                    <button
                      type="button"
                      onClick={() => promptDeleteDraft(selectedItem.comm_id)}
                      disabled={submitting}
                      style={{
                        background: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid rgba(239, 68, 68, 0.25)',
                        color: '#F87171',
                        borderRadius: '6px',
                        padding: '0.45rem 0.75rem',
                        fontSize: '0.8rem',
                        cursor: 'pointer',
                      }}
                    >
                      Discard
                    </button>
                  )}

                  <span className="outlook-tag">
                    {isComposing ? 'New Outlook' : 'Draft'}
                  </span>
                </div>
              </div>

              {/* Quick Contacts Bar */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                flexWrap: 'wrap',
                padding: '0.4rem 0',
                fontSize: '0.75rem',
                color: '#94A3B8'
              }}>
                <span>Quick To:</span>
                {QUICK_CONTACTS.map((qc) => (
                  <button
                    key={qc.email}
                    type="button"
                    onClick={() => setEditRecipient(qc.email)}
                    style={{
                      background: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#93C5FD',
                      borderRadius: '4px',
                      padding: '2px 8px',
                      fontSize: '0.72rem',
                      cursor: 'pointer'
                    }}
                  >
                    {qc.name}
                  </button>
                ))}
              </div>

              <div className="editor-fields">
                <div className="field-group">
                  <label>To (Recipient Email or Distribution List):</label>
                  <input
                    type="text"
                    placeholder="e.g. team@novatech.com, sarah.jenkins@novatech.com"
                    value={editRecipient}
                    onChange={(e) => setEditRecipient(e.target.value)}
                  />
                </div>
                <div className="field-group">
                  <label>Subject:</label>
                  <input
                    type="text"
                    placeholder="e.g. Sprint Planning Update"
                    value={editSubject}
                    onChange={(e) => setEditSubject(e.target.value)}
                  />
                </div>
                <div className="field-group full-height">
                  <label>Message Body:</label>
                  <textarea
                    rows={6}
                    placeholder="Type your enterprise message or announcement here..."
                    value={editBody}
                    onChange={(e) => setEditBody(e.target.value)}
                  />
                </div>
              </div>

              {/* Action Buttons: Always Visible and Sticky */}
              <div className="editor-actions">
                <button
                  type="button"
                  className="btn-send-email"
                  onClick={promptSendDraft}
                  disabled={submitting}
                  title="Send message immediately through Microsoft Outlook"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                  </svg>
                  <span>{submitting ? 'Sending...' : 'Send via Outlook'}</span>
                </button>

                <button
                  type="button"
                  className="btn-save-draft"
                  onClick={promptSaveDraft}
                  disabled={submitting}
                  title="Save changes to your drafts folder"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                    <polyline points="17 21 17 13 7 13 7 21"></polyline>
                    <polyline points="7 3 7 8 15 8"></polyline>
                  </svg>
                  <span>{submitting ? 'Saving...' : isComposing ? 'Save as Draft' : 'Update Draft'}</span>
                </button>

                {!isComposing && selectedItem?.status === 'draft' && (
                  <button
                    type="button"
                    onClick={() => promptDeleteDraft(selectedItem.comm_id)}
                    disabled={submitting}
                    style={{
                      background: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.25)',
                      color: '#F87171',
                      borderRadius: '8px',
                      padding: '0.65rem 1rem',
                      fontSize: '0.84rem',
                      cursor: 'pointer',
                      marginLeft: 'auto',
                    }}
                  >
                    Discard Draft
                  </button>
                )}

                {isComposing && (
                  <button
                    type="button"
                    onClick={() => {
                      setIsComposing(false);
                      if (items.length > 0) selectItem(items[0]);
                    }}
                    style={{
                      background: 'transparent',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#94A3B8',
                      borderRadius: '8px',
                      padding: '0.65rem 1rem',
                      fontSize: '0.84rem',
                      cursor: 'pointer',
                      marginLeft: 'auto',
                    }}
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>
          ) : selectedItem ? (
            /* Read Only View for Sent / Inbox */
            <div className="message-read-view">
              <div className="read-header">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <h2>{selectedItem.subject || '(No Subject)'}</h2>
                  <span className={`status-tag status-${selectedItem.status}`}>{selectedItem.status}</span>
                </div>
                <div className="read-meta-row">
                  <div className="meta-avatars">
                    <div className="avatar-chip">
                      {(folder === 'inbox' ? selectedItem.sender_id : selectedItem.recipient).charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="meta-to">
                        {folder === 'inbox' ? 'From: ' : 'To: '}
                        <strong>{folder === 'inbox' ? selectedItem.sender_id : selectedItem.recipient}</strong>
                      </div>
                      <div className="meta-from">
                        {folder === 'inbox' ? `Recipient: ${selectedItem.recipient}` : `Sender: ${selectedItem.sender_id}`}
                      </div>
                    </div>
                  </div>
                  <div className="meta-date">{selectedItem.timestamp}</div>
                </div>
              </div>

              <div className="read-body-content">
                <pre>{selectedItem.body}</pre>
              </div>

              <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem' }}>
                <button
                  type="button"
                  className="btn-send-email"
                  onClick={() => {
                    setIsComposing(true);
                    setSelectedItem(null);
                    setEditRecipient(folder === 'inbox' ? selectedItem.sender_id : selectedItem.recipient);
                    setEditSubject(`Re: ${selectedItem.subject || ''}`);
                    setEditBody(`\n\n--- Original Message ---\n${selectedItem.body}`);
                  }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="9 17 4 12 9 7"></polyline>
                    <path d="M20 18v-2a4 4 0 0 0-4-4H4"></path>
                  </svg>
                  <span>Reply</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="no-selection-placeholder">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                <polyline points="22,6 12,13 2,6"></polyline>
              </svg>
              <p>Select an email from the list or compose a new message.</p>
              <button
                type="button"
                className="compose-action-btn"
                style={{ marginTop: '1rem', width: 'auto', padding: '0.6rem 1.25rem' }}
                onClick={handleStartCompose}
              >
                Compose New Email
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        details={confirmModal.details}
        confirmText={confirmModal.confirmText}
        cancelText={confirmModal.cancelText}
        isDanger={confirmModal.isDanger}
        iconType={confirmModal.iconType}
        loading={submitting}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal((prev) => ({ ...prev, isOpen: false }))}
      />

      {/* 5-Second Auto-Vanishing Feedback Toast */}
      <ActionFeedbackToast
        message={toast.message}
        type={toast.type}
        title={toast.title}
        duration={5000}
        onClose={() => setToast({ message: null, type: 'success' })}
      />
    </div>
  );
};
