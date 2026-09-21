import random
from datetime import datetime
from typing import Dict, Any, List
from ..registry import mcp_registry
from ...auth import IdentityContext, check_permission
from ...database import get_db_connection

def handle_create_it_ticket(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    issue = params.get("issue", "").strip()
    priority = params.get("priority", "Medium")
    department = params.get("department") or identity.department

    if not issue:
        return {"status": "error", "message": "Issue description cannot be empty."}

    ticket_num = random.randint(1050, 9999)
    ticket_id = f"IT-{ticket_num}"
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO it_tickets (ticket_id, company_id, employee_id, user_name, department, issue, priority, status, assigned_to, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (ticket_id, identity.company_id, identity.employee_id, identity.name, department, issue, priority, "Open", "IT Tier-1 Helpdesk", now))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "ticket_id": ticket_id,
        "issue": issue,
        "priority": priority,
        "user_name": identity.name,
        "employee_id": identity.full_id,
        "department": department,
        "ticket_status": "Open",
        "assigned_to": "IT Tier-1 Helpdesk",
        "created_at": now,
        "message": f"IT Support Ticket {ticket_id} created successfully for {identity.name}. An IT engineer will follow up."
    }

def handle_list_my_it_tickets(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM it_tickets WHERE company_id = ? AND employee_id = ? ORDER BY created_at DESC
    """, (identity.company_id, identity.employee_id))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "status": "success",
        "employee": identity.name,
        "ticket_count": len(rows),
        "tickets": rows
    }

def handle_list_all_it_tickets(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM it_tickets ORDER BY created_at DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "status": "success",
        "view": "all_company_tickets",
        "ticket_count": len(rows),
        "tickets": rows
    }

def handle_update_it_ticket(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    ticket_id = params.get("ticket_id", "").strip().upper()
    new_status = params.get("status")
    assigned_to = params.get("assigned_to")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM it_tickets WHERE ticket_id = ?", (ticket_id,))
    ticket = cursor.fetchone()
    if not ticket:
        conn.close()
        return {"status": "error", "message": f"Ticket {ticket_id} not found."}

    updates = []
    vals = []
    if new_status:
        updates.append("status = ?")
        vals.append(new_status)
    if assigned_to:
        updates.append("assigned_to = ?")
        vals.append(assigned_to)

    if updates:
        vals.append(ticket_id)
        cursor.execute(f"UPDATE it_tickets SET {', '.join(updates)} WHERE ticket_id = ?", vals)
        conn.commit()

    cursor.execute("SELECT * FROM it_tickets WHERE ticket_id = ?", (ticket_id,))
    updated = cursor.fetchone()
    conn.close()

    return {
        "status": "success",
        "message": f"Ticket {ticket_id} updated.",
        "ticket": dict(updated)
    }

def register():
    mcp_registry.register(
        name="create_it_ticket",
        description="Creates a new IT helpdesk support ticket for hardware, software, or access requests. [Real SQLite]",
        category="IT",
        required_permission="it.create_ticket",
        parameters_schema={
            "type": "object",
            "properties": {
                "issue": {"type": "string", "description": "Description of the problem or request"},
                "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"], "description": "Priority level"}
            },
            "required": ["issue"]
        },
        handler=handle_create_it_ticket
    )

    mcp_registry.register(
        name="list_my_it_tickets",
        description="List the IT support tickets opened by the currently authenticated employee. [Real SQLite]",
        category="IT",
        required_permission="it.view_own_ticket",
        parameters_schema={"type": "object", "properties": {}},
        handler=handle_list_my_it_tickets
    )

    mcp_registry.register(
        name="list_all_it_tickets",
        description="List all company-wide IT support tickets. Requires IT Operations or Admin authorization. [Real SQLite]",
        category="IT",
        required_permission="it.view_all_tickets",
        parameters_schema={"type": "object", "properties": {}},
        handler=handle_list_all_it_tickets
    )

    mcp_registry.register(
        name="update_it_ticket",
        description="Update ticket status (Open, In Progress, Resolved) or technician assignment. Requires IT Operations authorization. [Real SQLite]",
        category="IT",
        required_permission="it.update_ticket",
        parameters_schema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Ticket ID e.g. IT-1002"},
                "status": {"type": "string", "enum": ["Open", "In Progress", "Resolved", "Closed"], "description": "New status"},
                "assigned_to": {"type": "string", "description": "Engineer name"}
            },
            "required": ["ticket_id"]
        },
        handler=handle_update_it_ticket
    )
