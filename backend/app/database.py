import sqlite3
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from argon2 import PasswordHasher
from .config import settings

logger = logging.getLogger("knoquest.database")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "knoquest.db")

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates tables if they do not exist and seeds initial data."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Employees table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        company_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        designation TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Active',
        extension TEXT,
        location TEXT,
        password_hash TEXT,
        password_changed_at TEXT,
        last_login_at TEXT,
        failed_login_attempts INTEGER NOT NULL DEFAULT 0,
        locked_until TEXT,
        must_change_password INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        PRIMARY KEY (company_id, employee_id)
    );
    """)

    # Check and migrate existing employees table if columns are missing
    cursor.execute("PRAGMA table_info(employees);")
    existing_cols = {row["name"] for row in cursor.fetchall()}
    if "password_hash" not in existing_cols:
        cursor.execute("ALTER TABLE employees ADD COLUMN password_hash TEXT;")
    if "password_changed_at" not in existing_cols:
        cursor.execute("ALTER TABLE employees ADD COLUMN password_changed_at TEXT;")
    if "last_login_at" not in existing_cols:
        cursor.execute("ALTER TABLE employees ADD COLUMN last_login_at TEXT;")
    if "failed_login_attempts" not in existing_cols:
        cursor.execute("ALTER TABLE employees ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0;")
    if "locked_until" not in existing_cols:
        cursor.execute("ALTER TABLE employees ADD COLUMN locked_until TEXT;")
    if "must_change_password" not in existing_cols:
        cursor.execute("ALTER TABLE employees ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0;")

    # 1b. Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        company_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        last_activity TEXT NOT NULL,
        is_revoked INTEGER NOT NULL DEFAULT 0
    );
    """)

    # 2. Roles & Permissions tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        role_name TEXT PRIMARY KEY,
        description TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS role_permissions (
        role_name TEXT NOT NULL,
        permission_key TEXT NOT NULL,
        PRIMARY KEY (role_name, permission_key)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_permissions (
        company_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        permission_key TEXT NOT NULL,
        is_granted INTEGER NOT NULL,
        PRIMARY KEY (company_id, employee_id, permission_key)
    );
    """)

    # 3. IT Tickets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS it_tickets (
        ticket_id TEXT PRIMARY KEY,
        company_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        department TEXT NOT NULL,
        issue TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'Medium',
        status TEXT NOT NULL DEFAULT 'Open',
        assigned_to TEXT NOT NULL DEFAULT 'IT Tier-1 Helpdesk',
        created_at TEXT NOT NULL
    );
    """)

    # 4. Calendar Events table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calendar_events (
        event_id TEXT PRIMARY KEY,
        company_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        title TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        attendees TEXT NOT NULL,
        location TEXT,
        description TEXT
    );
    """)

    # 5. Communications table (Email / Teams)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS communications (
        comm_id TEXT PRIMARY KEY,
        comm_type TEXT NOT NULL DEFAULT 'email',
        company_id TEXT NOT NULL,
        sender_id TEXT NOT NULL,
        recipient TEXT NOT NULL,
        subject TEXT,
        body TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'sent',
        timestamp TEXT NOT NULL
    );
    """)

    # 6. HR Records table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hr_records (
        company_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        leave_balance_paid INTEGER NOT NULL DEFAULT 18,
        leave_balance_sick INTEGER NOT NULL DEFAULT 10,
        salary_band TEXT NOT NULL,
        compensation_notes TEXT,
        performance_rating TEXT NOT NULL DEFAULT 'Exceeds Expectations',
        PRIMARY KEY (company_id, employee_id)
    );
    """)

    conn.commit()

    # Seed default data if empty
    _seed_roles_and_permissions(cursor)
    _seed_employees(cursor)
    _seed_enterprise_data(cursor)

    conn.commit()
    conn.close()
    logger.info(f"KnoQuest SQLite database initialized successfully at {DB_PATH}")

def _seed_roles_and_permissions(cursor: sqlite3.Cursor):
    roles = [
        ("Employee", "Standard enterprise employee with access to personal tools and knowledge"),
        ("Manager", "Team leader with team management, calendar, and approvals access"),
        ("HR", "People Operations with access to HR records, leave balances, and company-wide policies"),
        ("IT", "IT Specialist with elevated access to manage, view, and resolve all company tickets"),
        ("Admin", "Executive Top Team with full administrative rights over company registry and permissions")
    ]
    cursor.executemany("INSERT OR IGNORE INTO roles (role_name, description) VALUES (?, ?);", roles)

    # Standard permissions mapping
    role_perms = {
        "Employee": [
            "knowledge.read",
            "documents.read",
            "employee_directory.read",
            "employee_profile.read",
            "hr.self",
            "it.create_ticket",
            "it.view_own_ticket",
            "calendar.read",
            "calendar.create",
            "communication.read",
            "communication.draft",
            "communication.send"
        ],
        "Manager": [
            "knowledge.read",
            "documents.read",
            "employee_directory.read",
            "employee_profile.read",
            "hr.self",
            "hr.team",
            "it.create_ticket",
            "it.view_own_ticket",
            "calendar.read",
            "calendar.create",
            "communication.read",
            "communication.draft",
            "communication.send"
        ],
        "HR": [
            "knowledge.read",
            "documents.read",
            "employee_directory.read",
            "employee_profile.read",
            "hr.self",
            "hr.team",
            "hr.all",
            "it.create_ticket",
            "it.view_own_ticket",
            "calendar.read",
            "calendar.create",
            "communication.read",
            "communication.draft",
            "communication.send"
        ],
        "IT": [
            "knowledge.read",
            "documents.read",
            "employee_directory.read",
            "employee_profile.read",
            "hr.self",
            "it.create_ticket",
            "it.view_own_ticket",
            "it.view_all_tickets",
            "it.update_ticket",
            "calendar.read",
            "calendar.create",
            "communication.read",
            "communication.draft",
            "communication.send"
        ],
        "Admin": [
            "knowledge.read",
            "documents.read",
            "employee_directory.read",
            "employee_profile.read",
            "hr.self",
            "hr.team",
            "hr.all",
            "it.create_ticket",
            "it.view_own_ticket",
            "it.view_all_tickets",
            "it.update_ticket",
            "calendar.read",
            "calendar.create",
            "communication.read",
            "communication.draft",
            "communication.send",
            "admin.manage_employees"
        ]
    }

    for role, perms in role_perms.items():
        for perm in perms:
            cursor.execute("INSERT OR IGNORE INTO role_permissions (role_name, permission_key) VALUES (?, ?);", (role, perm))

def _seed_employees(cursor: sqlite3.Cursor):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    ph = PasswordHasher()
    default_hash = ph.hash(settings.DEV_DEFAULT_PASSWORD)

    employees = [
        ("NOVA", "EMP001", "Rahul Sharma", "rahul.sharma@novatech.com", "Employee", "Engineering", "Software Engineer", "Active", "4105", "HQ - Floor 4", default_hash, now, now),
        ("NOVA", "EMP002", "Elena Rostova", "elena.rostova@novatech.com", "Manager", "Finance", "Senior Travel & Expense Coordinator", "Active", "4350", "HQ - Floor 3", default_hash, now, now),
        ("NOVA", "EMP003", "Sarah Jenkins", "sarah.jenkins@novatech.com", "HR", "Human Resources", "VP of People & HR", "Active", "4101", "HQ - Floor 4", default_hash, now, now),
        ("NOVA", "EMP004", "Marcus Vance", "marcus.vance@novatech.com", "IT", "IT Operations", "Lead IT Infrastructure Engineer", "Active", "4220", "HQ - Floor 2", default_hash, now, now),
        ("NOVA", "EMP005", "David Kumar", "david.kumar@novatech.com", "Admin", "Information Security", "Chief Information Security Officer (CISO)", "Active", "4444", "HQ - Floor 5", default_hash, now, now),
        ("NOVA", "EMP006", "Alex Chen", "alex.chen@novatech.com", "Manager", "Facilities", "Workplace Operations Manager", "Active", "4115", "HQ - Floor 1", default_hash, now, now),
    ]

    for emp in employees:
        cursor.execute("""
        INSERT OR IGNORE INTO employees (company_id, employee_id, name, email, role, department, designation, status, extension, location, password_hash, password_changed_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, emp)

    # Ensure any existing employees without a password hash get the default hash populated
    cursor.execute("""
    UPDATE employees 
    SET password_hash = ?, password_changed_at = COALESCE(password_changed_at, ?) 
    WHERE password_hash IS NULL OR password_hash = '';
    """, (default_hash, now))

def _seed_enterprise_data(cursor: sqlite3.Cursor):
    # Seed HR records
    hr_data = [
        ("NOVA", "EMP001", 16, 8, "Band 4 ($120,000 - $140,000)", "Eligible for mid-year promotion review. Next stock vesting in Q3.", "Exceeds Expectations"),
        ("NOVA", "EMP002", 22, 10, "Band 5 ($145,000 - $165,000)", "Oversees international travel budget reconciliations and corporate card compliance.", "Outstanding"),
        ("NOVA", "EMP003", 25, 12, "Executive ($190,000 - $220,000)", "Executive leadership compensation package with equity grants.", "Exceptional"),
        ("NOVA", "EMP004", 19, 9, "Band 5 ($140,000 - $160,000)", "Primary on-call for Azure cloud infra, VPN gateways, and Zero-Trust rollout.", "Exceeds Expectations"),
        ("NOVA", "EMP005", 24, 11, "Executive ($210,000 - $240,000)", "Executive cybersecurity compensation package with security audit incentives.", "Exceptional"),
        ("NOVA", "EMP006", 20, 8, "Band 4 ($115,000 - $135,000)", "Manages facility vendors, office badges, and hybrid workplace hot-desking.", "Meets Expectations")
    ]
    for hr in hr_data:
        cursor.execute("""
        INSERT OR IGNORE INTO hr_records (company_id, employee_id, leave_balance_paid, leave_balance_sick, salary_band, compensation_notes, performance_rating)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, hr)

    # Seed some sample IT tickets
    tickets = [
        ("IT-1001", "NOVA", "EMP001", "Rahul Sharma", "Engineering", "Request dual 4K external monitors for remote setup", "Medium", "Resolved", "IT Tier-1 Helpdesk", "2026-09-10 10:30:00 UTC"),
        ("IT-1002", "NOVA", "EMP001", "Rahul Sharma", "Engineering", "VPN disconnects intermittently on macOS Sequoia", "High", "In Progress", "Marcus Vance", "2026-09-18 14:15:00 UTC"),
        ("IT-1003", "NOVA", "EMP002", "Elena Rostova", "Finance", "Concur travel booking system API integration timeout", "High", "Open", "IT Tier-1 Helpdesk", "2026-09-19 09:00:00 UTC"),
        ("IT-1004", "NOVA", "EMP006", "Alex Chen", "Facilities", "Replace access badge scanner on HQ Floor 1 lobby", "Low", "Open", "IT Tier-1 Helpdesk", "2026-09-20 08:30:00 UTC"),
    ]
    for t in tickets:
        cursor.execute("""
        INSERT OR IGNORE INTO it_tickets (ticket_id, company_id, employee_id, user_name, department, issue, priority, status, assigned_to, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, t)

    # Seed some sample calendar events
    events = [
        ("EVT-201", "NOVA", "EMP001", "Engineering Architecture Sync", "2026-09-21 10:00", "2026-09-21 11:00", "rahul.sharma@novatech.com, marcus.vance@novatech.com", "Teams Room - Alpha", "Reviewing Azure AI Search RAG pipeline and hybrid vector indexes."),
        ("EVT-202", "NOVA", "EMP001", "1-on-1 with Tech Lead", "2026-09-21 14:00", "2026-09-21 14:30", "rahul.sharma@novatech.com", "HQ - Floor 4 Conf B", "Bi-weekly sprint check-in and career development."),
        ("EVT-203", "NOVA", "EMP002", "Monthly Expense & Travel Audit", "2026-09-22 11:00", "2026-09-22 12:30", "elena.rostova@novatech.com, sarah.jenkins@novatech.com", "Finance Boardroom", "Quarterly corporate card audit and policy review."),
        ("EVT-204", "NOVA", "EMP004", "Security Incident Response Drill", "2026-09-23 15:00", "2026-09-23 16:30", "marcus.vance@novatech.com, david.kumar@novatech.com", "Virtual War Room", "Annual tabletop drill for Zero-Trust and multi-region failover.")
    ]
    for ev in events:
        cursor.execute("""
        INSERT OR IGNORE INTO calendar_events (event_id, company_id, employee_id, title, start_time, end_time, attendees, location, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ev)

    # Seed sample communications (emails / Teams)
    comms = [
        ("COMM-301", "email", "NOVA", "EMP003", "all-staff@novatech.com", "NovaTech Q3 Hybrid Work & Benefits Update", "Hi team, please find attached the revised WFH policy. Core collaboration hours remain 10 AM - 4 PM.", "sent", "2026-09-15 09:00:00 UTC"),
        ("COMM-302", "email", "NOVA", "EMP004", "rahul.sharma@novatech.com", "VPN Gateway Certificate Rotation Notice", "Hi Rahul, we have updated the root CA on the GlobalProtect VPN. Please restart your client if you experience drops.", "sent", "2026-09-18 16:20:00 UTC"),
        ("COMM-303", "teams", "NOVA", "EMP002", "rahul.sharma@novatech.com", "Expense Report EXP-889 approved", "Your flight and hotel claim for Azure TechDays has been approved for reimbursement.", "sent", "2026-09-19 11:45:00 UTC")
    ]
    for c in comms:
        cursor.execute("""
        INSERT OR IGNORE INTO communications (comm_id, comm_type, company_id, sender_id, recipient, subject, body, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, c)

# Initialize on module load
init_db()
