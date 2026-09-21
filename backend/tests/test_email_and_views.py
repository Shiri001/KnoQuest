import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.mcp.tools.communication_tools import parse_email_intent

from backend.app.config import settings
from backend.app.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_auth():
    init_db()
    # Log in as NOVA-EMP001
    client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP001",
        "password": settings.DEV_DEFAULT_PASSWORD
    })

def test_parse_email_intent():
    # 1. Subject extraction from "regarding ..."
    res1 = parse_email_intent("Draft email to team regarding Sprint Planning on Friday")
    assert res1["recipient"] == "team@novatech.com"
    assert "Sprint Planning" in res1["subject"]
    assert "team" in res1["recipient"]

    # 2. Email with specific recipient and explicit body
    res2 = parse_email_intent("Send email to sarah.jenkins@novatech.com regarding Q3 Review: Hi Sarah, please review.")
    assert res2["recipient"] == "sarah.jenkins@novatech.com"
    assert res2["subject"] == "Q3 Review"
    assert "Hi Sarah, please review." in res2["body"]

def test_policies_endpoint():
    res = client.get("/api/tools/documents/policies")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 8
    categories = {p["category"] for p in data["policies"]}
    assert "Human Resources" in categories
    assert "Information Technology" in categories

def test_communications_send_and_draft():
    # Save a draft
    draft_res = client.post("/api/tools/communications/draft", json={
        "recipient": "team@novatech.com",
        "subject": "Sprint Goals",
        "body": "Hi team, please find sprint goals."
    })
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    assert draft_data["status"] == "drafted"
    comm_id = draft_data["comm_id"]

    # Send communication
    send_res = client.post("/api/tools/communications/send", json={
        "recipient": "team@novatech.com",
        "subject": "Sprint Goals",
        "body": "Hi team, please find sprint goals.",
        "channel": "email",
        "draft_id": comm_id
    })
    assert send_res.status_code == 200
    send_data = send_res.json()
    assert send_data["status"] == "sent"

def test_calendar_and_hr_endpoints():
    # Calendar
    cal_res = client.get("/api/tools/calendar")
    assert cal_res.status_code == 200
    assert "events" in cal_res.json()

    # HR Profile
    hr_res = client.get("/api/tools/hr/profile")
    assert hr_res.status_code == 200
    assert hr_res.json()["status"] == "success"

    # Unauthorized payroll check (NOVA-EMP001 is standard employee)
    payroll_res = client.get("/api/tools/hr/payroll")
    assert payroll_res.status_code == 403

