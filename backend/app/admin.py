import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Response
from pydantic import BaseModel, Field

from .config import settings
from .database import get_db_connection
from .auth import (
    IdentityContext,
    get_current_identity,
    get_effective_permissions,
    resolve_identity,
    check_permission,
    parse_employee_id,
    hash_password,
    verify_password,
    create_session_token,
    revoke_session,
    SESSION_COOKIE_NAME
)

logger = logging.getLogger("knoquest.admin")

admin_router = APIRouter(prefix="/api/admin", tags=["Admin / Top Team"])
auth_router = APIRouter(prefix="/api/auth", tags=["Authentication & Identity"])

# --- Request / Response Schemas ---

class EmployeeSummary(BaseModel):
    company_id: str
    employee_id: str
    full_id: str
    name: str
    email: str
    role: str
    department: str
    designation: str
    status: str
    extension: Optional[str] = None
    location: Optional[str] = None
    effective_permissions: List[str]

class EmployeeDetail(EmployeeSummary):
    role_permissions: List[str]
    overrides: List[Dict[str, Any]]  # [{"permission_key": str, "is_granted": bool}]

class CreateEmployeeRequest(BaseModel):
    company_id: str = Field(default="NOVA")
    employee_id: str = Field(..., description="e.g. EMP007")
    name: str
    email: str
    role: str = Field(default="Employee", description="Employee, Manager, HR, IT, Admin")
    department: str
    designation: str
    status: str = Field(default="Active")
    extension: Optional[str] = None
    location: Optional[str] = None
    password: Optional[str] = Field(default=None, description="Initial corporate password. Defaults to system default.")

class UpdateEmployeeRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    status: Optional[str] = None
    extension: Optional[str] = None
    location: Optional[str] = None
    password: Optional[str] = Field(default=None, description="New corporate password.")

class PermissionOverrideRequest(BaseModel):
    permission_key: str
    is_granted: bool = Field(..., description="True to explicitly grant, False to explicitly revoke")

ALL_AVAILABLE_PERMISSIONS = [
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

def require_admin(identity: IdentityContext = Depends(get_current_identity)) -> IdentityContext:
    """Security guard to restrict admin endpoints to Top Team / Admin role."""
    if not check_permission(identity, "admin.manage_employees"):
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied: Your identity ({identity.name} - {identity.role}) lacks 'admin.manage_employees' permission."
        )
    return identity

# --- Auth Endpoints for Frontend Switcher & Identity ---

class LoginRequest(BaseModel):
    company_id: str = Field(default="NOVA", description="Company Code, e.g. NOVA")
    identifier: str = Field(..., description="Employee ID (e.g. NOVA-EMP001 or EMP001) or Corporate Email")
    password: str = Field(..., description="Corporate account password")

class LoginResponse(BaseModel):
    employee: EmployeeSummary
    session_token: str
    must_change_password: bool = False

@auth_router.post("/login", response_model=LoginResponse)
async def login_endpoint(payload: LoginRequest, response: Response):
    """
    Authenticates employee using Company ID, Identifier (Employee ID or Email), and Password.
    Enforces account lockout (15 mins after 5 failed attempts).
    Issues HttpOnly session cookie and signed session token.
    Never returns passwords or password hashes.
    """
    comp_input = (payload.company_id or "NOVA").strip().upper()
    ident_input = payload.identifier.strip()
    password_input = payload.password

    if not ident_input or not password_input:
        raise HTTPException(status_code=400, detail="Company ID, Identifier, and Password are required.")

    # Parse potential combined identifier like NOVA-EMP001
    parsed_comp, parsed_emp = parse_employee_id(ident_input, comp_input if ident_input == comp_input else None)
    target_comp = parsed_comp or comp_input

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM employees 
        WHERE (company_id = ? AND employee_id = ?)
           OR (company_id = ? AND LOWER(email) = LOWER(?))
    """, (target_comp, parsed_emp, target_comp, ident_input))
    row = cursor.fetchone()

    if not row:
        conn.close()
        # Generic error message to prevent user enumeration
        raise HTTPException(
            status_code=401,
            detail="Invalid Company ID, Employee ID/Email, or password."
        )

    # 1. Check account lockout
    locked_until = row["locked_until"]
    if locked_until:
        try:
            lock_dt = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) < lock_dt:
                conn.close()
                raise HTTPException(
                    status_code=423,
                    detail=f"Account is temporarily locked due to repeated failed login attempts until {locked_until}."
                )
            else:
                # Lock has expired; clear lockout
                cursor.execute("""
                    UPDATE employees 
                    SET failed_login_attempts = 0, locked_until = NULL 
                    WHERE company_id = ? AND employee_id = ?
                """, (row["company_id"], row["employee_id"]))
                conn.commit()
        except ValueError:
            pass

    # 2. Check active status
    if row["status"] != "Active":
        conn.close()
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied: Account '{row['company_id']}-{row['employee_id']}' is deactivated. Please contact your IT / HR administrator."
        )

    # 3. Verify Argon2 password hash
    stored_hash = row["password_hash"]
    if not stored_hash or not verify_password(stored_hash, password_input):
        current_attempts = (row["failed_login_attempts"] or 0) + 1
        if current_attempts >= 5:
            lock_time = datetime.now(timezone.utc) + timedelta(minutes=15)
            lock_str = lock_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            cursor.execute("""
                UPDATE employees 
                SET failed_login_attempts = ?, locked_until = ? 
                WHERE company_id = ? AND employee_id = ?
            """, (current_attempts, lock_str, row["company_id"], row["employee_id"]))
            conn.commit()
            conn.close()
            raise HTTPException(
                status_code=423,
                detail="Too many failed login attempts. Your account has been temporarily locked for 15 minutes."
            )
        else:
            cursor.execute("""
                UPDATE employees 
                SET failed_login_attempts = ? 
                WHERE company_id = ? AND employee_id = ?
            """, (current_attempts, row["company_id"], row["employee_id"]))
            conn.commit()
            conn.close()
            remaining = 5 - current_attempts
            raise HTTPException(
                status_code=401,
                detail=f"Invalid credentials. {remaining} attempt(s) remaining before account lockout."
            )

    # 4. Successful authentication - reset lockout & record last login
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    cursor.execute("""
        UPDATE employees 
        SET failed_login_attempts = 0, locked_until = NULL, last_login_at = ? 
        WHERE company_id = ? AND employee_id = ?
    """, (now_utc, row["company_id"], row["employee_id"]))
    conn.commit()
    conn.close()

    # 5. Issue session token and store in sessions table
    session_token, session_id = create_session_token(row["company_id"], row["employee_id"])

    # 6. Set HttpOnly session cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False
    )

    identity = resolve_identity(row["company_id"], row["employee_id"], session_id=session_id)
    if not identity:
        raise HTTPException(status_code=500, detail="Failed to load employee profile.")

    emp_summary = EmployeeSummary(
        company_id=identity.company_id,
        employee_id=identity.employee_id,
        full_id=identity.full_id,
        name=identity.name,
        email=identity.email,
        role=identity.role,
        department=identity.department,
        designation=identity.designation,
        status=identity.status,
        extension=identity.extension,
        location=identity.location,
        effective_permissions=identity.permissions
    )

    return LoginResponse(
        employee=emp_summary,
        session_token=session_token,
        must_change_password=bool(row["must_change_password"])
    )

@auth_router.post("/logout")
async def logout_endpoint(response: Response, identity: IdentityContext = Depends(get_current_identity)):
    """Terminates session, revokes session record, and clears the HttpOnly session cookie."""
    if identity.session_id:
        revoke_session(identity.session_id)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return {"status": "success", "message": f"Successfully logged out {identity.full_id}."}

@auth_router.get("/me", response_model=EmployeeSummary)
async def get_current_user_profile(identity: IdentityContext = Depends(get_current_identity)):
    """Returns the authenticated employee's profile and effective permissions based on verified session."""
    return EmployeeSummary(
        company_id=identity.company_id,
        employee_id=identity.employee_id,
        full_id=identity.full_id,
        name=identity.name,
        email=identity.email,
        role=identity.role,
        department=identity.department,
        designation=identity.designation,
        status=identity.status,
        extension=identity.extension,
        location=identity.location,
        effective_permissions=identity.permissions
    )

# --- Top Team / Admin Endpoints ---

@admin_router.get("/permissions/catalog")
async def get_permissions_catalog(admin: IdentityContext = Depends(require_admin)):
    """Returns all available enterprise permissions and roles for admin assignment."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role_name, description FROM roles")
    roles = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "permissions": ALL_AVAILABLE_PERMISSIONS,
        "roles": roles
    }

@admin_router.get("/employees", response_model=List[EmployeeSummary])
async def list_employees_admin(admin: IdentityContext = Depends(require_admin)):
    """Lists all employees along with their calculated effective permissions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees ORDER BY employee_id ASC")
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        perms = get_effective_permissions(r["company_id"], r["employee_id"], r["role"])
        result.append(EmployeeSummary(
            company_id=r["company_id"],
            employee_id=r["employee_id"],
            full_id=f"{r['company_id']}-{r['employee_id']}",
            name=r["name"],
            email=r["email"],
            role=r["role"],
            department=r["department"],
            designation=r["designation"],
            status=r["status"],
            extension=r["extension"],
            location=r["location"],
            effective_permissions=perms
        ))
    return result

@admin_router.get("/employees/{company_id}/{employee_id}", response_model=EmployeeDetail)
async def get_employee_detail_admin(
    company_id: str = Path(...),
    employee_id: str = Path(...),
    admin: IdentityContext = Depends(require_admin)
):
    """Fetches employee record with role permissions and individual overrides."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE company_id = ? AND employee_id = ?", (company_id.upper(), employee_id.upper()))
    emp = cursor.fetchone()

    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Employee {company_id}-{employee_id} not found")

    cursor.execute("SELECT permission_key FROM role_permissions WHERE role_name = ?", (emp["role"],))
    role_perms = [r["permission_key"] for r in cursor.fetchall()]

    cursor.execute("SELECT permission_key, is_granted FROM employee_permissions WHERE company_id = ? AND employee_id = ?", (company_id.upper(), employee_id.upper()))
    overrides = [{"permission_key": r["permission_key"], "is_granted": bool(r["is_granted"])} for r in cursor.fetchall()]

    conn.close()

    effective = get_effective_permissions(emp["company_id"], emp["employee_id"], emp["role"])

    return EmployeeDetail(
        company_id=emp["company_id"],
        employee_id=emp["employee_id"],
        full_id=f"{emp['company_id']}-{emp['employee_id']}",
        name=emp["name"],
        email=emp["email"],
        role=emp["role"],
        department=emp["department"],
        designation=emp["designation"],
        status=emp["status"],
        extension=emp["extension"],
        location=emp["location"],
        effective_permissions=effective,
        role_permissions=role_perms,
        overrides=overrides
    )

@admin_router.post("/employees", response_model=EmployeeSummary)
async def create_employee_admin(
    payload: CreateEmployeeRequest,
    admin: IdentityContext = Depends(require_admin)
):
    """Creates a new employee in the company database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    comp = payload.company_id.upper()
    emp = payload.employee_id.upper()

    cursor.execute("SELECT * FROM employees WHERE company_id = ? AND employee_id = ?", (comp, emp))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail=f"Employee {comp}-{emp} already exists.")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    plain_pw = payload.password or settings.DEV_DEFAULT_PASSWORD
    hashed_pw = hash_password(plain_pw)
    cursor.execute("""
    INSERT INTO employees (company_id, employee_id, name, email, role, department, designation, status, extension, location, password_hash, password_changed_at, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (comp, emp, payload.name, payload.email, payload.role, payload.department, payload.designation, payload.status, payload.extension, payload.location, hashed_pw, now, now))

    # Initialize standard HR record
    cursor.execute("""
    INSERT INTO hr_records (company_id, employee_id, leave_balance_paid, leave_balance_sick, salary_band, compensation_notes, performance_rating)
    VALUES (?, ?, 18, 10, 'Band 3 ($90,000 - $110,000)', 'Standard initial compensation package.', 'Meets Expectations');
    """, (comp, emp))

    conn.commit()
    conn.close()

    perms = get_effective_permissions(comp, emp, payload.role)
    return EmployeeSummary(
        company_id=comp,
        employee_id=emp,
        full_id=f"{comp}-{emp}",
        name=payload.name,
        email=payload.email,
        role=payload.role,
        department=payload.department,
        designation=payload.designation,
        status=payload.status,
        extension=payload.extension,
        location=payload.location,
        effective_permissions=perms
    )

@admin_router.put("/employees/{company_id}/{employee_id}", response_model=EmployeeSummary)
async def update_employee_admin(
    company_id: str,
    employee_id: str,
    payload: UpdateEmployeeRequest,
    admin: IdentityContext = Depends(require_admin)
):
    """Updates employee role, department, designation, status, or password."""
    conn = get_db_connection()
    cursor = conn.cursor()
    comp = company_id.upper()
    emp = employee_id.upper()

    cursor.execute("SELECT * FROM employees WHERE company_id = ? AND employee_id = ?", (comp, emp))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Employee {comp}-{emp} not found.")

    updates = []
    params = []
    if payload.name is not None:
        updates.append("name = ?")
        params.append(payload.name)
    if payload.email is not None:
        updates.append("email = ?")
        params.append(payload.email)
    if payload.role is not None:
        updates.append("role = ?")
        params.append(payload.role)
    if payload.department is not None:
        updates.append("department = ?")
        params.append(payload.department)
    if payload.designation is not None:
        updates.append("designation = ?")
        params.append(payload.designation)
    if payload.status is not None:
        updates.append("status = ?")
        params.append(payload.status)
    if payload.extension is not None:
        updates.append("extension = ?")
        params.append(payload.extension)
    if payload.location is not None:
        updates.append("location = ?")
        params.append(payload.location)
    if payload.password is not None and payload.password.strip():
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        updates.append("password_hash = ?")
        params.append(hash_password(payload.password.strip()))
        updates.append("password_changed_at = ?")
        params.append(now_utc)

    if updates:
        params.extend([comp, emp])
        sql = f"UPDATE employees SET {', '.join(updates)} WHERE company_id = ? AND employee_id = ?"
        cursor.execute(sql, params)
        conn.commit()

    cursor.execute("SELECT * FROM employees WHERE company_id = ? AND employee_id = ?", (comp, emp))
    updated = cursor.fetchone()
    conn.close()

    perms = get_effective_permissions(comp, emp, updated["role"])
    return EmployeeSummary(
        company_id=comp,
        employee_id=emp,
        full_id=f"{comp}-{emp}",
        name=updated["name"],
        email=updated["email"],
        role=updated["role"],
        department=updated["department"],
        designation=updated["designation"],
        status=updated["status"],
        extension=updated["extension"],
        location=updated["location"],
        effective_permissions=perms
    )

@admin_router.post("/employees/{company_id}/{employee_id}/permissions")
async def override_employee_permission_admin(
    company_id: str,
    employee_id: str,
    payload: PermissionOverrideRequest,
    admin: IdentityContext = Depends(require_admin)
):
    """Grants or revokes a specific individual permission override."""
    conn = get_db_connection()
    cursor = conn.cursor()
    comp = company_id.upper()
    emp = employee_id.upper()

    cursor.execute("SELECT * FROM employees WHERE company_id = ? AND employee_id = ?", (comp, emp))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Employee {comp}-{emp} not found.")

    cursor.execute("""
    INSERT INTO employee_permissions (company_id, employee_id, permission_key, is_granted)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(company_id, employee_id, permission_key)
    DO UPDATE SET is_granted = excluded.is_granted;
    """, (comp, emp, payload.permission_key, 1 if payload.is_granted else 0))

    conn.commit()
    conn.close()

    updated_perms = get_effective_permissions(comp, emp, admin.role)
    return {
        "status": "success",
        "message": f"Permission '{payload.permission_key}' override set to {'Granted' if payload.is_granted else 'Revoked'} for {comp}-{emp}.",
        "effective_permissions": updated_perms
    }

@admin_router.delete("/employees/{company_id}/{employee_id}/permissions/{permission_key}")
async def remove_permission_override_admin(
    company_id: str,
    employee_id: str,
    permission_key: str,
    admin: IdentityContext = Depends(require_admin)
):
    """Deletes an override, reverting the employee's permission back to their role default."""
    conn = get_db_connection()
    cursor = conn.cursor()
    comp = company_id.upper()
    emp = employee_id.upper()

    cursor.execute(
        "DELETE FROM employee_permissions WHERE company_id = ? AND employee_id = ? AND permission_key = ?",
        (comp, emp, permission_key)
    )
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": f"Override for '{permission_key}' removed. Reverted to role default."
    }
