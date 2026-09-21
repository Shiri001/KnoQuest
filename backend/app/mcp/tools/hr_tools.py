from typing import Dict, Any, List
from ..registry import mcp_registry
from ...auth import IdentityContext
from ...database import get_db_connection

def handle_get_my_hr_profile(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.*, e.name, e.department, e.designation, e.role
        FROM hr_records h
        JOIN employees e ON h.company_id = e.company_id AND h.employee_id = e.employee_id
        WHERE h.company_id = ? AND h.employee_id = ?
    """, (identity.company_id, identity.employee_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "status": "not_found",
            "message": f"No HR record found for {identity.name} ({identity.full_id})."
        }

    return {
        "status": "success",
        "employee_id": identity.full_id,
        "name": row["name"],
        "department": row["department"],
        "leave_balance_paid_days": row["leave_balance_paid"],
        "leave_balance_sick_days": row["leave_balance_sick"],
        "salary_band": row["salary_band"],
        "compensation_notes": row["compensation_notes"],
        "performance_rating": row["performance_rating"]
    }

def handle_get_team_hr_summary(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.employee_id, e.name, e.department, e.designation, h.leave_balance_paid, h.performance_rating
        FROM employees e
        JOIN hr_records h ON e.company_id = h.company_id AND e.employee_id = h.employee_id
        WHERE e.department = ? AND e.status = 'Active'
    """, (identity.department,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "status": "success",
        "department": identity.department,
        "team_count": len(rows),
        "team_members": rows
    }

def handle_get_all_hr_payroll(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.company_id, e.employee_id, e.name, e.department, e.role, h.salary_band, h.compensation_notes, h.performance_rating
        FROM hr_records h
        JOIN employees e ON h.company_id = e.company_id AND h.employee_id = e.employee_id
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "status": "success",
        "total_records": len(rows),
        "payroll_records": rows
    }

def handle_request_leave(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    days = int(params.get("days", 1))
    leave_type = params.get("leave_type", "Paid")
    reason = params.get("reason", "Personal time off")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT leave_balance_paid, leave_balance_sick FROM hr_records WHERE company_id = ? AND employee_id = ?",
                   (identity.company_id, identity.employee_id))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return {"status": "error", "message": "HR record not found."}

    curr_paid = row["leave_balance_paid"]
    curr_sick = row["leave_balance_sick"]

    if leave_type.lower() == "sick":
        if curr_sick < days:
            conn.close()
            return {"status": "error", "message": f"Insufficient sick leave balance ({curr_sick} days available, requested {days})."}
        new_balance = curr_sick - days
        cursor.execute("UPDATE hr_records SET leave_balance_sick = ? WHERE company_id = ? AND employee_id = ?",
                       (new_balance, identity.company_id, identity.employee_id))
    else:
        if curr_paid < days:
            conn.close()
            return {"status": "error", "message": f"Insufficient paid leave balance ({curr_paid} days available, requested {days})."}
        new_balance = curr_paid - days
        cursor.execute("UPDATE hr_records SET leave_balance_paid = ? WHERE company_id = ? AND employee_id = ?",
                       (new_balance, identity.company_id, identity.employee_id))

    conn.commit()
    conn.close()

    return {
        "status": "approved",
        "employee_id": identity.full_id,
        "name": identity.name,
        "leave_type": leave_type,
        "days_deducted": days,
        "remaining_balance": new_balance,
        "reason": reason,
        "message": f"Leave request for {days} day(s) submitted and recorded successfully."
    }

def register():
    mcp_registry.register(
        name="get_my_hr_profile",
        description="Retrieve personal HR profile, leave balances, compensation band, and performance rating for currently authenticated employee. [Mock Service / SQLite]",
        category="HR",
        required_permission="hr.self",
        parameters_schema={"type": "object", "properties": {}},
        handler=handle_get_my_hr_profile
    )

    mcp_registry.register(
        name="get_team_hr_summary",
        description="Retrieve departmental/team HR overview and leave schedules for managers. [Mock Service / SQLite]",
        category="HR",
        required_permission="hr.team",
        parameters_schema={"type": "object", "properties": {}},
        handler=handle_get_team_hr_summary
    )

    mcp_registry.register(
        name="get_all_hr_payroll",
        description="Retrieve all enterprise salary bands, executive compensation, and performance evaluations across NovaTech. Restricted to HR/Top Team. [Mock Service / SQLite]",
        category="HR",
        required_permission="hr.all",
        parameters_schema={"type": "object", "properties": {}},
        handler=handle_get_all_hr_payroll
    )

    mcp_registry.register(
        name="request_leave",
        description="Submit a time off or sick leave request for the authenticated employee. [Mock Service / SQLite]",
        category="HR",
        required_permission="hr.self",
        parameters_schema={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days requested"},
                "leave_type": {"type": "string", "enum": ["Paid", "Sick"], "description": "Type of leave"},
                "reason": {"type": "string", "description": "Reason for leave"}
            },
            "required": ["days"]
        },
        handler=handle_request_leave
    )
