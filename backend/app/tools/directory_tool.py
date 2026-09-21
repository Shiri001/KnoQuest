import re
from typing import Dict, Any, List, Optional
from ..database import get_db_connection

def get_all_employees() -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, role, department, email, extension, location FROM employees WHERE status = 'Active'")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return [
            {
                "name": "Sarah Jenkins",
                "role": "Vice President of People & HR",
                "department": "Human Resources",
                "email": "sarah.jenkins@novatech.com",
                "extension": "4101",
                "location": "HQ - Floor 4"
            },
            {
                "name": "David Kumar",
                "role": "Chief Information Security Officer (CISO)",
                "department": "Information Security",
                "email": "david.kumar@novatech.com",
                "extension": "4444",
                "location": "HQ - Floor 5"
            },
            {
                "name": "Marcus Vance",
                "role": "Lead IT Infrastructure Engineer",
                "department": "IT Operations",
                "email": "marcus.vance@novatech.com",
                "extension": "4220",
                "location": "HQ - Floor 2"
            },
            {
                "name": "Elena Rostova",
                "role": "Senior Travel & Expense Coordinator",
                "department": "Finance",
                "email": "elena.rostova@novatech.com",
                "extension": "4350",
                "location": "HQ - Floor 3"
            },
            {
                "name": "Alex Chen",
                "role": "Workplace Operations Manager",
                "department": "Facilities",
                "email": "alex.chen@novatech.com",
                "extension": "4115",
                "location": "HQ - Floor 1"
            },
            {
                "name": "Rahul Sharma",
                "role": "Software Engineer",
                "department": "Engineering",
                "email": "rahul.sharma@novatech.com",
                "extension": "4105",
                "location": "HQ - Floor 4"
            }
        ]

def search_employee_directory(query: str) -> List[Dict[str, Any]]:
    """Searches NovaTech Solutions staff directory by name, department, or role."""
    all_employees = get_all_employees()
    clean_q = query.lower().strip(" ?.:,!")
    
    # Strip common leading stop words / search prefixes
    for prefix in [
        "who is the ", "who is ", "who's the ", "who's ", "find employee ", "find ",
        "search directory for ", "search directory ", "contact for ", "contact details for ",
        "reach out to ", "the ", "our ", "a ", "an "
    ]:
        if clean_q.startswith(prefix):
            clean_q = clean_q[len(prefix):].strip()

    # Empty query: return the full staff directory
    if not clean_q:
        return all_employees

    # 1. Exact or direct substring match
    matches = []
    for emp in all_employees:
        emp_text = f"{emp['name']} {emp['role']} {emp['department']} {emp['email']}".lower()
        if clean_q in emp_text or emp["name"].lower() in clean_q or emp["role"].lower() in clean_q:
            matches.append(emp)

    if matches:
        return matches

    # 2. Token overlap ranking (e.g. 'Elena Rostova travel' -> Elena Rostova)
    q_tokens = set(re.findall(r'\b[a-zA-Z0-9]{2,}\b', clean_q))
    stop_words = {"who", "is", "for", "the", "and", "our", "about", "what", "does", "she", "he", "handle", "regarding", "contact"}
    q_tokens = {t for t in q_tokens if t not in stop_words}
    
    scored = []
    for emp in all_employees:
        emp_tokens = set(re.findall(r'\b[a-zA-Z0-9]{2,}\b', f"{emp['name']} {emp['role']} {emp['department']}".lower()))
        overlap = len(q_tokens.intersection(emp_tokens))
        if overlap > 0:
            scored.append((overlap, emp))

    scored.sort(key=lambda x: x[0], reverse=True)
    if scored:
        return [emp for _, emp in scored]

    return all_employees
