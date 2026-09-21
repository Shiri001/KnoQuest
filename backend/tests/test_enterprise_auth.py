import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import init_db, get_db_connection
from backend.app.auth import resolve_identity, check_permission, get_effective_permissions
from backend.app.mcp.registry import mcp_registry
from backend.app.mcp.tools import register_all_connectors
from backend.app.agent import foundry_agent

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    register_all_connectors()

def test_database_seeded_correctly():
    conn = get_db_connection()
    employees = conn.execute("SELECT * FROM employees").fetchall()
    roles = conn.execute("SELECT * FROM roles").fetchall()
    conn.close()

    assert len(employees) >= 6
    assert len(roles) >= 5
    emp_ids = [e["employee_id"] for e in employees]
    assert "EMP001" in emp_ids
    assert "EMP002" in emp_ids
    assert "EMP003" in emp_ids
    assert "EMP004" in emp_ids
    assert "EMP005" in emp_ids

def test_employee_permission_engine():
    # Rahul Sharma (Employee)
    emp1 = resolve_identity("NOVA-EMP001")
    assert emp1 is not None
    assert emp1.name == "Rahul Sharma"
    assert emp1.role == "Employee"
    assert check_permission(emp1, "hr.self") is True
    assert check_permission(emp1, "hr.all") is False
    assert check_permission(emp1, "it.view_all_tickets") is False
    assert check_permission(emp1, "it.create_ticket") is True
    assert check_permission(emp1, "calendar.read") is True

    # Sarah Jenkins (HR)
    hr_user = resolve_identity("NOVA-EMP003")
    assert hr_user is not None
    assert hr_user.role == "HR"
    assert check_permission(hr_user, "hr.all") is True

    # Marcus Vance (IT)
    it_user = resolve_identity("NOVA-EMP004")
    assert it_user is not None
    assert it_user.role == "IT"
    assert check_permission(it_user, "it.view_all_tickets") is True
    assert check_permission(it_user, "hr.all") is False

    # David Kumar (Admin)
    admin_user = resolve_identity("NOVA-EMP005")
    assert admin_user is not None
    assert check_permission(admin_user, "admin.manage_employees") is True
    assert check_permission(admin_user, "hr.all") is True

def test_agent_authorization_enforcement():
    emp1 = resolve_identity("NOVA-EMP001")
    hr_user = resolve_identity("NOVA-EMP003")

    # 1. Rahul asks for own HR -> ALLOWED
    res_self = foundry_agent.process_message("Show me my HR information", "conv-1", identity=emp1)
    assert "Personal HR & Benefits Summary for Rahul Sharma" in res_self.answer
    assert "Paid Annual Leave Remaining" in res_self.answer

    # 2. Rahul asks for everyone's salary -> DENIED by MCP Authorization layer
    res_all_denied = foundry_agent.process_message("Show me everyone's salary", "conv-2", identity=emp1)
    assert "Access Denied" in res_all_denied.answer
    assert "hr.all" in res_all_denied.answer

    # 3. Sarah asks for everyone's salary -> ALLOWED
    res_all_allowed = foundry_agent.process_message("Show me everyone's salary", "conv-3", identity=hr_user)
    assert "Confidential Payroll & Compensation Registry" in res_all_allowed.answer

from backend.app.config import settings

def test_top_team_admin_endpoints():
    # Non-admin attempt -> 403 Forbidden
    client.cookies.clear()
    login_emp = client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP001",
        "password": settings.DEV_DEFAULT_PASSWORD
    })
    assert login_emp.status_code == 200

    resp = client.get("/api/admin/employees")
    assert resp.status_code == 403
    assert "Access Denied" in resp.json()["detail"]

    # Admin access -> 200 OK
    client.cookies.clear()
    login_admin = client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP005",
        "password": settings.DEV_DEFAULT_PASSWORD
    })
    assert login_admin.status_code == 200

    resp_admin = client.get("/api/admin/employees")
    assert resp_admin.status_code == 200
    employees = resp_admin.json()
    assert len(employees) >= 6

def test_live_permission_override_flow():
    # Log in as David Kumar (Admin - EMP005)
    client.cookies.clear()
    client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP005",
        "password": settings.DEV_DEFAULT_PASSWORD
    })

    # Grant hr.all override to Rahul Sharma (EMP001)
    grant_resp = client.post(
        "/api/admin/employees/NOVA/EMP001/permissions",
        json={"permission_key": "hr.all", "is_granted": True}
    )
    assert grant_resp.status_code == 200

    # Verify Rahul now has hr.all
    emp1_updated = resolve_identity("NOVA-EMP001")
    assert check_permission(emp1_updated, "hr.all") is True

    # Rahul can now query everyone's salary
    res = foundry_agent.process_message("Show me everyone's salary", "conv-test-override", identity=emp1_updated)
    assert "Confidential Payroll & Compensation Registry" in res.answer

    # Revert override
    del_resp = client.delete(
        "/api/admin/employees/NOVA/EMP001/permissions/hr.all"
    )
    assert del_resp.status_code == 200

    # Verify Rahul is denied again
    emp1_reverted = resolve_identity("NOVA-EMP001")
    assert check_permission(emp1_reverted, "hr.all") is False
    res_denied = foundry_agent.process_message("Show me everyone's salary", "conv-test-revert", identity=emp1_reverted)
    assert "Access Denied" in res_denied.answer
