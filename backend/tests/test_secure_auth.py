import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import init_db, get_db_connection
from backend.app.config import settings

@pytest.fixture
def client():
    c = TestClient(app)
    c.cookies.clear()
    return c

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    conn = get_db_connection()
    conn.execute("UPDATE employees SET failed_login_attempts = 0, locked_until = NULL WHERE company_id = 'NOVA'")
    conn.commit()
    conn.close()

def test_login_successful_with_employee_id(client: TestClient):
    response = client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP001",
        "password": settings.DEV_DEFAULT_PASSWORD
    })
    assert response.status_code == 200
    data = response.json()
    assert "employee" in data
    assert data["employee"]["employee_id"] == "EMP001"
    assert data["employee"]["name"] == "Rahul Sharma"
    assert "password" not in data["employee"]
    assert "password_hash" not in data["employee"]
    assert "session_token" in data
    assert "knoquest_session" in response.cookies

def test_login_successful_with_corporate_email(client: TestClient):
    response = client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "rahul.sharma@novatech.com",
        "password": settings.DEV_DEFAULT_PASSWORD
    })
    assert response.status_code == 200
    data = response.json()
    assert data["employee"]["employee_id"] == "EMP001"
    assert data["employee"]["email"] == "rahul.sharma@novatech.com"

def test_login_invalid_password_returns_401(client: TestClient):
    response = client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP001",
        "password": "WrongPassword123!"
    })
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]
    assert "attempt(s) remaining" in response.json()["detail"]

def test_login_nonexistent_user_returns_generic_401(client: TestClient):
    response = client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP999",
        "password": settings.DEV_DEFAULT_PASSWORD
    })
    assert response.status_code == 401
    assert "Invalid Company ID, Employee ID/Email, or password." in response.json()["detail"]

def test_account_lockout_after_five_failed_attempts(client: TestClient):
    # Attempt 1 to 4 should fail with 401
    for i in range(1, 5):
        res = client.post("/api/auth/login", json={
            "company_id": "NOVA",
            "identifier": "EMP002",
            "password": "WrongPassword!"
        })
        assert res.status_code == 401

    # 5th attempt should lock the account and return 423 Locked
    res_5th = client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP002",
        "password": "WrongPassword!"
    })
    assert res_5th.status_code == 423
    assert "locked for 15 minutes" in res_5th.json()["detail"].lower()

    # Even with correct password, account remains locked
    res_locked = client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP002",
        "password": settings.DEV_DEFAULT_PASSWORD
    })
    assert res_locked.status_code == 423
    assert "temporarily locked" in res_locked.json()["detail"].lower()

def test_unauthenticated_request_rejected_with_401(client: TestClient):
    # Accessing protected profile endpoint without cookie
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]

def test_header_spoofing_prevented(client: TestClient):
    # Attempt to spoof employee identity via header without valid session
    res = client.get("/api/auth/me", headers={"X-Employee-ID": "NOVA-EMP005"})
    assert res.status_code == 401

    # Attempt to spoof chat request without session cookie
    chat_res = client.post("/api/chat", json={
        "message": "What is the policy?",
        "employee_id": "NOVA-EMP005"
    }, headers={"X-Employee-ID": "NOVA-EMP005"})
    assert chat_res.status_code == 401

def test_session_lifecycle_login_me_logout(client: TestClient):
    # 1. Login
    login_res = client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP003",
        "password": settings.DEV_DEFAULT_PASSWORD
    })
    assert login_res.status_code == 200

    # 2. Access /api/auth/me using session cookie stored in client
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Sarah Jenkins"
    assert me_res.json()["role"] == "HR"

    # 3. Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # 4. Subsequent access is rejected because session is revoked in DB
    # (Client cookies might have been cleared by response or session invalidated)
    me_after_logout = client.get("/api/auth/me")
    assert me_after_logout.status_code == 401

def test_bearer_token_authorization(client: TestClient):
    # 1. Login to get token
    login_res = client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP004",
        "password": settings.DEV_DEFAULT_PASSWORD
    })
    token = login_res.json()["session_token"]

    # Clear cookies so client only tests Bearer token
    client.cookies.clear()

    # 2. Access /api/auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Marcus Vance"
    assert me_res.json()["role"] == "IT"
