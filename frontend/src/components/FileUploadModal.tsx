import React, { useRef, useState, useEffect } from 'react';
import { UploadCloud, X, AlertCircle } from 'lucide-react';
import { uploadDocument } from '../services/api';
import type { UploadedFile } from '../types/chat';

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (file: UploadedFile) => void;
}

export const FileUploadModal: React.FC<FileUploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      setErrorMsg(null);
      if (!dialog.open) {
        dialog.showModal();
      }
    } else {
      if (dialog.open) {
        dialog.close();
      }
    }
  }, [isOpen]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await processUpload(file);
  };

  const processUpload = async (file: File) => {
    try {
      setIsUploading(true);
      setErrorMsg(null);
      const res = await uploadDocument(file);
      onUploadSuccess(res);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to upload document');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      await processUpload(file);
    }
  };

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
        <h3>Upload Enterprise Policy</h3>
        <button
          onClick={onClose}
          className="icon-btn"
          style={{ border: 'none' }}
          title="Close dialog"
        >
          <X size={18} />
        </button>
      </div>

      <div
        className="dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <UploadCloud size={40} style={{ color: '#3B82F6', margin: '0 auto 0.75rem' }} />
        <p style={{ fontWeight: 600, marginBottom: '0.25rem', color: '#F8FAFC' }}>
          {isUploading ? 'Ingesting & Chunking Document...' : 'Click to browse or drop file here'}
        </p>
        <p style={{ fontSize: '0.78rem', color: '#9CA3AF' }}>
          Supported: PDF, DOCX, TXT (e.g. New_Travel_Policy.pdf)
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />
      </div>

      {errorMsg && (
        <div style={{ marginTop: '1rem', color: '#FB7185', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <AlertCircle size={14} />
          <span>{errorMsg}</span>
        </div>
      )}

      <p style={{ fontSize: '0.75rem', color: '#6B7280', marginTop: '1rem', textAlign: 'center' }}>
        Uploaded files are parsed into semantic chunks and made available for immediate natural language Q&A in this session.
      </p>
    </dialog>
  );
};
