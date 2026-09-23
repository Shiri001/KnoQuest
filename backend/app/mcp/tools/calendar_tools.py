import random
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from ..registry import mcp_registry
from ...auth import IdentityContext
from ...database import get_db_connection

def parse_meeting_intent(prompt: str, base_dt: Optional[datetime] = None, organizer_email: Optional[str] = None) -> Dict[str, Any]:
    """
    Intelligently parses meeting intent from natural language prompts, extracting:
    - Date (ISO, month name words, relative like today/tomorrow, day of week)
    - Time (12h AM/PM or 24h)
    - Duration and end_time
    - Meeting title/topic (regarding/about/to discuss/titled)
    - Attendees (emails and recognized employee names)
    - Location
    """
    if base_dt is None:
        base_dt = datetime.now()
    
    clean_p = prompt.strip()
    lower_p = clean_p.lower()

    # 1. Attendees extraction
    attendees_list: List[str] = []
    if organizer_email:
        attendees_list.append(organizer_email)
    
    # Check explicit emails in prompt
    found_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', clean_p)
    for em in found_emails:
        if em not in attendees_list:
            attendees_list.append(em)
    
    # Check recognized employee names
    name_map = {
        "sarah jenkins": "sarah.jenkins@novatech.com",
        "sarah": "sarah.jenkins@novatech.com",
        "david kumar": "david.kumar@novatech.com",
        "david": "david.kumar@novatech.com",
        "marcus vance": "marcus.vance@novatech.com",
        "marcus": "marcus.vance@novatech.com",
        "elena rostova": "elena.rostova@novatech.com",
        "elena": "elena.rostova@novatech.com",
        "alex chen": "alex.chen@novatech.com",
        "alex": "alex.chen@novatech.com",
        "rahul sharma": "rahul.sharma@novatech.com",
        "rahul": "rahul.sharma@novatech.com",
    }
    for name_key, em in name_map.items():
        if re.search(r'\b' + re.escape(name_key) + r'\b', lower_p):
            if em not in attendees_list:
                attendees_list.append(em)

    # 2. Date extraction
    target_date: Optional[datetime] = None

    # Check ISO format: YYYY-MM-DD
    iso_match = re.search(r'\b(20\d\d)[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b', clean_p)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        target_date = base_dt.replace(year=y, month=m, day=d)
    
    # Check Month Name: e.g. "25th September", "September 25", "Sep 25"
    if not target_date:
        month_map = {
            "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
            "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
            "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10, "oct": 10,
            "november": 11, "nov": 11, "december": 12, "dec": 12
        }
        m_match1 = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([a-z]+)\b', lower_p)
        m_match2 = re.search(r'\b([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\b', lower_p)
        if m_match1 and m_match1.group(2) in month_map:
            day_val = int(m_match1.group(1))
            month_val = month_map[m_match1.group(2)]
            target_date = base_dt.replace(month=month_val, day=day_val)
        elif m_match2 and m_match2.group(1) in month_map:
            month_val = month_map[m_match2.group(1)]
            day_val = int(m_match2.group(2))
            target_date = base_dt.replace(month=month_val, day=day_val)

    # Check relative days: "day after tomorrow", "tomorrow", "today"
    if not target_date:
        if "day after tomorrow" in lower_p:
            target_date = base_dt + timedelta(days=2)
        elif "tomorrow" in lower_p:
            target_date = base_dt + timedelta(days=1)
        elif "today" in lower_p:
            target_date = base_dt

    # Check days of week: "monday", "tuesday", etc.
    if not target_date:
        days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for dow_idx, dow_name in enumerate(days_of_week):
            if re.search(r'\b(?:this\s+|next\s+|on\s+)?' + dow_name + r'\b', lower_p):
                current_dow = base_dt.weekday()
                days_ahead = dow_idx - current_dow
                if "next " + dow_name in lower_p:
                    days_ahead += 7
                elif days_ahead <= 0:
                    days_ahead += 7
                target_date = base_dt + timedelta(days=days_ahead)
                break

    if not target_date:
        target_date = base_dt + timedelta(days=1)

    # 3. Time extraction
    target_hour = 10
    target_minute = 0

    time_12h = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', lower_p)
    if time_12h:
        h = int(time_12h.group(1))
        m = int(time_12h.group(2)) if time_12h.group(2) else 0
        ampm = time_12h.group(3)
        if ampm == "pm" and h < 12:
            h += 12
        elif ampm == "am" and h == 12:
            h = 0
        target_hour = h
        target_minute = m
    else:
        time_24h = re.search(r'\b(?:at\s+)?([01]?\d|2[0-3]):([0-5]\d)\b', lower_p)
        if time_24h:
            target_hour = int(time_24h.group(1))
            target_minute = int(time_24h.group(2))
        elif "noon" in lower_p:
            target_hour = 12
            target_minute = 0

    start_dt = target_date.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    
    # Duration calculation
    duration_mins = 30
    dur_match = re.search(r'\bfor\s+(\d+)\s*(hour|hr|minute|min)s?\b', lower_p)
    if dur_match:
        val = int(dur_match.group(1))
        unit = dur_match.group(2)
        if "hour" in unit or "hr" in unit:
            duration_mins = val * 60
        else:
            duration_mins = val
    
    end_dt = start_dt + timedelta(minutes=duration_mins)

    # 4. Title / Subject extraction
    title = "Team Sync Meeting"
    q_title = re.search(r'(?:titled|subject|called)\s*["\']([^"\']+)["\']', clean_p, re.IGNORECASE)
    if q_title:
        title = q_title.group(1).strip()
    else:
        topic_match = re.search(r'(?:regarding|about|to discuss|for)\s+([^,\.\n]+)', clean_p, re.IGNORECASE)
        if topic_match:
            candidate = topic_match.group(1).strip()
            candidate = re.sub(r'\b(at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|tomorrow|today|on\s+[a-z0-9]+|with\s+[a-z\s]+)\b.*$', '', candidate, flags=re.IGNORECASE).strip()
            if candidate and len(candidate) > 2:
                title = candidate
        else:
            candidate = clean_p
            for pfx in ["schedule a meeting", "schedule meeting", "book a meeting", "book meeting", "create a meeting", "create meeting", "book a sync", "schedule sync"]:
                if candidate.lower().startswith(pfx):
                    candidate = candidate[len(pfx):].strip()
            candidate = re.sub(r'\b(with\s+[A-Za-z\s]+|at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|tomorrow|today|on\s+[a-z0-9]+)\b', '', candidate, flags=re.IGNORECASE).strip(" :-")
            if candidate and len(candidate) > 2 and len(candidate) < 60:
                title = candidate

    # 5. Location
    location = "Microsoft Teams (Virtual)"
    if "conference room" in lower_p or "room" in lower_p:
        room_match = re.search(r'\b(conference room\s+[A-Za-z0-9]+|room\s+[A-Za-z0-9]+)\b', clean_p, re.IGNORECASE)
        if room_match:
            location = room_match.group(1).title()

    final_title = title.strip()
    if len(final_title) < 40 and not final_title.isupper():
        final_title = final_title.title()

    return {
        "title": final_title,
        "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
        "attendees": ", ".join(attendees_list) if attendees_list else (organizer_email or "team@novatech.com"),
        "location": location
    }

def handle_get_my_calendar(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM calendar_events
        WHERE (company_id = ? AND employee_id = ?)
           OR attendees LIKE ?
        ORDER BY start_time ASC
    """, (identity.company_id, identity.employee_id, f"%{identity.email}%"))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "status": "success",
        "employee": identity.name,
        "email": identity.email,
        "event_count": len(rows),
        "events": rows
    }

def parse_dt_str(val: str) -> Optional[datetime]:
    if not val:
        return None
    val = val.strip()
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None

def check_time_frame_conflict(
    conn,
    company_id: str,
    new_start_dt: datetime,
    new_end_dt: datetime,
    participants: List[str],
    exclude_event_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Checks if any existing meeting for the company conflicts with the requested time frame.
    An overlap occurs if: new_start < existing_end AND new_end > existing_start
    and at least one participant (organizer or attendee) is shared.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT event_id, employee_id, title, start_time, end_time, attendees, location
        FROM calendar_events
        WHERE company_id = ?
    """, (company_id,))
    rows = cursor.fetchall()
    
    clean_participants = {p.strip().lower() for p in participants if p and p.strip()}
    
    for row in rows:
        row_dict = dict(row)
        if exclude_event_id and row_dict["event_id"] == exclude_event_id:
            continue
            
        e_start = parse_dt_str(row_dict["start_time"])
        e_end = parse_dt_str(row_dict["end_time"])
        if not e_start:
            continue
        if not e_end:
            e_end = e_start + timedelta(minutes=30)
            
        # Overlap condition: startA < endB AND endA > startB
        if new_start_dt < e_end and new_end_dt > e_start:
            # Check shared participants
            existing_attendees = [a.strip().lower() for a in re.split(r'[,;]\s*', row_dict.get("attendees") or "")]
            existing_participants = set(existing_attendees)
            if row_dict.get("employee_id"):
                existing_participants.add(row_dict["employee_id"].strip().lower())
                
            shared = clean_participants.intersection(existing_participants)
            if shared:
                return {
                    "event_id": row_dict["event_id"],
                    "title": row_dict["title"],
                    "start_time": row_dict["start_time"],
                    "end_time": row_dict["end_time"],
                    "shared_participants": list(shared)
                }
    return None

def handle_schedule_meeting(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    title = params.get("title", "Sync Meeting")
    start_time = params.get("start_time", "2026-09-22 10:00")
    end_time = params.get("end_time", "2026-09-22 10:30")
    attendees = params.get("attendees", identity.email)
    location = params.get("location", "Microsoft Teams (Virtual)")
    description = params.get("description", "")

    # Parse and validate datetimes
    start_dt = parse_dt_str(start_time)
    if not start_dt:
        return {
            "status": "error",
            "error": "INVALID_DATETIME",
            "message": f"Invalid start_time format '{start_time}'. Expected YYYY-MM-DD HH:MM."
        }
    
    end_dt = parse_dt_str(end_time)
    if not end_dt:
        end_dt = start_dt + timedelta(minutes=30)
        end_time = end_dt.strftime("%Y-%m-%d %H:%M")

    if end_dt <= start_dt:
        return {
            "status": "error",
            "error": "INVALID_TIME_FRAME",
            "message": "Invalid meeting time frame: End time must be strictly after start time."
        }

    # Normalize formatted strings
    start_time_str = start_dt.strftime("%Y-%m-%d %H:%M")
    end_time_str = end_dt.strftime("%Y-%m-%d %H:%M")

    # Gather participants
    attendee_emails = [a.strip() for a in re.split(r'[,;]\s*', attendees) if a.strip()]
    participants = list(set([identity.employee_id, identity.email] + attendee_emails))

    conn = get_db_connection()

    # Time frame conflict check - prevent overriding already set time slots
    conflict = check_time_frame_conflict(
        conn=conn,
        company_id=identity.company_id,
        new_start_dt=start_dt,
        new_end_dt=end_dt,
        participants=participants
    )

    if conflict:
        conn.close()
        shared_str = ", ".join(conflict["shared_participants"])
        return {
            "status": "conflict",
            "error": "SCHEDULING_CONFLICT",
            "conflicting_event": conflict,
            "message": (
                f"Time frame conflict: Participant(s) [{shared_str}] already booked for "
                f"'{conflict['title']}' from {conflict['start_time']} to {conflict['end_time']}. "
                f"Existing meeting time frames cannot be overridden."
            )
        }

    event_id = f"EVT-{random.randint(300, 999)}"
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO calendar_events (event_id, company_id, employee_id, title, start_time, end_time, attendees, location, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (event_id, identity.company_id, identity.employee_id, title, start_time_str, end_time_str, attendees, location, description))
    conn.commit()
    conn.close()

    return {
        "status": "scheduled",
        "event_id": event_id,
        "organizer": identity.name,
        "title": title,
        "start_time": start_time_str,
        "end_time": end_time_str,
        "attendees": attendees,
        "location": location,
        "message": f"Meeting '{title}' scheduled successfully for {start_time_str} - {end_time_str}."
    }

def handle_delete_meeting(identity: IdentityContext, params: Dict[str, Any]) -> Dict[str, Any]:
    event_id = params.get("event_id", "").strip()
    if not event_id:
        return {"status": "error", "message": "Meeting event_id is required for deletion."}

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM calendar_events WHERE event_id = ? AND company_id = ?;
    """, (event_id, identity.company_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"status": "error", "message": f"Meeting with ID '{event_id}' was not found in your company calendar."}

    event = dict(row)
    # Authorization: Organizer, Attendee, or Manager/Admin
    is_organizer = (event["employee_id"] == identity.employee_id)
    is_attendee = (identity.email.lower() in event.get("attendees", "").lower())
    is_privileged = (
        identity.role in ["Manager", "Top Team", "Executive", "IT Specialist", "HR Executive"]
        or "admin.manage_employees" in identity.permissions
    )

    if not (is_organizer or is_attendee or is_privileged):
        conn.close()
        return {
            "status": "permission_denied",
            "message": f"Access Denied: You are not authorized to cancel meeting '{event['title']}'. Only the organizer ({event['employee_id']}) or meeting attendees can cancel this appointment."
        }

    cursor.execute("DELETE FROM calendar_events WHERE event_id = ? AND company_id = ?;", (event_id, identity.company_id))
    conn.commit()
    conn.close()

    return {
        "status": "deleted",
        "event_id": event_id,
        "title": event["title"],
        "start_time": event["start_time"],
        "end_time": event["end_time"],
        "message": f"Meeting '{event['title']}' ({event_id}) has been cancelled and removed from the calendar."
    }

def register():
    mcp_registry.register(
        name="get_my_calendar",
        description="View scheduled meetings, upcoming syncs, and check calendar availability for the authenticated employee. [Mock Service / SQLite]",
        category="Calendar",
        required_permission="calendar.read",
        parameters_schema={"type": "object", "properties": {}},
        handler=handle_get_my_calendar
    )

    mcp_registry.register(
        name="schedule_meeting",
        description="Schedule a new enterprise calendar meeting / Outlook appointment. [Mock Service / SQLite]",
        category="Calendar",
        required_permission="calendar.create",
        parameters_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title or subject of the meeting"},
                "start_time": {"type": "string", "description": "Start date and time (e.g. 2026-09-22 14:00)"},
                "end_time": {"type": "string", "description": "End date and time (e.g. 2026-09-22 15:00)"},
                "attendees": {"type": "string", "description": "Comma separated emails of attendees"},
                "location": {"type": "string", "description": "Meeting room or Teams link"}
            },
            "required": ["title", "start_time"]
        },
        handler=handle_schedule_meeting
    )

    mcp_registry.register(
        name="delete_meeting",
        description="Cancel and delete a scheduled meeting from the enterprise calendar / Outlook. [Mock Service / SQLite]",
        category="Calendar",
        required_permission="calendar.create",
        parameters_schema={
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "ID of the event to cancel, e.g. EVT-201"}
            },
            "required": ["event_id"]
        },
        handler=handle_delete_meeting
    )
