import React, { useState, useEffect } from 'react';
import { Trash2 } from 'lucide-react';
import type { EmployeePersona } from '../types/chat';
import { fetchCalendar, bookMeeting, deleteMeeting } from '../services/api';
import { ConfirmationModal } from '../components/common/ConfirmationModal';
import { ActionFeedbackToast } from '../components/common/ActionFeedbackToast';

interface CalendarViewProps {
  currentUser: EmployeePersona;
}

interface CalendarEvent {
  event_id: string;
  company_id: string;
  employee_id: string;
  title: string;
  start_time: string;
  end_time: string;
  attendees: string;
  location: string;
  description?: string;
}

export const CalendarView: React.FC<CalendarViewProps> = ({ currentUser }) => {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  // Modal Form State
  const [title, setTitle] = useState('');
  const [startTime, setStartTime] = useState('2026-09-22 10:00');
  const [endTime, setEndTime] = useState('2026-09-22 10:30');
  const [attendees, setAttendees] = useState(currentUser.email);
  const [location, setLocation] = useState('Microsoft Teams (Virtual)');
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
    isDanger?: boolean;
    iconType?: 'send' | 'calendar' | 'ticket' | 'delete' | 'general';
    onConfirm: () => void;
  }>({
    isOpen: false,
    title: '',
    message: '',
    isDanger: false,
    iconType: 'calendar',
    onConfirm: () => {},
  });

  const loadCalendar = async () => {
    setLoading(true);
    try {
      const res = await fetchCalendar();
      setEvents(res.events || []);
    } catch (err) {
      console.error('Failed to fetch calendar:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCalendar();
  }, []);

  const handleBookMeeting = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !startTime.trim()) {
      setToast({
        message: 'Meeting title and start time are required.',
        type: 'error',
        title: 'Missing Details',
      });
      return;
    }

    setConfirmModal({
      isOpen: true,
      title: 'Confirm Meeting Reservation',
      message: 'Are you sure you want to proceed with booking this appointment on Microsoft Teams / Outlook?',
      details: [
        { label: 'Title', value: title.trim() },
        { label: 'Start Time', value: startTime.trim() },
        { label: 'End Time', value: endTime.trim() },
        { label: 'Attendees', value: attendees.trim() || currentUser.email },
        { label: 'Location', value: location.trim() },
      ],
      confirmText: 'Proceed & Schedule',
      isDanger: false,
      iconType: 'calendar',
      onConfirm: async () => {
        setConfirmModal((prev) => ({ ...prev, isOpen: false }));
        await executeBookMeeting();
      },
    });
  };

  const executeBookMeeting = async () => {
    setSubmitting(true);
    try {
      await bookMeeting({
        title: title.trim(),
        start_time: startTime.trim(),
        end_time: endTime.trim(),
        attendees: attendees.trim(),
        location: location.trim(),
      });
      setToast({
        message: `Meeting '${title.trim()}' scheduled successfully! Added to Outlook calendar.`,
        type: 'success',
        title: 'Meeting Scheduled',
      });
      setTitle('');
      setShowModal(false);
      await loadCalendar();
    } catch (err: any) {
      const isConflict = err.message && err.message.includes('Time frame conflict');
      setToast({
        message: err.message || 'Failed to book meeting.',
        type: 'error',
        title: isConflict ? 'Time Frame Conflict' : 'Scheduling Failed',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const promptCancelMeeting = (evt: CalendarEvent) => {
    setConfirmModal({
      isOpen: true,
      title: 'Cancel Scheduled Meeting',
      message: `Are you sure you want to cancel and delete "${evt.title}"? This appointment will be permanently removed from Microsoft Teams and Outlook for all attendees.`,
      details: [
        { label: 'Meeting Title', value: evt.title },
        { label: 'Time Slot', value: `${evt.start_time} - ${evt.end_time || ''}` },
        { label: 'Location', value: evt.location },
        { label: 'Attendees', value: evt.attendees },
        { label: 'Event ID', value: evt.event_id },
      ],
      confirmText: 'Yes, Cancel Meeting',
      isDanger: true,
      iconType: 'delete',
      onConfirm: async () => {
        setConfirmModal((prev) => ({ ...prev, isOpen: false }));
        await executeDeleteMeeting(evt);
      },
    });
  };

  const executeDeleteMeeting = async (evt: CalendarEvent) => {
    setSubmitting(true);
    try {
      await deleteMeeting(evt.event_id);
      setToast({
        message: `Meeting '${evt.title}' (${evt.event_id}) was cancelled and removed from the calendar.`,
        type: 'success',
        title: 'Meeting Cancelled',
      });
      await loadCalendar();
    } catch (err: any) {
      setToast({
        message: err.message || 'Failed to cancel meeting.',
        type: 'error',
        title: 'Cancellation Failed',
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="view-page-container calendar-view">
      <div className="calendar-header-row">
        <div>
          <h2>Calendar & Sync</h2>
          <p className="subtext">Synced appointments and meeting schedules across Microsoft Teams & Outlook</p>
        </div>
        <button
          type="button"
          className="btn-book-meeting"
          onClick={() => setShowModal(true)}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          <span>Schedule Meeting</span>
        </button>
      </div>

      {loading ? (
        <div className="calendar-loading">
          <span className="spinner-icon"></span>
          <span>Loading calendar events...</span>
        </div>
      ) : events.length === 0 ? (
        <div className="calendar-empty">
          <p>No upcoming meetings scheduled for your account.</p>
        </div>
      ) : (
        <div className="calendar-events-list">
          {events.map((evt) => (
            <div key={evt.event_id} className="calendar-event-card">
              <div className="event-time-column">
                <span className="event-date-text">{evt.start_time.split(' ')[0]}</span>
                <span className="event-time-text">
                  {evt.start_time.split(' ')[1] || '09:00'}
                  {evt.end_time ? ` - ${evt.end_time.split(' ')[1] || ''}` : ''}
                </span>
              </div>

              <div className="event-details-column">
                <div className="event-title-row">
                  <h3 className="event-title">{evt.title}</h3>
                  <span className="event-id-tag">{evt.event_id}</span>
                </div>
                <div className="event-meta-row">
                  <span className="event-location">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                      <circle cx="12" cy="10" r="3"></circle>
                    </svg>
                    {evt.location}
                  </span>
                  <span className="event-attendees">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                      <circle cx="9" cy="7" r="4"></circle>
                    </svg>
                    {evt.attendees}
                  </span>
                </div>
              </div>

              <div className="event-actions-column">
                <button
                  type="button"
                  className="btn-cancel-meeting"
                  onClick={() => promptCancelMeeting(evt)}
                  title={`Cancel meeting ${evt.event_id}`}
                >
                  <Trash2 size={14} />
                  <span>Cancel</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Schedule Modal */}
      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Schedule Team Meeting</h3>
              <button type="button" className="close-btn" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleBookMeeting} className="modal-form">
              <div className="form-group">
                <label>Meeting Title</label>
                <input
                  type="text"
                  placeholder="e.g. Q4 Sprint Retrospective"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
              </div>

              <div className="form-row-2col">
                <div className="form-group">
                  <label>Start Date & Time</label>
                  <input
                    type="text"
                    placeholder="YYYY-MM-DD HH:MM"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>End Date & Time</label>
                  <input
                    type="text"
                    placeholder="YYYY-MM-DD HH:MM"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Attendees (Emails)</label>
                <input
                  type="text"
                  placeholder="e.g. sarah.jenkins@novatech.com, david.kim@novatech.com"
                  value={attendees}
                  onChange={(e) => setAttendees(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Location / Meeting Room</label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-cancel" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={submitting}>
                  {submitting ? 'Booking...' : 'Book Meeting'}
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
        isDanger={confirmModal.isDanger}
        iconType={confirmModal.iconType || 'calendar'}
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
