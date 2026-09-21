import React, { useState, useEffect } from 'react';
import { X, Wrench, RefreshCw, Plus, Clock, User, Building, CheckCircle2 } from 'lucide-react';
import { listTickets, createTicket } from '../services/api';

interface Ticket {
  ticket_id: string;
  status: string;
  issue: string;
  priority: string;
  user_name: string;
  department: string;
  created_at: string;
  assigned_to?: string;
  message?: string;
}

interface TicketsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onTicketCreated?: () => void;
}

export const TicketsDrawer: React.FC<TicketsDrawerProps> = ({
  isOpen,
  onClose,
  onTicketCreated,
}) => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [issue, setIssue] = useState('');
  const [priority, setPriority] = useState('Medium');
  const [userName, setUserName] = useState('');
  const [department, setDepartment] = useState('Engineering');
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchTicketsList();
    }
  }, [isOpen]);

  const fetchTicketsList = async () => {
    try {
      setLoading(true);
      const res = await listTickets();
      setTickets(res.tickets || []);
    } catch (err) {
      console.error('Failed to load tickets', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issue.trim()) return;
    try {
      setSubmitting(true);
      setFeedback(null);
      const res = await createTicket(issue, priority);
      setFeedback(`Ticket ${res.ticket_id} submitted successfully!`);
      setIssue('');
      setIsFormOpen(false);
      await fetchTicketsList();
      if (onTicketCreated) onTicketCreated();
    } catch (err: any) {
      setFeedback(`Error: ${err.message || 'Failed to submit'}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div className="drawer-title-group">
            <div className="drawer-icon-badge">
              <Wrench size={20} />
            </div>
            <div>
              <h3>IT Support Tickets</h3>
              <p>MCP Helpdesk Service • NovaTech Operations</p>
            </div>
          </div>
          <div className="drawer-actions">
            <button
              className="icon-btn"
              onClick={fetchTicketsList}
              title="Refresh tickets"
              disabled={loading}
            >
              <RefreshCw size={16} className={loading ? 'spinning' : ''} />
            </button>
            <button className="icon-btn" onClick={onClose} title="Close drawer">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="drawer-body">
          {feedback && (
            <div className="drawer-feedback-banner">
              <CheckCircle2 size={16} />
              <span>{feedback}</span>
            </div>
          )}

          <div className="drawer-toolbar">
            <span className="tickets-count-badge">
              {tickets.length} {tickets.length === 1 ? 'Ticket' : 'Tickets'} Logged
            </span>
            <button
              className="action-pill-btn"
              onClick={() => setIsFormOpen(!isFormOpen)}
            >
              <Plus size={15} />
              <span>{isFormOpen ? 'Cancel' : 'New Ticket'}</span>
            </button>
          </div>

          {isFormOpen && (
            <form className="quick-ticket-form" onSubmit={handleCreateTicket}>
              <h4>Submit New IT Incident</h4>
              <div className="form-group">
                <label>Issue Description *</label>
                <textarea
                  rows={2}
                  required
                  placeholder="e.g., VPN disconnects after 5 minutes, screen flickering..."
                  value={issue}
                  onChange={(e) => setIssue(e.target.value)}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Your Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Alex Smith"
                    value={userName}
                    onChange={(e) => setUserName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Department</label>
                  <select value={department} onChange={(e) => setDepartment(e.target.value)}>
                    <option value="Engineering">Engineering</option>
                    <option value="Human Resources">Human Resources</option>
                    <option value="Finance">Finance</option>
                    <option value="Facilities">Facilities</option>
                    <option value="Executive">Executive</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Priority</label>
                <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                  <option value="Low">Low Priority</option>
                  <option value="Medium">Medium Priority</option>
                  <option value="High">High Priority</option>
                  <option value="Critical">Critical Incident</option>
                </select>
              </div>

              <div className="form-actions">
                <button
                  type="submit"
                  className="primary-submit-btn"
                  disabled={submitting || !issue.trim()}
                >
                  {submitting ? 'Creating Ticket...' : 'Log Ticket to IT'}
                </button>
              </div>
            </form>
          )}

          {loading && tickets.length === 0 ? (
            <div className="drawer-empty-state">
              <RefreshCw size={24} className="spinning" style={{ color: '#3B82F6' }} />
              <p>Fetching active tickets from IT dispatch...</p>
            </div>
          ) : tickets.length === 0 ? (
            <div className="drawer-empty-state">
              <Wrench size={32} style={{ color: '#6B7280' }} />
              <h4>No IT Tickets Created Yet</h4>
              <p>Ask in chat to report an issue (e.g. "My laptop is broken. Create a ticket") or click New Ticket above.</p>
            </div>
          ) : (
            <div className="tickets-list">
              {tickets.map((t) => (
                <div key={t.ticket_id} className="ticket-card">
                  <div className="ticket-card-header">
                    <span className="ticket-id-tag">{t.ticket_id}</span>
                    <span className={`ticket-priority-pill priority-${t.priority.toLowerCase()}`}>
                      {t.priority}
                    </span>
                    <span className="ticket-status-pill">{t.status}</span>
                  </div>

                  <div className="ticket-issue-desc">{t.issue}</div>

                  <div className="ticket-footer-meta">
                    <div className="meta-item">
                      <Clock size={12} />
                      <span>{t.created_at}</span>
                    </div>
                    {t.user_name && (
                      <div className="meta-item">
                        <User size={12} />
                        <span>{t.user_name}</span>
                      </div>
                    )}
                    {t.department && (
                      <div className="meta-item">
                        <Building size={12} />
                        <span>{t.department}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
