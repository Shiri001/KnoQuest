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
    assert data["count"] == 12
    assert data["authorized_count"] == 12
    assert data["total_enterprise_documents"] == 32
    assert data["user_role"] == "Employee"
    categories = {p["category"] for p in data["policies"]}
    assert "Human Resources" in categories
    assert "Information Technology" in categories

def test_policies_endpoint_rbac_all_roles():
    # 1. Employee (EMP001) -> 12 Tier 1 docs
    client.post("/api/auth/login", json={"company_id": "NOVA", "identifier": "EMP001", "password": settings.DEV_DEFAULT_PASSWORD})
    res_emp = client.get("/api/tools/documents/policies")
    assert res_emp.status_code == 200
    emp_data = res_emp.json()
    assert emp_data["authorized_count"] == 12
    assert emp_data["total_enterprise_documents"] == 32
    assert emp_data["user_role"] == "Employee"
    emp_filenames = {p["filename"] for p in emp_data["policies"]}
    assert "Code_of_Conduct.txt" in emp_filenames
    assert "Workplace_Health_Safety.txt" in emp_filenames
    assert "Board_Resolution_Project_Titan_Merger.txt" not in emp_filenames
    assert "Executive_Compensation_Salary_Grids.txt" not in emp_filenames
    assert "Zero_Trust_Architecture_Infra_Runbook.txt" not in emp_filenames

    # 2. Manager (EMP002) -> 17 docs (Tier 1 + Tier 2)
    client.post("/api/auth/login", json={"company_id": "NOVA", "identifier": "EMP002", "password": settings.DEV_DEFAULT_PASSWORD})
    res_mgr = client.get("/api/tools/documents/policies")
    mgr_data = res_mgr.json()
    assert mgr_data["authorized_count"] == 17
    mgr_filenames = {p["filename"] for p in mgr_data["policies"]}
    assert "Manager_Performance_Review_SOP.txt" in mgr_filenames
    assert "Engineering_Hiring_Headcount_Budget.txt" in mgr_filenames
    assert "Board_Resolution_Project_Titan_Merger.txt" not in mgr_filenames
    assert "Executive_Compensation_Salary_Grids.txt" not in mgr_filenames

    # 3. HR (EMP003) -> 17 docs (Tier 1 + Tier 3)
    client.post("/api/auth/login", json={"company_id": "NOVA", "identifier": "EMP003", "password": settings.DEV_DEFAULT_PASSWORD})
    res_hr = client.get("/api/tools/documents/policies")
    hr_data = res_hr.json()
    assert hr_data["authorized_count"] == 17
    hr_filenames = {p["filename"] for p in hr_data["policies"]}
    assert "Executive_Compensation_Salary_Grids.txt" in hr_filenames
    assert "Internal_Workplace_Grievance_Investigation_Log.txt" in hr_filenames
    assert "Zero_Trust_Architecture_Infra_Runbook.txt" not in hr_filenames
    assert "Board_Resolution_Project_Titan_Merger.txt" not in hr_filenames

    # 4. IT (EMP004) -> 17 docs (Tier 1 + Tier 4)
    client.post("/api/auth/login", json={"company_id": "NOVA", "identifier": "EMP004", "password": settings.DEV_DEFAULT_PASSWORD})
    res_it = client.get("/api/tools/documents/policies")
    it_data = res_it.json()
    assert it_data["authorized_count"] == 17
    it_filenames = {p["filename"] for p in it_data["policies"]}
    assert "Zero_Trust_Architecture_Infra_Runbook.txt" in it_filenames
    assert "Disaster_Recovery_Failover_Protocol.txt" in it_filenames
    assert "Executive_Compensation_Salary_Grids.txt" not in it_filenames
    assert "Board_Resolution_Project_Titan_Merger.txt" not in it_filenames

    # 5. Admin (EMP005) -> All 32 docs
    client.post("/api/auth/login", json={"company_id": "NOVA", "identifier": "EMP005", "password": settings.DEV_DEFAULT_PASSWORD})
    res_adm = client.get("/api/tools/documents/policies")
    adm_data = res_adm.json()
    assert adm_data["authorized_count"] == 32
    adm_filenames = {p["filename"] for p in adm_data["policies"]}
    assert "Board_Resolution_Project_Titan_Merger.txt" in adm_filenames
    assert "Executive_Compensation_Salary_Grids.txt" in adm_filenames
    assert "Zero_Trust_Architecture_Infra_Runbook.txt" in adm_filenames
    assert "Manager_Performance_Review_SOP.txt" in adm_filenames
    assert "Code_of_Conduct.txt" in adm_filenames

def test_chatbot_knowledge_rbac_gating():
    from backend.app.auth import resolve_identity
    from backend.app.agent import FoundryAgentService
    agent = FoundryAgentService()
    
    # 1. Employee asks about Project Titan Merger (Unauthorized -> Zero Leakage)
    emp_identity = resolve_identity("NOVA", "EMP001")
    res_emp = agent.process_message(
        "What is the purchase price for Project Titan CloudScale AI acquisition?",
        conversation_id="conv-rbac-1",
        identity=emp_identity
    )
    assert "$145,000,000" not in res_emp.answer
    assert "couldn't find" in res_emp.answer or "Access Restricted" in res_emp.answer

    # 2. Admin asks about Project Titan Merger (Authorized -> Access Granted)
    adm_identity = resolve_identity("NOVA", "EMP005")
    res_adm = agent.process_message(
        "What is the purchase price for Project Titan CloudScale AI acquisition?",
        conversation_id="conv-rbac-2",
        identity=adm_identity
    )
    assert "145,000,000" in res_adm.answer or "Project Titan" in res_adm.answer

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

def test_agent_email_draft_and_send_visible_in_comms():
    from backend.app.auth import resolve_identity
    from backend.app.agent import FoundryAgentService
    agent = FoundryAgentService()
    emp_identity = resolve_identity("NOVA", "EMP001")

    # 1. Agent saves draft
    draft_msg = "Save draft of email to sarah.jenkins@novatech.com subject Weekly Sync body Let us meet tomorrow at 10 AM"
    res_draft = agent.process_message(draft_msg, conversation_id="conv-draft-test", identity=emp_identity)
    assert "Email Draft Saved" in res_draft.answer or "COMM-" in res_draft.answer

    # Verify visible in communications endpoint under drafts
    comms_drafts = client.get("/api/tools/communications?folder=drafts").json()
    assert any(c["recipient"] == "sarah.jenkins@novatech.com" and "Weekly Sync" in c["subject"] for c in comms_drafts["communications"])

    # 2. Agent sends email
    send_msg = "Send mail to alex.chen@novatech.com subject Deployment Ready body Server deployment complete and verified"
    res_send = agent.process_message(send_msg, conversation_id="conv-send-test", identity=emp_identity)
    assert "Email Sent Successfully" in res_send.answer or "alex.chen" in res_send.answer

    # Verify visible in communications endpoint under sent
    comms_sent = client.get("/api/tools/communications?folder=sent").json()
    assert any(c["recipient"] == "alex.chen@novatech.com" and "Deployment Ready" in c["subject"] for c in comms_sent["communications"])

def test_it_ticket_status_update_endpoint_and_agent():
    from backend.app.auth import resolve_identity
    from backend.app.agent import FoundryAgentService

    # 1. Create a ticket as EMP001
    create_res = client.post("/api/tools/tickets", json={
        "issue": "Monitor flicker on workstation 4B",
        "priority": "Low"
    })
    assert create_res.status_code == 200
    ticket_id = create_res.json()["ticket_id"]

    # 2. EMP001 (Employee) attempts to resolve ticket -> 403 Forbidden
    patch_unauth = client.patch(f"/api/tools/tickets/{ticket_id}", json={"status": "Resolved"})
    assert patch_unauth.status_code == 403

    # 3. Log in as EMP004 (IT Specialist) -> Successfully resolve ticket
    client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP004",
        "password": settings.DEV_DEFAULT_PASSWORD
    })
    patch_auth = client.patch(f"/api/tools/tickets/{ticket_id}", json={"status": "Resolved"})
    assert patch_auth.status_code == 200
    assert patch_auth.json()["ticket"]["status"] == "Resolved"

    # 4. Chatbot Agent update intent with IT Specialist identity
    it_identity = resolve_identity("NOVA", "EMP004")
    agent = FoundryAgentService()
    res_agent = agent.process_message(f"Resolve ticket {ticket_id}", conversation_id="conv-ticket-resolve", identity=it_identity)
    assert "Updated Successfully" in res_agent.answer or "Resolved" in res_agent.answer

def test_agent_intelligent_synthesis_email_ticket_meeting():
    from backend.app.auth import resolve_identity
    from backend.app.agent import FoundryAgentService
    agent = FoundryAgentService()
    emp_identity = resolve_identity("NOVA", "EMP001")

    # 1. Intelligent Email Composition: casual prompt is turned into a structured professional email
    email_prompt = "send an email to sarah.jenkins@novatech.com saying the project is delayed because our primary vendor had supply chain issues and we will deliver next Tuesday"
    res_email = agent.process_message(email_prompt, conversation_id="conv-intel-email", identity=emp_identity)
    assert "Email Sent Successfully" in res_email.answer or "sarah.jenkins" in res_email.answer

    # Verify that in the communications DB, the email is professional and not a raw command dump
    comms = client.get("/api/tools/communications?folder=sent").json()["communications"]
    sarah_email = next((c for c in comms if c["recipient"] == "sarah.jenkins@novatech.com"), None)
    assert sarah_email is not None
    # Must NOT have raw prompt prefix
    assert "send an email to sarah" not in sarah_email["body"].lower()
    # Must have professional greeting and sign-off
    assert "Hi Sarah" in sarah_email["body"]
    assert "Best regards" in sarah_email["body"]
    # Subject must be an executive subject line
    assert "Update" in sarah_email["subject"] or "Timeline" in sarah_email["subject"] or "Delivery" in sarah_email["subject"]

    # 2. Intelligent IT Ticket: casual complaint turned into a clean technical issue with High priority
    ticket_prompt = "create an it ticket: my screen keeps flickering on HDMI and it is impossible to work"
    res_ticket = agent.process_message(ticket_prompt, conversation_id="conv-intel-ticket", identity=emp_identity)
    assert "Hardware Display" in res_ticket.answer or "Screen" in res_ticket.answer
    assert "High" in res_ticket.answer

    # 3. Intelligent Meeting Scheduling: derives clean executive title
    meeting_prompt = "schedule meeting with Rahul on 2026-10-15 from 14:00 to 15:00 to review the architecture"
    res_meeting = agent.process_message(meeting_prompt, conversation_id="conv-intel-meeting", identity=emp_identity)
    assert "Architecture Review" in res_meeting.answer or "Technical Sync" in res_meeting.answer



