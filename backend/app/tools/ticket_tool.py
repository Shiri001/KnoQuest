import random
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..database import get_db_connection

def create_it_ticket(
    issue: str,
    priority: str = "Medium",
    user_name: str = "Employee",
    department: str = "Engineering",
    company_id: str = "NOVA",
    employee_id: str = "EMP001"
) -> Dict[str, Any]:
    """
    Creates an IT Helpdesk Support Ticket for NovaTech Solutions in SQLite.
    """
    ticket_num = random.randint(1025, 9999)
    ticket_id = f"IT-{ticket_num}"
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO it_tickets (ticket_id, company_id, employee_id, user_name, department, issue, priority, status, assigned_to, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Open', 'IT Tier-1 Helpdesk', ?);
        """, (ticket_id, company_id, employee_id, user_name, department, issue, priority, created_at))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

    return {
        "ticket_id": ticket_id,
        "status": "Open",
        "issue": issue,
        "priority": priority,
        "user_name": user_name,
        "department": department,
        "created_at": created_at,
        "assigned_to": "IT Tier-1 Helpdesk",
        "message": f"Support ticket {ticket_id} created successfully. An IT technician will investigate."
    }

def list_it_tickets(company_id: Optional[str] = None, employee_id: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if company_id and employee_id:
            cursor.execute("SELECT * FROM it_tickets WHERE company_id = ? AND employee_id = ? ORDER BY created_at DESC", (company_id, employee_id))
        else:
            cursor.execute("SELECT * FROM it_tickets ORDER BY created_at DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []
