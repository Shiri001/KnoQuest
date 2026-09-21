import random
import re
from datetime import datetime
from typing import Dict, Any, List
from ..registry import mcp_registry
from ...auth import IdentityContext
from ...database import get_db_connection

def handle_search_emails(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    raw_query = params.get("query", "").strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Detect if user is asking specifically for drafts
    is_drafts_query = any(w in raw_query for w in ["draft", "drafts", "drafted"])
    is_sent_query = any(w in raw_query for w in ["sent", "outbox"])

    # Clean query prefixes
    clean_q = raw_query
    for prefix in [
        "where can i see the drafted mail", "where can i see my drafted mail",
        "where can i see drafted mail", "where can i see my drafts",
        "where is the drafted mail", "where are my drafted emails",
        "where are my drafts", "show my drafted emails", "show my drafts",
        "show drafts", "see drafts", "search emails for", "search emails",
        "search my emails for", "search inbox for", "my emails", "my messages"
    ]:
        if clean_q.startswith(prefix):
            clean_q = clean_q[len(prefix):].strip(" ?:.,!")

    if is_drafts_query:
        cursor.execute("""
            SELECT * FROM communications
            WHERE sender_id = ? AND status = 'draft'
            ORDER BY timestamp DESC
        """, (identity.employee_id,))
        folder = "Drafts"
    elif is_sent_query:
        cursor.execute("""
            SELECT * FROM communications
            WHERE sender_id = ? AND status = 'sent'
            ORDER BY timestamp DESC
        """, (identity.employee_id,))
        folder = "Sent Items"
    elif not clean_q:
        cursor.execute("""
            SELECT * FROM communications
            WHERE (recipient LIKE ? OR recipient = 'all-staff@novatech.com' OR sender_id = ?)
            ORDER BY timestamp DESC
        """, (f"%{identity.email}%", identity.employee_id))
        folder = "All Messages"
    else:
        cursor.execute("""
            SELECT * FROM communications
            WHERE (recipient LIKE ? OR recipient = 'all-staff@novatech.com' OR sender_id = ?)
              AND (LOWER(subject) LIKE ? OR LOWER(body) LIKE ?)
            ORDER BY timestamp DESC
        """, (f"%{identity.email}%", identity.employee_id, f"%{clean_q}%", f"%{clean_q}%"))
        folder = f"Search Results ('{clean_q}')"

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "status": "success",
        "folder": folder,
        "count": len(rows),
        "messages": rows
    }

def handle_list_email_drafts(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM communications
        WHERE sender_id = ? AND status = 'draft'
        ORDER BY timestamp DESC
    """, (identity.employee_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "status": "success",
        "folder": "Drafts",
        "draft_count": len(rows),
        "drafts": rows
    }

def parse_email_intent(prompt: str, default_recipient: str = "team@novatech.com") -> Dict[str, str]:
    """
    Intelligently extracts recipient, clean subject, and clean body from natural language prompts.
    Handles forms such as:
    - 'Draft email to team@novatech.com regarding Sprint Planning on Friday'
    - 'Send email to sarah.jenkins@novatech.com with subject "Q3 Review": Hi Sarah, please review.'
    - 'Draft email to Elena about expense report'
    """
    clean_p = prompt.strip()

    # 1. Extract email address if present
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', clean_p)
    recipient = email_match.group(0) if email_match else default_recipient

    # If a person's name is mentioned and no direct email found
    if not email_match:
        name_map = {
            "sarah": "sarah.jenkins@novatech.com",
            "elena": "elena.rostova@novatech.com",
            "marcus": "marcus.vance@novatech.com",
            "david": "david.kumar@novatech.com",
            "alex": "alex.chen@novatech.com",
            "rahul": "rahul.sharma@novatech.com",
            "team": "team@novatech.com",
            "hr": "hr@novatech.com",
            "it": "it-support@novatech.com"
        }
        for name, em in name_map.items():
            if re.search(r'\b' + name + r'\b', clean_p.lower()):
                recipient = em
                break

    # 2. Extract subject and body
    subject = "Enterprise Update"
    body = clean_p

    # Pattern: subject in quotes e.g. with subject "..."
    quoted_subj = re.search(r'(?:with\s+subject|subject:?)\s*["\']([^"\']+)["\']', clean_p, re.IGNORECASE)
    if quoted_subj:
        subject = quoted_subj.group(1).strip()
        remainder = clean_p[quoted_subj.end():].strip(" :,-")
        if remainder:
            body = remainder
        else:
            body = f"Hi,\n\nPlease find the update regarding {subject}.\n\nBest regards."
    else:
        subj_match = re.search(r'(?:regarding|about|with\s+subject)\s+([^:\.\n]+)', clean_p, re.IGNORECASE)
        if subj_match:
            raw_sub = subj_match.group(1).strip()
            if ":" in raw_sub:
                parts = raw_sub.split(":", 1)
                subject = parts[0].strip()
                body = parts[1].strip()
            else:
                subject = raw_sub
                colon_idx = clean_p.find(":")
                if colon_idx != -1:
                    body = clean_p[colon_idx+1:].strip()
                else:
                    body = f"Hi team,\n\nI am writing to share an update regarding {subject}.\n\nPlease let me know if you have any questions.\n\nBest regards."
        else:
            stripped = clean_p
            for pfx in ["draft email to ", "draft email regarding ", "draft an email to ", "draft an email ", "draft email ", "send email to ", "send an email to ", "compose email to "]:
                if stripped.lower().startswith(pfx):
                    stripped = stripped[len(pfx):].strip()
            if stripped.lower().startswith(recipient.lower()):
                stripped = stripped[len(recipient):].strip(" ,:-")
            subject = stripped[:50].strip() if stripped else "Enterprise Update"
            body = f"Hi,\n\n{stripped if stripped else clean_p}\n\nBest regards."

    return {
        "recipient": recipient,
        "subject": subject,
        "body": body
    }

def handle_draft_email(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    recipient = params.get("recipient", "").strip()
    subject = params.get("subject", "No Subject").strip()
    body = params.get("body", "").strip()
    draft_id = params.get("draft_id", "").strip()

    if not recipient or not body:
        return {"status": "error", "message": "Recipient and body are required."}

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    conn = get_db_connection()
    cursor = conn.cursor()

    if draft_id:
        cursor.execute("SELECT comm_id FROM communications WHERE comm_id = ? AND sender_id = ?", (draft_id, identity.employee_id))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE communications
                SET recipient = ?, subject = ?, body = ?, timestamp = ?
                WHERE comm_id = ? AND sender_id = ?;
            """, (recipient, subject, body, now, draft_id, identity.employee_id))
            conn.commit()
            conn.close()
            return {
                "status": "drafted",
                "draft_id": draft_id,
                "comm_id": draft_id,
                "from": identity.email,
                "to": recipient,
                "subject": subject,
                "body": body,
                "timestamp": now,
                "message": f"Email draft {draft_id} updated successfully in Outlook Drafts folder."
            }

    comm_id = f"COMM-{random.randint(400, 999)}"
    cursor.execute("""
        INSERT INTO communications (comm_id, comm_type, company_id, sender_id, recipient, subject, body, status, timestamp)
        VALUES (?, 'email', ?, ?, ?, ?, ?, 'draft', ?);
    """, (comm_id, identity.company_id, identity.employee_id, recipient, subject, body, now))
    conn.commit()
    conn.close()

    return {
        "status": "drafted",
        "draft_id": comm_id,
        "comm_id": comm_id,
        "from": identity.email,
        "to": recipient,
        "subject": subject,
        "body": body,
        "timestamp": now,
        "message": f"Email draft {comm_id} saved in Outlook Drafts folder. You can view it by asking 'Show my drafts' or opening Outlook."
    }

def handle_send_email(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    recipient = params.get("recipient", "").strip()
    subject = params.get("subject", "Enterprise Update").strip()
    body = params.get("body", "").strip()
    channel = params.get("channel", "email")  # 'email' or 'teams'
    draft_id = params.get("draft_id", "").strip()

    if not recipient or not body:
        return {"status": "error", "message": "Recipient and message body are required."}

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    conn = get_db_connection()
    cursor = conn.cursor()

    if draft_id:
        cursor.execute("SELECT comm_id FROM communications WHERE comm_id = ? AND sender_id = ?", (draft_id, identity.employee_id))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE communications
                SET comm_type = ?, recipient = ?, subject = ?, body = ?, status = 'sent', timestamp = ?
                WHERE comm_id = ? AND sender_id = ?;
            """, (channel, recipient, subject, body, now, draft_id, identity.employee_id))
            conn.commit()
            conn.close()
            return {
                "status": "sent",
                "comm_id": draft_id,
                "channel": "Microsoft Outlook" if channel == "email" else "Microsoft Teams",
                "sender": f"{identity.name} <{identity.email}>",
                "recipient": recipient,
                "subject": subject,
                "timestamp": now,
                "message": f"{'Email' if channel == 'email' else 'Teams message'} sent successfully to {recipient} (Draft {draft_id} finalized)."
            }

    comm_id = f"COMM-{random.randint(500, 999)}"
    cursor.execute("""
        INSERT INTO communications (comm_id, comm_type, company_id, sender_id, recipient, subject, body, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'sent', ?);
    """, (comm_id, channel, identity.company_id, identity.employee_id, recipient, subject, body, now))
    conn.commit()
    conn.close()

    return {
        "status": "sent",
        "comm_id": comm_id,
        "channel": "Microsoft Outlook" if channel == "email" else "Microsoft Teams",
        "sender": f"{identity.name} <{identity.email}>",
        "recipient": recipient,
        "subject": subject,
        "timestamp": now,
        "message": f"{'Email' if channel == 'email' else 'Teams message'} sent successfully to {recipient}."
    }

def handle_delete_communication(identity: IdentityContext, comm_id: str) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM communications WHERE comm_id = ? AND sender_id = ?", (comm_id, identity.employee_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected == 0:
        return {"status": "error", "message": f"Draft or message {comm_id} not found or unauthorized."}
    return {"status": "deleted", "comm_id": comm_id, "message": f"Message {comm_id} discarded."}

def register():
    mcp_registry.register(
        name="search_emails",
        description="Search Outlook corporate inbox, drafts, and Teams communications. [Mock Service / SQLite]",
        category="Communication",
        required_permission="communication.read",
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Subject, body, or folder keywords to search (e.g. 'drafts', 'VPN', 'sent')"}
            }
        },
        handler=handle_search_emails
    )

    mcp_registry.register(
        name="list_email_drafts",
        description="List all saved email drafts in Outlook for the authenticated employee. [Mock Service / SQLite]",
        category="Communication",
        required_permission="communication.read",
        parameters_schema={"type": "object", "properties": {}},
        handler=handle_list_email_drafts
    )

    mcp_registry.register(
        name="draft_email",
        description="Save an email draft in Outlook. [Mock Service / SQLite]",
        category="Communication",
        required_permission="communication.draft",
        parameters_schema={
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email message body"}
            },
            "required": ["recipient", "body"]
        },
        handler=handle_draft_email
    )

    mcp_registry.register(
        name="send_email",
        description="Send an email via Microsoft Outlook or post a message to Microsoft Teams. [Mock Service / SQLite]",
        category="Communication",
        required_permission="communication.send",
        parameters_schema={
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Recipient email or Teams channel"},
                "subject": {"type": "string", "description": "Subject line"},
                "body": {"type": "string", "description": "Message content"},
                "channel": {"type": "string", "enum": ["email", "teams"], "description": "Communication channel"}
            },
            "required": ["recipient", "body"]
        },
        handler=handle_send_email
    )
