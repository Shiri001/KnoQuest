import React, { useState, useEffect } from 'react';
import type { EmployeePersona } from '../types/chat';
import { listTickets, createTicket, updateTicketStatus } from '../services/api';
import { ConfirmationModal } from '../components/common/ConfirmationModal';
import { ActionFeedbackToast } from '../components/common/ActionFeedbackToast';

interface ITSupportViewProps {
  currentUser: EmployeePersona;
  onRefreshBadge?: () => void;
}

interface Ticket {
  ticket_id: string;
  user_name: string;
  department: string;
  issue: string;
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
  status: 'Open' | 'In Progress' | 'Resolved';
  created_at: string;
}

export const ITSupportView: React.FC<ITSupportViewProps> = ({ currentUser, onRefreshBadge }) => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  // Check if current user is IT Specialist or Admin with resolution rights
  const isITOrAdmin =
    currentUser.role === 'IT' ||
    currentUser.role === 'Admin' ||
    (currentUser.effective_permissions || []).includes('it.update_ticket');

  // Form State
  const [issue, setIssue] = useState('');
  const [priority, setPriority] = useState('Medium');
  const [department, setDepartment] = useState(currentUser.department || 'Engineering');
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<{
    message: string | null;
    type: 'success' | 'error' | 'info';
    title?: string;
  }>({ message: null, type: 'success' });

  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    details?: { label: string; value: string }[];
    confirmText?: string;
    onConfirm: () => void;
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
  });

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const res = await listTickets();
      setTickets(res.tickets || []);
      onRefreshBadge?.();
    } catch (err) {
      console.error('Failed to load tickets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  const handleCreateTicket = (e: React.FormEvent) => {
    e.preventDefault();
    if (!issue.trim()) {
      setToast({
        message: 'Please describe the issue before submitting a ticket.',
        type: 'error',
        title: 'Missing Details',
      });
      return;
    }

    setConfirmModal({
      isOpen: true,
      title: 'Confirm IT Support Ticket',
      message: 'Are you sure you want to proceed with raising this ticket with NovaTech IT Operations?',
      details: [
        { label: 'Issue Description', value: issue.trim() },
        { label: 'Priority Level', value: priority },
        { label: 'Department', value: department },
      ],
      confirmText: 'Proceed & Submit',
      onConfirm: async () => {
        setConfirmModal((prev) => ({ ...prev, isOpen: false }));
        await executeCreateTicket();
      },
    });
  };

  const executeCreateTicket = async () => {
    setSubmitting(true);
    try {
      const res = await createTicket(issue, priority);
      setToast({
        message: `Ticket ${res.ticket_id} created successfully! Dispatched to IT Support.`,
        type: 'success',
        title: 'Ticket Raised',
      });
      setIssue('');
      setShowModal(false);
      await fetchTickets();
    } catch (err: any) {
      setToast({
        message: `Error creating ticket: ${err.message}`,
        type: 'error',
        title: 'Submission Failed',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const promptResolveTicket = (ticket: Ticket) => {
    setConfirmModal({
      isOpen: true,
      title: 'Resolve IT Support Ticket',
      message: `Are you sure you want to mark ticket ${ticket.ticket_id} as Resolved? Once resolved, it will be archived from the active tickets list and the resolved count will increment.`,
      details: [
        { label: 'Ticket ID', value: ticket.ticket_id },
        { label: 'User', value: ticket.user_name },
        { label: 'Issue', value: ticket.issue },
        { label: 'Priority', value: ticket.priority },
      ],
      confirmText: 'Mark as Resolved',
      onConfirm: async () => {
        setConfirmModal((prev) => ({ ...prev, isOpen: false }));
        await executeUpdateStatus(ticket.ticket_id, 'Resolved');
      },
    });
  };

  const executeUpdateStatus = async (ticketId: string, newStatus: string) => {
    setSubmitting(true);
    try {
      await updateTicketStatus(ticketId, newStatus);
      setToast({
        message: `Ticket ${ticketId} marked as ${newStatus}. Archived from active queue.`,
        type: 'success',
        title: 'Ticket Resolved',
      });
      await fetchTickets();
    } catch (err: any) {
      setToast({
        message: `Error updating ticket: ${err.message}`,
        type: 'error',
        title: 'Update Failed',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const openCount = tickets.filter((t) => t.status === 'Open').length;
  const inProgressCount = tickets.filter((t) => t.status === 'In Progress').length;
  const resolvedCount = tickets.filter((t) => t.status === 'Resolved').length;
  // Resolved tickets are NOT visible in the active IT tickets tab
  const activeTickets = tickets.filter((t) => t.status !== 'Resolved');

  return (
    <div className="view-page-container it-support-view">
      {/* Top Banner & Stats */}
      <div className="it-header-row">
        <div>
          <h2>IT Support Helpdesk</h2>
          <p className="subtext">Hardware provisioning, software licenses, network access, and troubleshooting</p>
        </div>
        <button
          type="button"
          className="btn-create-ticket"
          onClick={() => setShowModal(true)}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          <span>Raise New Ticket</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="it-metrics-grid">
        <div className="it-metric-card">
          <span className="metric-num">{activeTickets.length}</span>
          <span className="metric-label">Active Tickets</span>
        </div>
        <div className="it-metric-card border-amber">
          <span className="metric-num text-amber">{openCount}</span>
          <span className="metric-label">Open</span>
        </div>
        <div className="it-metric-card border-blue">
          <span className="metric-num text-blue">{inProgressCount}</span>
          <span className="metric-label">In Progress</span>
        </div>
        <div className="it-metric-card border-emerald">
          <span className="metric-num text-emerald">{resolvedCount}</span>
          <span className="metric-label">Resolved</span>
        </div>
      </div>

      {/* Tickets Table */}
      <div className="tickets-table-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ margin: 0 }}>Active Support Tickets</h3>
            <span className="subtext" style={{ fontSize: '0.8rem', color: '#94A3B8' }}>
              Showing active open & in-progress tickets ({activeTickets.length}) • Resolved tickets archived
            </span>
          </div>
          {isITOrAdmin && (
            <span
              style={{
                fontSize: '0.75rem',
                background: 'rgba(56, 189, 248, 0.12)',
                color: '#38BDF8',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                padding: '0.25rem 0.65rem',
                borderRadius: '999px',
                fontWeight: 600,
              }}
            >
              🛡️ IT / Admin Clearance Active
            </span>
          )}
        </div>

        {loading ? (
          <div className="table-loading">
            <span className="spinner-icon"></span>
            <span>Fetching IT tickets...</span>
          </div>
        ) : activeTickets.length === 0 ? (
          <div className="table-empty">
            <p>No active IT tickets in the queue. All tickets have been resolved!</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="enterprise-data-table">
              <thead>
                <tr>
                  <th>Ticket ID</th>
                  <th>User</th>
                  <th>Department</th>
                  <th>Issue Summary</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Date Raised</th>
                  {isITOrAdmin && <th style={{ textAlign: 'center' }}>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {activeTickets.map((t) => (
                  <tr key={t.ticket_id}>
                    <td className="mono font-bold text-azure">{t.ticket_id}</td>
                    <td>{t.user_name}</td>
                    <td><span className="badge-dept">{t.department}</span></td>
                    <td className="issue-cell" title={t.issue}>{t.issue}</td>
                    <td>
                      <span className={`priority-badge priority-${t.priority.toLowerCase()}`}>
                        {t.priority}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge status-${t.status.toLowerCase().replace(' ', '-')}`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="text-secondary text-sm">{t.created_at}</td>
                    {isITOrAdmin && (
                      <td style={{ textAlign: 'center' }}>
                        <button
                          type="button"
                          className="btn-resolve-ticket"
                          onClick={() => promptResolveTicket(t)}
                          disabled={submitting}
                          title="Resolve and archive this ticket"
                          style={{
                            background: 'rgba(16, 185, 129, 0.12)',
                            border: '1px solid rgba(16, 185, 129, 0.35)',
                            color: '#34D399',
                            borderRadius: '6px',
                            padding: '0.35rem 0.75rem',
                            fontSize: '0.78rem',
                            fontWeight: 600,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
                          }}
                        >
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <polyline points="20 6 9 17 4 12"></polyline>
                          </svg>
                          <span>Resolve</span>
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Raise Ticket Modal */}
      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Raise IT Support Ticket</h3>
              <button type="button" className="close-btn" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleCreateTicket} className="modal-form">
              <div className="form-group">
                <label>Issue Description</label>
                <textarea
                  rows={4}
                  placeholder="Describe your hardware, software, or access problem in detail..."
                  value={issue}
                  onChange={(e) => setIssue(e.target.value)}
                  required
                />
              </div>

              <div className="form-row-2col">
                <div className="form-group">
                  <label>Priority</label>
                  <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                    <option value="Critical">Critical</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Department</label>
                  <select value={department} onChange={(e) => setDepartment(e.target.value)}>
                    <option value="Engineering">Engineering</option>
                    <option value="Product">Product</option>
                    <option value="Human Resources">Human Resources</option>
                    <option value="Finance">Finance</option>
                    <option value="Operations">Operations</option>
                  </select>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-cancel" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={submitting}>
                  {submitting ? 'Submitting...' : 'Submit Ticket'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        details={confirmModal.details}
        confirmText={confirmModal.confirmText}
        iconType="ticket"
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
