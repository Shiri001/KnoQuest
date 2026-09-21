import re
from typing import Dict, Any, List
from ..registry import mcp_registry
from ...auth import IdentityContext
from ...database import get_db_connection

def handle_search_employee_directory(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    query = params.get("query", "").strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT company_id, employee_id, name, email, role, department, designation, extension, location, status
        FROM employees
        WHERE status = 'Active'
    """)
    all_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not query:
        return {"count": len(all_rows), "employees": all_rows, "query": query}

    clean_q = query.lower().strip()

    # 1. Bi-directional name, email, and ID matching (handles long prompts like 'Tell me about Sarah Jenkins')
    name_matches = []
    for emp in all_rows:
        emp_name = emp["name"].lower()
        emp_email = emp["email"].lower()
        emp_id = emp["employee_id"].lower()
        full_emp_id = f"{emp['company_id']}-{emp['employee_id']}".lower()
        
        if (
            emp_name in clean_q or clean_q in emp_name or
            emp_email in clean_q or clean_q in emp_email or
            emp_id in clean_q or full_emp_id in clean_q
        ):
            name_matches.append(emp)

    if name_matches:
        return {"count": len(name_matches), "employees": name_matches, "query": query}

    # 2. Check title / role / department
    role_matches = []
    for emp in all_rows:
        emp_role = emp["role"].lower()
        emp_desig = (emp.get("designation") or "").lower()
        emp_dept = emp["department"].lower()
        if (
            emp_desig and (emp_desig in clean_q or clean_q in emp_desig) or
            emp_role and (emp_role in clean_q or clean_q in emp_role) or
            emp_dept and (clean_q == emp_dept or clean_q in emp_dept)
        ):
            role_matches.append(emp)

    if role_matches:
        return {"count": len(role_matches), "employees": role_matches, "query": query}

    # 3. Fallback to token overlap matching
    q_tokens = set(re.findall(r'\b[a-zA-Z0-9]{2,}\b', clean_q))
    stop_words = {
        "who", "is", "the", "for", "and", "our", "about", "what", "does", "she", "he",
        "handle", "regarding", "contact", "from", "staff", "directory", "profile", "dossier",
        "provide", "comprehensive", "including", "department", "official", "designation",
        "info", "physical", "office", "key", "responsibilities", "how", "collaborate", "with", "them"
    }
    filtered_tokens = {t for t in q_tokens if t not in stop_words}

    scored = []
    for emp in all_rows:
        emp_tokens = set(re.findall(r'\b[a-zA-Z0-9]{2,}\b', f"{emp['name']} {emp['role']} {emp['department']} {emp.get('designation', '')}".lower()))
        overlap = len(filtered_tokens.intersection(emp_tokens))
        if overlap > 0:
            scored.append((overlap, emp))

    scored.sort(key=lambda x: x[0], reverse=True)
    if scored:
        matched_emps = [emp for _, emp in scored]
        return {"count": len(matched_emps), "employees": matched_emps, "query": query}

    return {"count": 0, "employees": [], "query": query}

def handle_get_employee_profile(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    target_id = params.get("employee_id") or identity.employee_id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT company_id, employee_id, name, email, role, department, designation, extension, location, status, created_at
        FROM employees
        WHERE employee_id = ? OR employee_id = ?
    """, (target_id.upper(), target_id.replace("NOVA-", "").upper()))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"status": "not_found", "message": f"Employee {target_id} not found."}
    return {"status": "success", "profile": dict(row)}

def register():
    mcp_registry.register(
        name="search_employee_directory",
        description="Search NovaTech employee directory by name, role, department, skill, or ID. [Real SQLite]",
        category="Employee",
        required_permission="employee_directory.read",
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Name, role, department, or keyword to search (e.g. 'Elena', 'HR', 'IT')"
                }
            }
        },
        handler=handle_search_employee_directory
    )

    mcp_registry.register(
        name="get_employee_profile",
        description="Get detailed profile of an employee. Defaults to currently authenticated employee. [Real SQLite]",
        category="Employee",
        required_permission="employee_profile.read",
        parameters_schema={
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee ID (e.g., EMP001 or NOVA-EMP001). If omitted, returns current user's profile."
                }
            }
        },
        handler=handle_get_employee_profile
    )
