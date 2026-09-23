import React, { useState, useEffect, useMemo } from 'react';
import { ShieldCheck, FileText, UploadCloud, Search } from 'lucide-react';
import type { EmployeePersona } from '../types/chat';
import { fetchPolicies } from '../services/api';

interface Policy {
  filename: string;
  title: string;
  category: string;
  tier?: string;
  length: number;
  summary: string;
  content: string;
}

interface DocumentsViewProps {
  currentUser?: EmployeePersona;
  onAskAboutPolicy: (policyTitle: string) => void;
  onOpenUploadModal: () => void;
}

export const DocumentsView: React.FC<DocumentsViewProps> = ({
  currentUser,
  onAskAboutPolicy,
  onOpenUploadModal,
}) => {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [readingPolicy, setReadingPolicy] = useState<Policy | null>(null);
  const [meta, setMeta] = useState<{
    authorizedCount: number;
    totalCount: number;
    userRole: string;
  }>({
    authorizedCount: 0,
    totalCount: 32,
    userRole: currentUser?.role || 'Employee',
  });

  useEffect(() => {
    setLoading(true);
    fetchPolicies()
      .then((res: any) => {
        const loaded = res.policies || [];
        setPolicies(loaded);
        setMeta({
          authorizedCount: res.authorized_count || loaded.length,
          totalCount: res.total_enterprise_documents || 32,
          userRole: res.user_role || currentUser?.role || 'Employee',
        });
      })
      .catch((err) => console.error('Failed to load policies:', err))
      .finally(() => setLoading(false));
  }, [currentUser?.role, currentUser?.employee_id]);

  const categories = useMemo(() => {
    const cats = new Set<string>();
    cats.add('All');
    policies.forEach((p) => {
      if (p.category) cats.add(p.category);
    });
    return Array.from(cats);
  }, [policies]);

  const filtered = policies.filter((p) => {
    const matchesCat = selectedCategory === 'All' || p.category === selectedCategory;
    const matchesSearch = !searchQuery.trim() ||
      p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.summary.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
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
          <UploadCloud size={16} />
          <span>Upload Custom Document</span>
        </button>
      </div>

      {/* Role-Based Clearance & Authorization Banner */}
      <div className="rbac-clearance-bar">
        <div className="rbac-clearance-info">
          <ShieldCheck size={20} className="shield-icon" />
          <div>
            <div className="rbac-title">
              Role-Authorized Documents: <strong>{meta.authorizedCount} of {meta.totalCount} Documents Accessible</strong>
            </div>
            <div className="rbac-sub">
              Access Clearance: <strong>{currentUser?.name || 'Active Employee'}</strong> (<span className="rbac-role-pill">{meta.userRole}</span> • {currentUser?.department || 'NovaTech Global'})
            </div>
          </div>
        </div>
        <div className="rbac-status-tag">
          <span className="live-indicator"></span>
          <span>Zero-Trust Role Gating Active</span>
        </div>
      </div>

      {/* Search & Category Filter Bar */}
      <div className="docs-toolbar-row">
        <div className="docs-search-wrapper">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            placeholder="Search authorized policies by title or keyword..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button type="button" className="clear-search-btn" onClick={() => setSearchQuery('')}>✕</button>
          )}
        </div>

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
      </div>

      {/* Policies Grid */}
      {loading ? (
        <div className="docs-loading">
          <span className="spinner-icon"></span>
          <span>Loading authorized enterprise policies for {meta.userRole}...</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="calendar-empty">
          <p>No authorized documents match your current filter.</p>
        </div>
      ) : (
        <div className="policies-grid">
          {filtered.map((pol) => (
            <div key={pol.filename} className="policy-doc-card">
              <div className="policy-card-top">
                <span className="policy-cat-badge">{pol.category}</span>
                <span className="policy-tier-badge">{pol.tier ? pol.tier.split(' - ')[0] : 'Tier 1'}</span>
              </div>
              <h3 className="policy-title">{pol.title}</h3>
              <p className="policy-snippet">{pol.summary}</p>

              <div className="policy-card-actions">
                <button
                  type="button"
                  className="btn-read-doc"
                  onClick={() => setReadingPolicy(pol)}
                >
                  <FileText size={14} />
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
                <span className="modal-subtext">{readingPolicy.category} • {readingPolicy.tier || 'Authorized'} • {readingPolicy.filename}</span>
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
