import React, { useState, useEffect } from 'react';
import { fetchPolicies } from '../services/api';

interface Policy {
  filename: string;
  title: string;
  category: string;
  length: number;
  summary: string;
  content: string;
}

interface DocumentsViewProps {
  onAskAboutPolicy: (policyTitle: string) => void;
  onOpenUploadModal: () => void;
}

export const DocumentsView: React.FC<DocumentsViewProps> = ({
  onAskAboutPolicy,
  onOpenUploadModal,
}) => {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [readingPolicy, setReadingPolicy] = useState<Policy | null>(null);

  useEffect(() => {
    fetchPolicies()
      .then((res) => setPolicies(res.policies || []))
      .catch((err) => console.error('Failed to load policies:', err))
      .finally(() => setLoading(false));
  }, []);

  const categories = ['All', 'Human Resources', 'Information Technology', 'Finance & Travel', 'Operations & Remote Work'];

  const filtered = policies.filter((p) => {
    if (selectedCategory === 'All') return true;
    return p.category === selectedCategory;
  });

  return (
    <div className="view-page-container documents-view">
      <div className="docs-header-row">
        <div>
          <h2>Enterprise Knowledge Base & Policies</h2>
          <p className="subtext">
            Official NovaTech documentation indexed into Azure AI Search (<code>knoquest-novatech-index</code>)
          </p>
        </div>
        <button
          type="button"
          className="btn-upload-doc-view"
          onClick={onOpenUploadModal}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          <span>Upload Custom Document</span>
        </button>
      </div>

      {/* Category Pills */}
      <div className="docs-category-pills">
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            className={`category-pill ${selectedCategory === cat ? 'active' : ''}`}
            onClick={() => setSelectedCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Policies Grid */}
      {loading ? (
        <div className="docs-loading">
          <span className="spinner-icon"></span>
          <span>Indexing enterprise policies...</span>
        </div>
      ) : (
        <div className="policies-grid">
          {filtered.map((pol) => (
            <div key={pol.filename} className="policy-doc-card">
              <div className="policy-card-top">
                <span className="policy-cat-badge">{pol.category}</span>
                <span className="policy-size">{Math.round(pol.length / 100) / 10} KB</span>
              </div>
              <h3 className="policy-title">{pol.title}</h3>
              <p className="policy-snippet">{pol.summary}</p>

              <div className="policy-card-actions">
                <button
                  type="button"
                  className="btn-read-doc"
                  onClick={() => setReadingPolicy(pol)}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                    <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
                  </svg>
                  <span>Read Full Policy</span>
                </button>
                <button
                  type="button"
                  className="btn-ask-policy"
                  onClick={() => onAskAboutPolicy(pol.title)}
                >
                  Ask AI
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Read Policy Modal */}
      {readingPolicy && (
        <div className="modal-backdrop">
          <div className="modal-dialog policy-read-modal">
            <div className="modal-header">
              <div>
                <h3>{readingPolicy.title}</h3>
                <span className="modal-subtext">{readingPolicy.category} • {readingPolicy.filename}</span>
              </div>
              <button type="button" className="close-btn" onClick={() => setReadingPolicy(null)}>✕</button>
            </div>
            <div className="policy-full-content">
              <pre>{readingPolicy.content}</pre>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn-ask-policy"
                onClick={() => {
                  const t = readingPolicy.title;
                  setReadingPolicy(null);
                  onAskAboutPolicy(t);
                }}
              >
                Ask Agent about this Policy
              </button>
              <button type="button" className="btn-cancel" onClick={() => setReadingPolicy(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
