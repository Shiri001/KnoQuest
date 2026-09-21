import React, { useRef, useEffect } from 'react';
import { X, FileText, Bookmark } from 'lucide-react';
import type { SourceCitation } from '../types/chat';

interface SourceCitationModalProps {
  citation: SourceCitation | null;
  onClose: () => void;
}

export const SourceCitationModal: React.FC<SourceCitationModalProps> = ({
  citation,
  onClose,
}) => {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (citation) {
      if (!dialog.open) {
        dialog.showModal();
      }
    } else {
      if (dialog.open) {
        dialog.close();
      }
    }
  }, [citation]);

  if (!citation) return null;

  return (
    <dialog
      ref={dialogRef}
      className="custom-modal"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
    >
      <div className="modal-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FileText size={18} style={{ color: '#3B82F6' }} />
          <h3>Document Source</h3>
        </div>
        <button
          onClick={onClose}
          className="icon-btn"
          style={{ border: 'none' }}
          title="Close dialog"
        >
          <X size={18} />
        </button>
      </div>

      <div style={{ marginBottom: '1rem' }}>
        <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#E2E8F0', marginBottom: '0.25rem' }}>
          {citation.source}
        </div>
        {citation.section && (
          <div style={{ fontSize: '0.78rem', color: '#93C5FD', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Bookmark size={13} />
            <span>{citation.section}</span>
          </div>
        )}
      </div>

      <div style={{
        background: '#0F172A',
        border: '1px solid #334155',
        borderRadius: '8px',
        padding: '1rem',
        fontSize: '0.85rem',
        color: '#CBD5E1',
        lineHeight: '1.6',
        maxHeight: '300px',
        overflowY: 'auto'
      }}>
        {citation.snippet || 'No excerpt available.'}
      </div>

      <p style={{ fontSize: '0.72rem', color: '#64748B', marginTop: '1rem' }}>
        This text was retrieved directly from the verified NovaTech enterprise knowledge repository.
      </p>
    </dialog>
  );
};
