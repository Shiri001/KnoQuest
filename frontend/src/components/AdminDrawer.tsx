import React, { useState, useEffect } from 'react';
import { X, Shield, User, Check, Ban, RefreshCw, AlertCircle } from 'lucide-react';
import type { EmployeePersona, AdminEmployeeDetail } from '../types/chat';
import { fetchAdminEmployees, fetchAdminEmployeeDetail, updateAdminEmployee, setPermissionOverride, removePermissionOverride } from '../services/api';

interface AdminDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  adminId: string;
  onProfileUpdated?: () => void;
}

const ALL_PERMISSIONS = [
  { key: 'knowledge.read', label: 'Knowledge Base (Read)', category: 'Knowledge' },
  { key: 'documents.read', label: 'Enterprise Documents / SharePoint', category: 'Documents' },
  { key: 'employee_directory.read', label: 'Staff Directory Search', category: 'Directory' },
  { key: 'employee_profile.read', label: 'View Employee Profiles', category: 'Directory' },
  { key: 'hr.self', label: 'Personal HR & Leave Info', category: 'HR' },
  { key: 'hr.team', label: 'Team HR & Leave Overview', category: 'HR' },
  { key: 'hr.all', label: 'All Company Salaries & Payroll', category: 'HR' },
  { key: 'it.create_ticket', label: 'Create IT Helpdesk Ticket', category: 'IT' },
  { key: 'it.view_own_ticket', label: 'View Own IT Tickets', category: 'IT' },
  { key: 'it.view_all_tickets', label: 'View All Company IT Tickets', category: 'IT' },
  { key: 'it.update_ticket', label: 'Update & Assign IT Tickets', category: 'IT' },
  { key: 'calendar.read', label: 'View Enterprise Calendar', category: 'Calendar' },
  { key: 'calendar.create', label: 'Schedule Calendar Meetings', category: 'Calendar' },
  { key: 'communication.read', label: 'Search Corporate Emails & Teams', category: 'Comms' },
  { key: 'communication.draft', label: 'Draft Outlook Emails', category: 'Comms' },
  { key: 'communication.send', label: 'Send Emails & Teams Messages', category: 'Comms' },
  { key: 'admin.manage_employees', label: 'Top Team Admin Console Access', category: 'Admin' }
];

export const AdminDrawer: React.FC<AdminDrawerProps> = ({ isOpen, onClose, adminId, onProfileUpdated }) => {
  const [employees, setEmployees] = useState<EmployeePersona[]>([]);
  const [selectedEmp, setSelectedEmp] = useState<AdminEmployeeDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadEmployees();
    }
  }, [isOpen, adminId]);

  const loadEmployees = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const list = await fetchAdminEmployees();
      setEmployees(list);
      if (list.length > 0 && !selectedEmp) {
        loadDetail(list[0].company_id, list[0].employee_id);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Access Denied: Current user lacks admin privileges.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadDetail = async (companyId: string, employeeId: string) => {
    setErrorMessage(null);
    try {
      const detail = await fetchAdminEmployeeDetail(companyId, employeeId);
      setSelectedEmp(detail);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to fetch employee details');
    }
  };

  const handleRoleChange = async (newRole: string) => {
    if (!selectedEmp) return;
    setActionLoading(true);
    try {
      await updateAdminEmployee(selectedEmp.company_id, selectedEmp.employee_id, { role: newRole });
      await loadDetail(selectedEmp.company_id, selectedEmp.employee_id);
      await loadEmployees();
      setSuccessMessage(`Role updated to ${newRole}`);
      setTimeout(() => setSuccessMessage(null), 3000);
      if (onProfileUpdated) onProfileUpdated();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update role');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStatusToggle = async () => {
    if (!selectedEmp) return;
    const newStatus = selectedEmp.status === 'Active' ? 'Inactive' : 'Active';
    setActionLoading(true);
    try {
      await updateAdminEmployee(selectedEmp.company_id, selectedEmp.employee_id, { status: newStatus });
      await loadDetail(selectedEmp.company_id, selectedEmp.employee_id);
      await loadEmployees();
      setSuccessMessage(`Status updated to ${newStatus}`);
      setTimeout(() => setSuccessMessage(null), 3000);
      if (onProfileUpdated) onProfileUpdated();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to toggle status');
    } finally {
      setActionLoading(false);
    }
  };

  const handleTogglePermission = async (permKey: string, currentlyGranted: boolean) => {
    if (!selectedEmp) return;
    setActionLoading(true);
    try {
      // If currently granted, set explicit revocation (false). If revoked, set explicit grant (true).
      await setPermissionOverride(selectedEmp.company_id, selectedEmp.employee_id, permKey, !currentlyGranted);
      await loadDetail(selectedEmp.company_id, selectedEmp.employee_id);
      await loadEmployees();
      setSuccessMessage(`Permission '${permKey}' override updated.`);
      setTimeout(() => setSuccessMessage(null), 3000);
      if (onProfileUpdated) onProfileUpdated();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to set permission override');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResetOverride = async (permKey: string) => {
    if (!selectedEmp) return;
    setActionLoading(true);
    try {
      await removePermissionOverride(selectedEmp.company_id, selectedEmp.employee_id, permKey);
      await loadDetail(selectedEmp.company_id, selectedEmp.employee_id);
      await loadEmployees();
      setSuccessMessage(`Reverted '${permKey}' to role default.`);
      setTimeout(() => setSuccessMessage(null), 3000);
      if (onProfileUpdated) onProfileUpdated();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to reset override');
    } finally {
      setActionLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="admin-drawer" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="drawer-header">
          <div className="drawer-title">
            <Shield size={20} style={{ color: '#38BDF8' }} />
            <div>
              <h3>Top Team / Admin Console</h3>
              <p style={{ fontSize: '0.78rem', color: '#94A3B8', margin: 0 }}>
                Internal Company Employee Access & Permission Management
              </p>
            </div>
          </div>
          <button className="drawer-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Notifications */}
        {errorMessage && (
          <div className="drawer-banner error">
            <AlertCircle size={15} />
            <span>{errorMessage}</span>
          </div>
        )}
        {successMessage && (
          <div className="drawer-banner success">
            <Check size={15} />
            <span>{successMessage}</span>
          </div>
        )}

        {isLoading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#94A3B8' }}>
            <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite' }} />
            <p>Loading company registry...</p>
          </div>
        ) : (
          <div className="admin-body">
            {/* Left sidebar: Employee List */}
            <div className="admin-emp-list">
              <div className="admin-list-header">
                <span>Employee Registry ({employees.length})</span>
                <button onClick={loadEmployees} title="Refresh" className="icon-btn-small">
                  <RefreshCw size={13} />
                </button>
              </div>
              <div className="admin-list-scroll">
                {employees.map((emp) => {
                  const isSelected = selectedEmp?.employee_id === emp.employee_id;
                  return (
                    <div
                      key={emp.employee_id}
                      className={`admin-emp-card ${isSelected ? 'active' : ''}`}
                      onClick={() => loadDetail(emp.company_id, emp.employee_id)}
                    >
                      <div className="emp-card-top">
                        <span className="emp-name">{emp.name}</span>
                        <span className={`status-pill ${emp.status.toLowerCase()}`}>{emp.status}</span>
                      </div>
                      <div className="emp-card-sub">
                        <span>{emp.full_id}</span> • <span>{emp.role}</span>
                      </div>
                      <div className="emp-card-dept">{emp.department}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right details pane */}
            <div className="admin-emp-detail">
              {selectedEmp ? (
                <>
                  <div className="detail-header-card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <div className="avatar-circle">
                        <User size={22} />
                      </div>
                      <div>
                        <h4 style={{ margin: 0, fontSize: '1.1rem', color: '#F8FAFC' }}>
                          {selectedEmp.name}
                        </h4>
                        <div style={{ fontSize: '0.82rem', color: '#94A3B8' }}>
                          <code>{selectedEmp.full_id}</code> • {selectedEmp.email}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <button
                        className={`status-toggle-btn ${selectedEmp.status === 'Active' ? 'active' : 'inactive'}`}
                        onClick={handleStatusToggle}
                        disabled={actionLoading}
                      >
                        {selectedEmp.status === 'Active' ? 'Deactivate Employee' : 'Activate Employee'}
                      </button>
                    </div>
                  </div>

                  {/* Metadata and Role Selector */}
                  <div className="detail-row">
                    <div className="detail-col">
                      <label>Assigned Role</label>
                      <select
                        value={selectedEmp.role}
                        onChange={(e) => handleRoleChange(e.target.value)}
                        disabled={actionLoading}
                        className="admin-select"
                      >
                        <option value="Employee">Employee (Standard Access)</option>
                        <option value="Manager">Manager (Team Access)</option>
                        <option value="HR">HR (People & Payroll Access)</option>
                        <option value="IT">IT (Helpdesk & Infrastructure)</option>
                        <option value="Admin">Admin (Executive Top Team)</option>
                      </select>
                    </div>

                    <div className="detail-col">
                      <label>Department</label>
                      <input
                        type="text"
                        value={selectedEmp.department}
                        readOnly
                        className="admin-input-readonly"
                      />
                    </div>

                    <div className="detail-col">
                      <label>Designation</label>
                      <input
                        type="text"
                        value={selectedEmp.designation}
                        readOnly
                        className="admin-input-readonly"
                      />
                    </div>
                  </div>

                  {/* Permissions Table / Matrix */}
                  <div className="permissions-matrix-section">
                    <div className="matrix-header">
                      <h5>Effective Permissions for {selectedEmp.name}</h5>
                      <span className="matrix-count">
                        {selectedEmp.effective_permissions?.length || 0} active
                      </span>
                    </div>
                    <p style={{ fontSize: '0.78rem', color: '#94A3B8', marginTop: 0 }}>
                      Effective permissions are calculated from <strong>Role Defaults</strong> + <strong>Direct Admin Overrides</strong>.
                      Click any toggle to demonstrate live permission changes on the agent.
                    </p>

                    <div className="permissions-grid">
                      {ALL_PERMISSIONS.map((perm) => {
                        const isEffective = selectedEmp.effective_permissions?.includes(perm.key) || false;
                        const isRoleDefault = selectedEmp.role_permissions?.includes(perm.key) || false;
                        const override = selectedEmp.overrides?.find((o) => o.permission_key === perm.key);
                        const hasOverride = override !== undefined;

                        return (
                          <div
                            key={perm.key}
                            className={`perm-card ${isEffective ? 'granted' : 'denied'} ${hasOverride ? 'overridden' : ''}`}
                          >
                            <div className="perm-info">
                              <div className="perm-key-row">
                                <span className="perm-category">{perm.category}</span>
                                <code>{perm.key}</code>
                              </div>
                              <span className="perm-label">{perm.label}</span>
                              <div className="perm-badge-row">
                                {isRoleDefault ? (
                                  <span className="perm-source-pill role">Role: Granted</span>
                                ) : (
                                  <span className="perm-source-pill denied">Role: None</span>
                                )}
                                {hasOverride && (
                                  <span className="perm-source-pill override">
                                    Override: {override.is_granted ? 'Granted' : 'Revoked'}
                                  </span>
                                )}
                              </div>
                            </div>

                            <div className="perm-actions">
                              <button
                                className={`perm-toggle-btn ${isEffective ? 'btn-granted' : 'btn-denied'}`}
                                onClick={() => handleTogglePermission(perm.key, isEffective)}
                                disabled={actionLoading}
                                title={isEffective ? 'Click to Revoke' : 'Click to Grant'}
                              >
                                {isEffective ? <Check size={14} /> : <Ban size={14} />}
                                <span>{isEffective ? 'Allowed' : 'Denied'}</span>
                              </button>

                              {hasOverride && (
                                <button
                                  className="perm-reset-btn"
                                  onClick={() => handleResetOverride(perm.key)}
                                  disabled={actionLoading}
                                  title="Reset to role default"
                                >
                                  Reset
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </>
              ) : (
                <div style={{ padding: '2rem', textAlign: 'center', color: '#94A3B8' }}>
                  Select an employee from the registry.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
