import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings
from backend.app.database import init_db, get_db_connection
from backend.app.mcp.tools.calendar_tools import parse_meeting_intent
from backend.app.agent import FoundryAgentService
from backend.app.auth import IdentityContext

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_auth():
    init_db()
    # Log in as NOVA-EMP001 (Rahul Sharma)
    client.post("/api/auth/login", json={
        "company_id": "NOVA",
        "identifier": "EMP001",
        "password": settings.DEV_DEFAULT_PASSWORD
    })

def test_parse_meeting_intent_relative_datetime():
    base_dt = datetime(2026, 9, 21, 10, 0)
    
    # 1. Tomorrow at 3:30 PM regarding Cloud Migration
    parsed = parse_meeting_intent(
        "Schedule a meeting with David Kumar tomorrow at 3:30 PM regarding Cloud Migration",
        base_dt=base_dt,
        organizer_email="rahul.sharma@novatech.com"
    )
    assert parsed["start_time"] == "2026-09-22 15:30"
    assert parsed["end_time"] == "2026-09-22 16:00"
    assert "Cloud Migration" in parsed["title"]
    assert "david.kumar@novatech.com" in parsed["attendees"]
    assert "rahul.sharma@novatech.com" in parsed["attendees"]

def test_parse_meeting_intent_iso_date_and_duration():
    base_dt = datetime(2026, 9, 21, 10, 0)
    
    # 2. Absolute ISO date with 1 hour duration
    parsed = parse_meeting_intent(
        "Book meeting on 2026-09-28 at 14:00 for 1 hour titled 'Q4 Architecture Review'",
        base_dt=base_dt
    )
    assert parsed["start_time"] == "2026-09-28 14:00"
    assert parsed["end_time"] == "2026-09-28 15:00"
    assert "Q4 Architecture Review" in parsed["title"]

def test_parse_meeting_intent_month_name():
    base_dt = datetime(2026, 9, 21, 10, 0)
    
    parsed = parse_meeting_intent(
        "Schedule a meeting on 25th September at 11 AM with Sarah about HR Benefits",
        base_dt=base_dt
    )
    assert parsed["start_time"] == "2026-09-25 11:00"
    assert parsed["end_time"] == "2026-09-25 11:30"
    assert "sarah.jenkins@novatech.com" in parsed["attendees"]

def test_chatbot_meeting_scheduling_intent():
    from backend.app.auth import resolve_identity
    agent = FoundryAgentService()
    identity = resolve_identity("NOVA", "EMP001")
    assert identity is not None
    
    # Ensure test slot is clean
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM calendar_events WHERE start_time = '2026-09-25 15:00';")
    conn.commit()
    conn.close()

    res = agent.process_message("Schedule a meeting with David Kumar on 2026-09-25 at 3 PM regarding Zero Trust Security", conversation_id="conv-test-1", identity=identity)
    assert "Calendar Meeting Scheduled" in res.answer
    assert "2026-09-25 15:00" in res.answer
    assert "Zero Trust Security" in res.answer

def test_email_draft_creation_and_inplace_update():
    # 1. Create initial draft
    create_res = client.post("/api/tools/communications/draft", json={
        "recipient": "elena.rostova@novatech.com",
        "subject": "Travel Budget Request",
        "body": "Initial request body."
    })
    assert create_res.status_code == 200
    data = create_res.json()
    draft_id = data["draft_id"]
    assert draft_id.startswith("COMM-")

    # 2. Update the same draft in-place
    update_res = client.post("/api/tools/communications/draft", json={
        "draft_id": draft_id,
        "recipient": "elena.rostova@novatech.com",
        "subject": "Travel Budget Request - Updated",
        "body": "Updated request body with per diem details."
    })
    assert update_res.status_code == 200
    up_data = update_res.json()
    assert up_data["draft_id"] == draft_id
    assert up_data["subject"] == "Travel Budget Request - Updated"

    # Verify in DB that no duplicate draft was created
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM communications WHERE comm_id = ?", (draft_id,))
    assert c.fetchone()[0] == 1
    conn.close()

def test_email_send_draft_finalization():
    # 1. Create draft
    create_res = client.post("/api/tools/communications/draft", json={
        "recipient": "marcus.vance@novatech.com",
        "subject": "Laptop Replacement Request",
        "body": "My laptop has battery degradation."
    })
    draft_id = create_res.json()["draft_id"]

    # 2. Send the draft
    send_res = client.post("/api/tools/communications/send", json={
        "draft_id": draft_id,
        "recipient": "marcus.vance@novatech.com",
        "subject": "Laptop Replacement Request",
        "body": "My laptop has battery degradation. Please approve.",
        "channel": "email"
    })
    assert send_res.status_code == 200
    send_data = send_res.json()
    assert send_data["status"] == "sent"
    assert send_data["comm_id"] == draft_id

    # Verify in DB that status is 'sent' and no duplicate exists
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT status FROM communications WHERE comm_id = ?", (draft_id,))
    row = c.fetchone()
    assert row[0] == "sent"
    conn.close()

def test_delete_draft_endpoint():
    # Create draft
    create_res = client.post("/api/tools/communications/draft", json={
        "recipient": "team@novatech.com",
        "subject": "Temporary Draft to Discard",
        "body": "Discard me."
    })
    draft_id = create_res.json()["draft_id"]

    # Delete draft
    del_res = client.delete(f"/api/tools/communications/{draft_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify deleted
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM communications WHERE comm_id = ?", (draft_id,))
    assert c.fetchone()[0] == 0
    conn.close()

def test_staff_directory_ask_ai_rich_dossier():
    from backend.app.auth import resolve_identity
    agent = FoundryAgentService()
    identity = resolve_identity("NOVA", "EMP001")
    assert identity is not None
    
    res = agent.process_message("Provide a comprehensive profile dossier for Sarah Jenkins from the staff directory, including their department, official designation, contact info, physical office, key responsibilities, and how to collaborate with them.", conversation_id="conv-test-2", identity=identity)
    assert "Employee Profile Dossier: Sarah Jenkins" in res.answer
    assert "VP of People & HR" in res.answer or "Vice President" in res.answer
    assert "NOVA-EMP003" in res.answer
    assert "sarah.jenkins@novatech.com" in res.answer
    assert "Key Responsibilities & Areas of Expertise" in res.answer
    assert "HR Policy Leadership" in res.answer
    assert "Quick Actions & Collaboration" in res.answer

def test_meeting_time_frame_overlap_rejection():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM calendar_events WHERE start_time LIKE '2026-10-15%';")
    conn.commit()
    conn.close()

    # 1. Book initial meeting
    res1 = client.post("/api/tools/calendar/book", json={
        "title": "Quarterly Budget Review",
        "start_time": "2026-10-15 10:00",
        "end_time": "2026-10-15 11:00",
        "attendees": "rahul.sharma@novatech.com, david.kumar@novatech.com",
        "location": "Finance Conf Room A"
    })
    assert res1.status_code == 200
    event_id = res1.json()["event_id"]

    # 2. Attempt to book overlapping meeting (10:30 - 11:30) with overlapping participant
    res_overlap = client.post("/api/tools/calendar/book", json={
        "title": "Conflicting Architecture Sync",
        "start_time": "2026-10-15 10:30",
        "end_time": "2026-10-15 11:30",
        "attendees": "rahul.sharma@novatech.com",
        "location": "Virtual Teams"
    })
    assert res_overlap.status_code == 409
    err_msg = res_overlap.json()["detail"]
    assert "Time frame conflict" in err_msg
    assert "cannot be overridden" in err_msg

    # 3. Adjacent meeting (11:00 - 12:00) should succeed (no overlap)
    res_adjacent = client.post("/api/tools/calendar/book", json={
        "title": "Adjacent Post-Review Sync",
        "start_time": "2026-10-15 11:00",
        "end_time": "2026-10-15 12:00",
        "attendees": "rahul.sharma@novatech.com",
        "location": "Virtual Teams"
    })
    assert res_adjacent.status_code == 200

    # Cleanup
    client.delete(f"/api/tools/calendar/{event_id}")
    client.delete(f"/api/tools/calendar/{res_adjacent.json()['event_id']}")

def test_meeting_deletion_flow():
    # Clean previous
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM calendar_events WHERE start_time LIKE '2026-10-20%';")
    conn.commit()
    conn.close()

    # 1. Book a meeting to delete
    res = client.post("/api/tools/calendar/book", json={
        "title": "Temporary Standup to Delete",
        "start_time": "2026-10-20 09:00",
        "end_time": "2026-10-20 09:30",
        "attendees": "rahul.sharma@novatech.com",
        "location": "Virtual"
    })
    assert res.status_code == 200
    event_id = res.json()["event_id"]

    # 2. Verify it shows in calendar
    cal_res = client.get("/api/tools/calendar")
    assert any(ev["event_id"] == event_id for ev in cal_res.json()["events"])

    # 3. Delete the meeting
    del_res = client.delete(f"/api/tools/calendar/{event_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"
    assert del_res.json()["event_id"] == event_id

    # 4. Verify it no longer appears in calendar
    cal_res_after = client.get("/api/tools/calendar")
    assert not any(ev["event_id"] == event_id for ev in cal_res_after.json()["events"])

    # 5. Second delete should return 404
    del_again = client.delete(f"/api/tools/calendar/{event_id}")
    assert del_again.status_code == 404

def test_chatbot_meeting_conflict_response():
    from backend.app.auth import resolve_identity
    agent = FoundryAgentService()
    identity = resolve_identity("NOVA", "EMP001")
    assert identity is not None

    # Clean test slot
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM calendar_events WHERE start_time LIKE '2026-10-22%';")
    conn.commit()
    conn.close()

    # Book a base meeting
    book_res = client.post("/api/tools/calendar/book", json={
        "title": "Sprint Planning A",
        "start_time": "2026-10-22 14:00",
        "end_time": "2026-10-22 15:00",
        "attendees": "rahul.sharma@novatech.com",
        "location": "Room 101"
    })
    assert book_res.status_code == 200
    event_id = book_res.json()["event_id"]

    # Try to schedule via chatbot at conflicting time
    chat_res = agent.process_message(
        "Schedule a meeting on 2026-10-22 at 14:30 titled 'Overriding Session'",
        conversation_id="conv-conflict-test",
        identity=identity
    )
    assert "Scheduling Conflict" in chat_res.answer
    assert "cannot be overridden" in chat_res.answer

    # Cleanup
    client.delete(f"/api/tools/calendar/{event_id}")
