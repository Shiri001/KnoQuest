import React, { useEffect, useState } from 'react';
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';

export interface ActionFeedbackToastProps {
  message: string | null;
  type?: 'success' | 'error' | 'info';
  title?: string;
  duration?: number; // In milliseconds, default 5000 (5 seconds)
  onClose: () => void;
}

export const ActionFeedbackToast: React.FC<ActionFeedbackToastProps> = ({
  message,
  type = 'success',
  title,
  duration = 5000,
  onClose,
}) => {
  const [isClosing, setIsClosing] = useState(false);

  useEffect(() => {
    if (!message) return;
    setIsClosing(false);

    const timer = setTimeout(() => {
      setIsClosing(true);
      setTimeout(onClose, 300); // Allow fade-out animation to complete
    }, duration);

    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  if (!message) return null;

  const defaultTitle =
    title ||
    (type === 'success'
      ? 'Action Completed Successfully'
      : type === 'error'
      ? 'Action Failed'
      : 'Enterprise Notice');

  const renderIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle2 size={20} className="toast-icon-success" />;
      case 'error':
        return <AlertTriangle size={20} className="toast-icon-error" />;
      default:
        return <Info size={20} className="toast-icon-info" />;
    }
  };

  return (
    <div
      className={`enterprise-feedback-toast toast-${type} ${isClosing ? 'toast-fade-out' : 'toast-fade-in'}`}
      role="alert"
      aria-live="polite"
    >
      <div className="toast-content-wrapper">
        <div className="toast-icon-column">
          <div className={`toast-icon-container icon-${type}`}>
            {renderIcon()}
          </div>
        </div>

        <div className="toast-body-column">
          <div className="toast-header-row">
            <span className="toast-title">{defaultTitle}</span>
            <span className="toast-timer-pill">Auto-dismiss in 5s</span>
          </div>
          <div className="toast-message-text">{message}</div>
        </div>

        <button
          type="button"
          className="toast-close-btn"
          onClick={() => {
            setIsClosing(true);
            setTimeout(onClose, 300);
          }}
          aria-label="Dismiss notification"
          title="Dismiss"
        >
          <X size={15} />
        </button>
      </div>

      {/* 5-Second Animated Progress Bar */}
      <div className="toast-progress-track">
        <div
          className={`toast-progress-fill fill-${type}`}
          style={{ animationDuration: `${duration}ms` }}
        />
      </div>
    </div>
  );
};
