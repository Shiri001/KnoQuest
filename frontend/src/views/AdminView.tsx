import React, { useState, useEffect } from 'react';
import { Shield, Check, Ban, RefreshCw, AlertCircle } from 'lucide-react';
import type { EmployeePersona, AdminEmployeeDetail } from '../types/chat';
import {
  fetchAdminEmployees,
  fetchAdminEmployeeDetail,
  updateAdminEmployee,
  setPermissionOverride,
  removePermissionOverride,
} from '../services/api';

interface AdminViewProps {
  currentUser: EmployeePersona;
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
  { key: 'admin.manage_employees', label: 'Top Team Admin Console Access', category: 'Admin' },
];

export const AdminView: React.FC<AdminViewProps> = ({ currentUser, onProfileUpdated }) => {
  const adminId = currentUser.full_id || currentUser.employee_id;
  const [employees, setEmployees] = useState<EmployeePersona[]>([]);
  const [selectedEmp, setSelectedEmp] = useState<AdminEmployeeDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    loadEmployees();
  }, [adminId]);

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
    setActionLoading(true);
    try {
      const detail = await fetchAdminEmployeeDetail(companyId, employeeId);
      setSelectedEmp(detail);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load employee detail.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRoleChange = async (newRole: string) => {
    if (!selectedEmp) return;
    setActionLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await updateAdminEmployee(
        selectedEmp.company_id,
        selectedEmp.employee_id,
        { role: newRole }
      );
      setSuccessMessage(`Updated role to ${newRole} for ${selectedEmp.name}.`);
      await loadDetail(selectedEmp.company_id, selectedEmp.employee_id);
      onProfileUpdated?.();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update role.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!selectedEmp) return;
    setActionLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await updateAdminEmployee(
        selectedEmp.company_id,
        selectedEmp.employee_id,
        { status: newStatus }
      );
      setSuccessMessage(`Updated status to ${newStatus} for ${selectedEmp.name}.`);
      await loadDetail(selectedEmp.company_id, selectedEmp.employee_id);
      onProfileUpdated?.();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update status.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleOverride = async (permissionKey: string, isGranted: boolean) => {
    if (!selectedEmp) return;
    setActionLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await setPermissionOverride(
        selectedEmp.company_id,
        selectedEmp.employee_id,
        permissionKey,
        isGranted
      );
      setSuccessMessage(`Applied override: ${permissionKey} = ${isGranted ? 'GRANTED' : 'REVOKED'}`);
      await loadDetail(selectedEmp.company_id, selectedEmp.employee_id);
      onProfileUpdated?.();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to apply override.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRemoveOverride = async (permissionKey: string) => {
    if (!selectedEmp) return;
    setActionLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await removePermissionOverride(
        selectedEmp.company_id,
        selectedEmp.employee_id,
        permissionKey
      );
      setSuccessMessage(`Removed override for ${permissionKey}. Reverted to role default.`);
      await loadDetail(selectedEmp.company_id, selectedEmp.employee_id);
      onProfileUpdated?.();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to remove override.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="view-page-container admin-view">
      <div className="admin-header-row">
        <div className="admin-title-wrap">
          <div className="admin-shield-icon">
            <Shield size={24} color="#F59E0B" />
          </div>
          <div>
            <h2>Top Team Employee Access Management</h2>
            <p className="subtext">Configure Roles, Grant/Revoke Permissions, and Control Agent MCP Execution</p>
          </div>
        </div>

        <button
          type="button"
          className="admin-refresh-btn"
          onClick={loadEmployees}
          disabled={isLoading}
        >
          <RefreshCw size={14} className={isLoading ? 'spin-icon' : ''} />
          <span>Refresh Directory</span>
        </button>
      </div>

      {errorMessage && (
        <div className="action-alert-banner error">
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {successMessage && (
        <div className="action-alert-banner success">
          <Check size={16} />
          <span>{successMessage}</span>
        </div>
      )}

      <div className="admin-workspace-grid">
        {/* Left: Employee Selection Pane */}
        <div className="admin-emp-pane">
          <div className="pane-header">
            <h3>Staff Members ({employees.length})</h3>
          </div>
          <div className="admin-emp-list">
            {employees.map((emp) => {
              const isSelected = selectedEmp?.employee_id === emp.employee_id;
              return (
                <div
                  key={emp.employee_id}
                  className={`admin-emp-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => loadDetail(emp.company_id, emp.employee_id)}
                >
                  <div className="admin-emp-avatar">{emp.name.charAt(0)}</div>
                  <div className="admin-emp-info">
                    <div className="emp-name">{emp.name}</div>
                    <div className="emp-role-dept">{emp.role} • {emp.department}</div>
                    <div className="emp-meta-row">
                      <span className="emp-id-tag">{emp.full_id || emp.employee_id}</span>
                      <span className={`emp-status-dot status-${emp.status?.toLowerCase()}`} />
                      <span className="emp-status-text">{emp.status}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: RBAC Editor Pane */}
        <div className="admin-rbac-pane">
          {selectedEmp ? (
            <div className="rbac-content">
              {/* Profile Card Header */}
              <div className="rbac-emp-header">
                <div>
                  <h3 className="rbac-name">{selectedEmp.name}</h3>
                  <div className="rbac-email">{selectedEmp.email} • {selectedEmp.full_id}</div>
                </div>

                <div className="rbac-controls-group">
                  <div className="control-item">
                    <label>Role:</label>
                    <select
                      value={selectedEmp.role}
                      onChange={(e) => handleRoleChange(e.target.value)}
                      disabled={actionLoading}
                    >
                      <option value="Employee">Employee</option>
                      <option value="Manager">Manager</option>
                      <option value="HR">HR</option>
                      <option value="Admin">Admin</option>
                      <option value="TopTeam">TopTeam</option>
                    </select>
                  </div>

                  <div className="control-item">
                    <label>Status:</label>
                    <select
                      value={selectedEmp.status}
                      onChange={(e) => handleStatusChange(e.target.value)}
                      disabled={actionLoading}
                    >
                      <option value="Active">Active</option>
                      <option value="Inactive">Inactive</option>
                      <option value="Suspended">Suspended</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Permission Matrix */}
              <div className="permission-matrix-section">
                <div className="matrix-title-row">
                  <h4>Effective Permissions & Dynamic Overrides</h4>
                  <span className="matrix-sub">Green = Active | Amber = Explicit Override | Gray = Inherited Role</span>
                </div>

                <div className="permissions-table-wrap">
                  <table className="permissions-table">
                    <thead>
                      <tr>
                        <th>Permission</th>
                        <th>Category</th>
                        <th>Status</th>
                        <th>Resolution</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ALL_PERMISSIONS.map((perm) => {
                        const isEffective = (selectedEmp.effective_permissions || []).includes(perm.key);
                        const isRoleDefault = (selectedEmp.role_permissions || []).includes(perm.key);
                        const override = (selectedEmp.overrides || []).find((o) => o.permission_key === perm.key);
                        const hasOverride = override !== undefined;

                        return (
                          <tr key={perm.key}>
                            <td>
                              <div className="perm-label">{perm.label}</div>
                              <div className="perm-key-sub mono">{perm.key}</div>
                            </td>
                            <td><span className="badge-cat">{perm.category}</span></td>
                            <td>
                              <span className={`perm-badge ${isEffective ? 'granted' : 'denied'}`}>
                                {isEffective ? 'GRANTED' : 'DENIED'}
                              </span>
                            </td>
                            <td>
                              {hasOverride ? (
                                <span className="resolution-override">
                                  {override.is_granted ? '⚡ Forced Grant' : '⛔ Forced Revoke'}
                                </span>
                              ) : (
                                <span className="resolution-role">
                                  Role: {selectedEmp.role} ({isRoleDefault ? 'Granted' : 'Denied'})
                                </span>
                              )}
                            </td>
                            <td>
                              <div className="action-buttons-group">
                                {!isEffective ? (
                                  <button
                                    type="button"
                                    className="btn-perm-grant"
                                    onClick={() => handleOverride(perm.key, true)}
                                    disabled={actionLoading}
                                    title="Explicitly grant this permission"
                                  >
                                    <Check size={12} />
                                    <span>Grant</span>
                                  </button>
                                ) : (
                                  <button
                                    type="button"
                                    className="btn-perm-revoke"
                                    onClick={() => handleOverride(perm.key, false)}
                                    disabled={actionLoading}
                                    title="Explicitly revoke this permission"
                                  >
                                    <Ban size={12} />
                                    <span>Revoke</span>
                                  </button>
                                )}

                                {hasOverride && (
                                  <button
                                    type="button"
                                    className="btn-perm-reset"
                                    onClick={() => handleRemoveOverride(perm.key)}
                                    disabled={actionLoading}
                                    title="Reset to role default"
                                  >
                                    Reset
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="no-emp-selected">
              <p>Select an employee from the left panel to manage their permissions.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
