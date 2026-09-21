import React, { useEffect } from 'react';
import { ShieldAlert, Send, Calendar, Ticket, Trash2, HelpCircle, X, ArrowRight } from 'lucide-react';

export interface ConfirmationModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  details?: { label: string; value: string }[];
  confirmText?: string;
  cancelText?: string;
  isDanger?: boolean;
  iconType?: 'send' | 'calendar' | 'ticket' | 'delete' | 'general';
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  title,
  message,
  details,
  confirmText = 'Proceed',
  cancelText = 'Cancel',
  isDanger = false,
  iconType = 'general',
  loading = false,
  onConfirm,
  onCancel,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  const renderIcon = () => {
    switch (iconType) {
      case 'send':
        return <Send size={22} className="text-blue-400" />;
      case 'calendar':
        return <Calendar size={22} className="text-cyan-400" />;
      case 'ticket':
        return <Ticket size={22} className="text-amber-400" />;
      case 'delete':
        return <Trash2 size={22} className="text-rose-400" />;
      default:
        return <HelpCircle size={22} className="text-blue-400" />;
    }
  };

  return (
    <div className="enterprise-modal-backdrop" onClick={onCancel}>
      <div
        className={`enterprise-confirm-dialog ${isDanger ? 'theme-danger' : 'theme-primary'}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
      >
        <div className="confirm-modal-header">
          <div className="confirm-header-left">
            <div className={`confirm-icon-badge ${isDanger ? 'badge-danger' : 'badge-primary'}`}>
              {renderIcon()}
            </div>
            <div>
              <h3 id="confirm-modal-title" className="confirm-modal-title">{title}</h3>
              <span className="confirm-modal-sub">Confirmation required to proceed</span>
            </div>
          </div>
          <button
            type="button"
            className="confirm-modal-close"
            onClick={onCancel}
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        <div className="confirm-modal-body">
          <p className="confirm-modal-message">{message}</p>

          {details && details.length > 0 && (
            <div className="confirm-details-card">
              {details.map((d, i) => (
                <div key={i} className="confirm-detail-row">
                  <span className="confirm-detail-label">{d.label}:</span>
                  <span className="confirm-detail-value">{d.value}</span>
                </div>
              ))}
            </div>
          )}

          <div className="confirm-security-notice">
            <ShieldAlert size={14} />
            <span>This action will be executed in your enterprise session.</span>
          </div>
        </div>

        <div className="confirm-modal-footer">
          <button
            type="button"
            className="confirm-btn-cancel"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelText}
          </button>
          <button
            type="button"
            className={`confirm-btn-proceed ${isDanger ? 'btn-danger' : 'btn-primary'}`}
            onClick={onConfirm}
            disabled={loading}
            autoFocus
          >
            {loading ? (
              <span>Processing...</span>
            ) : (
              <>
                <span>{confirmText}</span>
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
