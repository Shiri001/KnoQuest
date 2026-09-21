import React, { useState, useEffect } from 'react';
import type { EmployeePersona } from '../types/chat';
import { listTickets, createTicket } from '../services/api';
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

  const openCount = tickets.filter((t) => t.status === 'Open').length;
  const inProgressCount = tickets.filter((t) => t.status === 'In Progress').length;
  const resolvedCount = tickets.filter((t) => t.status === 'Resolved').length;

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
          <span className="metric-num">{tickets.length}</span>
          <span className="metric-label">Total Tickets</span>
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
        <h3>Enterprise Ticket Registry</h3>
        {loading ? (
          <div className="table-loading">
            <span className="spinner-icon"></span>
            <span>Fetching IT tickets...</span>
          </div>
        ) : tickets.length === 0 ? (
          <div className="table-empty">
            <p>No IT tickets recorded in the system.</p>
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
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => (
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
