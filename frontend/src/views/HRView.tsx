import React, { useState, useEffect } from 'react';
import type { EmployeePersona } from '../types/chat';
import { fetchHrProfile, fetchTeamHr, fetchAllHrPayroll, requestLeave } from '../services/api';

interface HRViewProps {
  currentUser: EmployeePersona;
}

export const HRView: React.FC<HRViewProps> = ({ currentUser }) => {
  const perms = currentUser.effective_permissions || [];
  const canViewTeam = perms.includes('hr.team') || currentUser.role === 'Admin' || currentUser.role === 'TopTeam';
  const canViewAllPayroll = perms.includes('hr.all') || currentUser.role === 'Admin' || currentUser.role === 'TopTeam';

  const [activeTab, setActiveTab] = useState<'personal' | 'team' | 'payroll'>('personal');
  const [profile, setProfile] = useState<any>(null);
  const [teamData, setTeamData] = useState<any>(null);
  const [payrollData, setPayrollData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Time off form
  const [leaveDays, setLeaveDays] = useState(1);
  const [leaveType, setLeaveType] = useState('Paid');
  const [leaveReason, setLeaveReason] = useState('Personal time off');
  const [leaveSubmitting, setLeaveSubmitting] = useState(false);
  const [leaveMessage, setLeaveMessage] = useState<string | null>(null);

  const loadPersonalProfile = async () => {
    setLoading(true);
    try {
      const p = await fetchHrProfile();
      setProfile(p);
    } catch (err) {
      console.error('Failed to load HR profile:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadTeam = async () => {
    try {
      const res = await fetchTeamHr();
      setTeamData(res);
    } catch (err: any) {
      setTeamData({ error: err.message });
    }
  };

  const loadPayroll = async () => {
    try {
      const res = await fetchAllHrPayroll();
      setPayrollData(res);
    } catch (err: any) {
      setPayrollData({ error: err.message });
    }
  };

  useEffect(() => {
    loadPersonalProfile();
    if (canViewTeam) loadTeam();
    if (canViewAllPayroll) loadPayroll();
  }, [currentUser]);

  const handleRequestLeave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLeaveSubmitting(true);
    setLeaveMessage(null);
    try {
      const res = await requestLeave({
        days: Number(leaveDays),
        leave_type: leaveType,
        reason: leaveReason,
      });
      setLeaveMessage(`Leave approved! ${res.message || ''}`);
      await loadPersonalProfile();
    } catch (err: any) {
      setLeaveMessage(`Error: ${err.message}`);
    } finally {
      setLeaveSubmitting(false);
    }
  };

  return (
    <div className="view-page-container hr-view">
      <div className="hr-header-block">
        <div>
          <h2>Human Resources & Personnel Portal</h2>
          <p className="subtext">Leave allocations, compensation bands, and personnel records</p>
        </div>

        {/* Tab Switcher */}
        <div className="hr-tab-pills">
          <button
            type="button"
            className={`hr-tab-pill ${activeTab === 'personal' ? 'active' : ''}`}
            onClick={() => setActiveTab('personal')}
          >
            My Profile & Leave
          </button>
          {canViewTeam && (
            <button
              type="button"
              className={`hr-tab-pill ${activeTab === 'team' ? 'active' : ''}`}
              onClick={() => setActiveTab('team')}
            >
              Team Summary
            </button>
          )}
          {canViewAllPayroll && (
            <button
              type="button"
              className={`hr-tab-pill ${activeTab === 'payroll' ? 'active' : ''}`}
              onClick={() => setActiveTab('payroll')}
            >
              Enterprise Payroll (Restricted)
            </button>
          )}
        </div>
      </div>

      {leaveMessage && (
        <div className={`action-alert-banner ${leaveMessage.startsWith('Error') ? 'error' : 'success'}`}>
          {leaveMessage}
        </div>
      )}

      {loading && (
        <div className="table-loading" style={{ margin: '1rem 0' }}>
          <span className="spinner-icon"></span>
          <span>Loading HR records...</span>
        </div>
      )}

      {activeTab === 'personal' && (
        <div className="hr-personal-grid">
          {/* Leave Balances */}
          <div className="hr-balance-cards-row">
            <div className="hr-stat-card border-blue">
              <span className="stat-label">Paid Annual Leave</span>
              <div className="stat-number-row">
                <span className="stat-value text-blue">{profile?.leave_balance_paid_days ?? 18}</span>
                <span className="stat-unit">days left</span>
              </div>
              <span className="stat-sub">Accrued monthly (20 days/yr)</span>
            </div>

            <div className="hr-stat-card border-emerald">
              <span className="stat-label">Sick & Medical Leave</span>
              <div className="stat-number-row">
                <span className="stat-value text-emerald">{profile?.leave_balance_sick_days ?? 10}</span>
                <span className="stat-unit">days left</span>
              </div>
              <span className="stat-sub">Fully paid medical allowance</span>
            </div>

            <div className="hr-stat-card border-amber">
              <span className="stat-label">Salary Band</span>
              <div className="stat-number-row">
                <span className="stat-value text-amber">{profile?.salary_band || 'Standard'}</span>
              </div>
              <span className="stat-sub">Designation: {currentUser.designation}</span>
            </div>

            <div className="hr-stat-card border-purple">
              <span className="stat-label">Performance Rating</span>
              <div className="stat-number-row">
                <span className="stat-value text-purple">{profile?.performance_rating || 'Exceeds Expectations'}</span>
              </div>
              <span className="stat-sub">Latest Q2 Performance Review</span>
            </div>
          </div>

          {/* Request Time Off Form */}
          <div className="dashboard-card time-off-form-card">
            <h3>Request Time-Off</h3>
            <p className="card-subtext">Deductions are verified directly against your live HR database allocation.</p>
            <form onSubmit={handleRequestLeave} className="time-off-form">
              <div className="form-row-3col">
                <div className="form-group">
                  <label>Leave Type</label>
                  <select value={leaveType} onChange={(e) => setLeaveType(e.target.value)}>
                    <option value="Paid">Paid Vacation</option>
                    <option value="Sick">Sick / Medical Leave</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Days Requested</label>
                  <input
                    type="number"
                    min={1}
                    max={15}
                    value={leaveDays}
                    onChange={(e) => setLeaveDays(Number(e.target.value))}
                  />
                </div>
                <div className="form-group">
                  <label>Reason</label>
                  <input
                    type="text"
                    placeholder="e.g. Family vacation"
                    value={leaveReason}
                    onChange={(e) => setLeaveReason(e.target.value)}
                  />
                </div>
              </div>

              <button type="submit" className="btn-submit-leave" disabled={leaveSubmitting}>
                {leaveSubmitting ? 'Recording Leave...' : 'Submit Leave Request'}
              </button>
            </form>
          </div>
        </div>
      )}

      {activeTab === 'team' && canViewTeam && (
        <div className="hr-team-section">
          <h3>Department Overview: {currentUser.department}</h3>
          {teamData?.team_members ? (
            <div className="table-responsive">
              <table className="enterprise-data-table">
                <thead>
                  <tr>
                    <th>Employee ID</th>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Paid Leave Balance</th>
                    <th>Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {teamData.team_members.map((m: any) => (
                    <tr key={m.employee_id}>
                      <td className="mono">{m.employee_id}</td>
                      <td className="font-medium">{m.name}</td>
                      <td>{m.designation}</td>
                      <td>{m.leave_balance_paid} days</td>
                      <td><span className="badge-rating">{m.performance_rating}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>{teamData?.error || 'No team records available.'}</p>
          )}
        </div>
      )}

      {activeTab === 'payroll' && canViewAllPayroll && (
        <div className="hr-payroll-section">
          <div className="payroll-warning-banner">
            🔒 <strong>Strictly Confidential Enterprise Payroll & Executive Compensation</strong>
          </div>
          {payrollData?.payroll_records ? (
            <div className="table-responsive">
              <table className="enterprise-data-table">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Employee ID</th>
                    <th>Name</th>
                    <th>Department</th>
                    <th>Role</th>
                    <th>Salary Band</th>
                    <th>Notes</th>
                    <th>Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {payrollData.payroll_records.map((r: any) => (
                    <tr key={r.employee_id}>
                      <td>{r.company_id}</td>
                      <td className="mono font-bold">{r.employee_id}</td>
                      <td className="font-medium">{r.name}</td>
                      <td>{r.department}</td>
                      <td>{r.role}</td>
                      <td className="mono text-emerald font-bold">{r.salary_band}</td>
                      <td className="text-sm">{r.compensation_notes}</td>
                      <td>{r.performance_rating}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>{payrollData?.error || 'Failed to load enterprise payroll.'}</p>
          )}
        </div>
      )}
    </div>
  );
};
