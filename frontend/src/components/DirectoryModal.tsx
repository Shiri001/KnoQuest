import React, { useState, useEffect } from 'react';
import { X, Search, Users, Mail, Phone, MapPin, Building, ShieldCheck } from 'lucide-react';
import { searchDirectory } from '../services/api';

interface Employee {
  name: string;
  role: string;
  department: string;
  email: string;
  extension: string;
  location: string;
}

interface DirectoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectEmployee?: (emp: Employee) => void;
}

export const DirectoryModal: React.FC<DirectoryModalProps> = ({
  isOpen,
  onClose,
  onSelectEmployee,
}) => {
  const [query, setQuery] = useState('');
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState('All');

  useEffect(() => {
    if (isOpen) {
      loadDirectory('');
    }
  }, [isOpen]);

  const loadDirectory = async (searchQuery: string) => {
    try {
      setLoading(true);
      const res = await searchDirectory(searchQuery);
      setEmployees(res.employees || []);
    } catch (err) {
      console.error('Failed to search employee directory', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    loadDirectory(val);
  };

  const departments = ['All', 'Human Resources', 'Information Security', 'IT Operations', 'Finance', 'Facilities'];

  const filteredEmployees = employees.filter((emp) => {
    if (activeFilter === 'All') return true;
    return emp.department.toLowerCase().includes(activeFilter.toLowerCase());
  });

  if (!isOpen) return null;

  return (
    <div className="custom-modal-overlay" onClick={onClose}>
      <div className="custom-modal directory-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div className="drawer-icon-badge" style={{ background: 'linear-gradient(135deg, #059669, #10B981)' }}>
              <Users size={18} />
            </div>
            <div>
              <h3>NovaTech Staff Directory</h3>
              <p style={{ fontSize: '0.78rem', color: '#9CA3AF' }}>Find verified employee contacts & department leads</p>
            </div>
          </div>
          <button onClick={onClose} className="icon-btn" style={{ border: 'none' }} title="Close">
            <X size={18} />
          </button>
        </div>

        <div className="directory-search-bar">
          <Search size={16} style={{ color: '#9CA3AF' }} />
          <input
            type="text"
            placeholder="Search by name, role (e.g. CISO, VP, Engineer), or department..."
            value={query}
            onChange={handleSearchChange}
            autoFocus
          />
          {query && (
            <button
              onClick={() => {
                setQuery('');
                loadDirectory('');
              }}
              className="icon-btn"
              style={{ width: '24px', height: '24px', border: 'none' }}
            >
              <X size={14} />
            </button>
          )}
        </div>

        <div className="directory-dept-chips">
          {departments.map((dept) => (
            <button
              key={dept}
              className={`dept-chip ${activeFilter === dept ? 'active' : ''}`}
              onClick={() => setActiveFilter(dept)}
            >
              {dept}
            </button>
          ))}
        </div>

        <div className="directory-results-container">
          {loading ? (
            <div className="drawer-empty-state">
              <p>Searching staff directory...</p>
            </div>
          ) : filteredEmployees.length === 0 ? (
            <div className="drawer-empty-state">
              <p>No matching employees found for "{query}".</p>
            </div>
          ) : (
            <div className="directory-grid">
              {filteredEmployees.map((emp) => (
                <div
                  key={emp.email}
                  className="directory-card"
                  onClick={() => onSelectEmployee && onSelectEmployee(emp)}
                >
                  <div className="directory-card-top">
                    <div className="employee-avatar">
                      {emp.name.split(' ').map((n) => n[0]).join('')}
                    </div>
                    <div className="employee-main-info">
                      <div className="employee-name-row">
                        <h4>{emp.name}</h4>
                        <span title="Verified NovaTech Staff">
                          <ShieldCheck size={14} style={{ color: '#10B981' }} />
                        </span>
                      </div>
                      <div className="employee-role">{emp.role}</div>
                    </div>
                  </div>

                  <div className="employee-details-list">
                    <div className="detail-line">
                      <Building size={13} />
                      <span>{emp.department}</span>
                    </div>
                    <div className="detail-line">
                      <Mail size={13} />
                      <a href={`mailto:${emp.email}`} onClick={(e) => e.stopPropagation()}>{emp.email}</a>
                    </div>
                    <div className="detail-line">
                      <Phone size={13} />
                      <span>Ext. {emp.extension}</span>
                    </div>
                    <div className="detail-line">
                      <MapPin size={13} />
                      <span>{emp.location}</span>
                    </div>
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
