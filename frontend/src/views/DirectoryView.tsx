import React, { useState, useEffect } from 'react';
import { searchDirectory } from '../services/api';

interface Employee {
  employee_id: string;
  name: string;
  email: string;
  department: string;
  designation: string;
  extension?: string;
  location?: string;
}

interface DirectoryViewProps {
  onAskAboutEmployee: (name: string) => void;
}

const DEPARTMENTS = ['All', 'Engineering', 'Product', 'Human Resources', 'Executive'];

export const DirectoryView: React.FC<DirectoryViewProps> = ({ onAskAboutEmployee }) => {
  const [query, setQuery] = useState('');
  const [selectedDept, setSelectedDept] = useState('All');
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDirectory();
  }, [query]);

  const fetchDirectory = async () => {
    setLoading(true);
    try {
      const res = await searchDirectory(query);
      setEmployees(res.employees || []);
    } catch (err) {
      console.error('Failed to search directory:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredEmployees = employees.filter((emp) => {
    if (selectedDept === 'All') return true;
    return emp.department.toLowerCase() === selectedDept.toLowerCase();
  });

  return (
    <div className="view-page-container directory-view">
      <div className="page-header-block">
        <div className="search-bar-row">
          <div className="directory-search-input-wrap">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input
              type="text"
              placeholder="Search employee by name, department, or title..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {query && (
              <button type="button" className="clear-search-btn" onClick={() => setQuery('')}>
                ×
              </button>
            )}
          </div>
        </div>

        {/* Department Filter Pills */}
        <div className="dept-pills-row">
          {DEPARTMENTS.map((dept) => (
            <button
              key={dept}
              type="button"
              className={`dept-filter-pill ${selectedDept === dept ? 'active' : ''}`}
              onClick={() => setSelectedDept(dept)}
            >
              {dept}
            </button>
          ))}
        </div>
      </div>

      {/* Employee Cards Grid */}
      {loading ? (
        <div className="directory-loading">
          <span className="spinner-icon"></span>
          <span>Searching staff directory...</span>
        </div>
      ) : filteredEmployees.length === 0 ? (
        <div className="directory-empty">
          <p>No employees match your search criteria.</p>
        </div>
      ) : (
        <div className="employee-cards-grid">
          {filteredEmployees.map((emp) => (
            <div key={emp.employee_id} className="employee-profile-card">
              <div className="emp-card-top">
                <div className="emp-avatar-circle">
                  {emp.name.charAt(0)}
                </div>
                <div className="emp-title-area">
                  <h3 className="emp-name">{emp.name}</h3>
                  <div className="emp-designation">{emp.designation}</div>
                </div>
                <span className="emp-id-badge">{emp.employee_id}</span>
              </div>

              <div className="emp-details-list">
                <div className="emp-detail-item">
                  <span className="item-label">Department:</span>
                  <span className="item-value dept-value">{emp.department}</span>
                </div>
                <div className="emp-detail-item">
                  <span className="item-label">Email:</span>
                  <a href={`mailto:${emp.email}`} className="item-value link-email">{emp.email}</a>
                </div>
                <div className="emp-detail-item">
                  <span className="item-label">Phone Ext:</span>
                  <span className="item-value">{emp.extension || 'Ext 401'}</span>
                </div>
                <div className="emp-detail-item">
                  <span className="item-label">Office:</span>
                  <span className="item-value">{emp.location || 'Headquarters / Remote'}</span>
                </div>
              </div>

              <div className="emp-card-footer">
                <button
                  type="button"
                  className="ask-ai-emp-btn"
                  onClick={() => onAskAboutEmployee(emp.name)}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                  </svg>
                  <span>Ask AI about {emp.name.split(' ')[0]}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
