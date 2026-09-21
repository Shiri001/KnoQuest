import logging
import secrets
from typing import Optional, Set, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from .config import settings
from .database import get_db_connection

logger = logging.getLogger("knoquest.auth")

ph = PasswordHasher()
serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="knoquest-session-salt")
security_bearer = HTTPBearer(auto_error=False)

SESSION_COOKIE_NAME = "knoquest_session"

class IdentityContext(BaseModel):
    company_id: str
    employee_id: str
    name: str
    email: str
    role: str
    department: str
    designation: str
    status: str
    extension: Optional[str] = None
    location: Optional[str] = None
    permissions: List[str]
    session_id: Optional[str] = None

    @property
    def full_id(self) -> str:
        return f"{self.company_id}-{self.employee_id}"

def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return ph.hash(password)

def verify_password(password_hash: str, candidate_password: str) -> bool:
    """Verifies a password against an Argon2id hash."""
    if not password_hash or not candidate_password:
        return False
    try:
        return ph.verify(password_hash, candidate_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception as ex:
        logger.warning(f"Error during password verification: {ex}")
        return False

def create_session_token(company_id: str, employee_id: str) -> Tuple[str, str]:
    """
    Creates a new session in SQLite and returns (session_token, session_id).
    Token is signed with URLSafeTimedSerializer.
    """
    session_id = f"sess_{secrets.token_urlsafe(24)}"
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    expires_str = expires.strftime("%Y-%m-%d %H:%M:%S UTC")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (session_id, company_id, employee_id, created_at, expires_at, last_activity, is_revoked)
        VALUES (?, ?, ?, ?, ?, ?, 0);
    """, (session_id, company_id, employee_id, now_str, expires_str, now_str))
    conn.commit()
    conn.close()

    token_payload = {
        "sid": session_id,
        "cid": company_id,
        "eid": employee_id
    }
    signed_token = serializer.dumps(token_payload)
    return signed_token, session_id

def revoke_session(session_id: str):
    """Revokes a session in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET is_revoked = 1 WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def decode_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a session token signature and timestamp."""
    try:
        data = serializer.loads(token, max_age=settings.SESSION_MAX_AGE_SECONDS)
        return data
    except SignatureExpired:
        logger.info("Session token expired.")
        return None
    except BadSignature:
        logger.warning("Session token has invalid signature.")
        return None
    except Exception as ex:
        logger.warning(f"Failed to decode session token: {ex}")
        return None

def parse_employee_id(company_id_or_combined: str, employee_id: Optional[str] = None) -> Tuple[str, str]:
    """
    Parses either 'NOVA-EMP001' or ('NOVA', 'EMP001') or 'EMP001' into (company_id, employee_id).
    """
    comp = (company_id_or_combined or "").strip()
    emp = (employee_id or "").strip()

    if not emp:
        if "-" in comp:
            parts = comp.split("-", 1)
            return parts[0].upper(), parts[1].upper()
        else:
            return "NOVA", comp.upper()
    return comp.upper(), emp.upper()

def get_effective_permissions(company_id: str, employee_id: str, role: str) -> List[str]:
    """
    Calculates effective permissions:
    Effective = (Role Permissions + Direct Granted Overrides) - Direct Revoked Overrides
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Role base permissions
    cursor.execute("SELECT permission_key FROM role_permissions WHERE role_name = ?", (role,))
    role_perms: Set[str] = {row["permission_key"] for row in cursor.fetchall()}

    # 2. Direct individual employee overrides
    cursor.execute(
        "SELECT permission_key, is_granted FROM employee_permissions WHERE company_id = ? AND employee_id = ?",
        (company_id, employee_id)
    )
    overrides = cursor.fetchall()
    conn.close()

    direct_grants = {row["permission_key"] for row in overrides if row["is_granted"] == 1}
    direct_revocations = {row["permission_key"] for row in overrides if row["is_granted"] == 0}

    effective = (role_perms | direct_grants) - direct_revocations
    return sorted(list(effective))

def resolve_identity(company_id_or_combined: str, employee_id: Optional[str] = None, session_id: Optional[str] = None) -> Optional[IdentityContext]:
    """
    Looks up employee in SQLite, verifies active status, and loads effective permissions.
    """
    comp_id, emp_id = parse_employee_id(company_id_or_combined, employee_id)
    if not emp_id:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM employees WHERE company_id = ? AND employee_id = ?",
        (comp_id, emp_id)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        logger.warning(f"Employee {comp_id}-{emp_id} not found in database.")
        return None

    if row["status"] != "Active":
        logger.warning(f"Employee {comp_id}-{emp_id} is inactive (status: {row['status']}). Access denied.")
        return None

    permissions = get_effective_permissions(comp_id, emp_id, row["role"])

    return IdentityContext(
        company_id=row["company_id"],
        employee_id=row["employee_id"],
        name=row["name"],
        email=row["email"],
        role=row["role"],
        department=row["department"],
        designation=row["designation"],
        status=row["status"],
        extension=row["extension"],
        location=row["location"],
        permissions=permissions,
        session_id=session_id
    )

def check_permission(identity: IdentityContext, required_permission: str) -> bool:
    """
    Checks whether the identity holds the required permission key.
    """
    if not identity:
        return False
    return required_permission in identity.permissions

async def get_current_identity(
    request: Request,
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> IdentityContext:
    """
    FastAPI security dependency.
    Extracts, decrypts, and validates the authenticated session token from either:
    1. HttpOnly Cookie: 'knoquest_session'
    2. Authorization header: 'Bearer <token>'

    Strictly rejects request if unauthenticated, token expired, session revoked, or account locked.
    NEVER trusts request headers like 'X-Employee-ID'.
    """
    token: Optional[str] = None

    # Check HttpOnly cookie first
    token = request.cookies.get(SESSION_COOKIE_NAME)

    # If not in cookie, check Bearer header
    if not token and bearer_auth:
        token = bearer_auth.credentials

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. No active session token found."
        )

    payload = decode_session_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session token. Please log in again."
        )

    session_id = payload.get("sid")
    comp_id = payload.get("cid")
    emp_id = payload.get("eid")

    if not session_id or not comp_id or not emp_id:
        raise HTTPException(
            status_code=401,
            detail="Malformed session token."
        )

    # Validate session state in database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_revoked, expires_at FROM sessions WHERE session_id = ?", (session_id,))
    session_row = cursor.fetchone()

    if not session_row:
        conn.close()
        raise HTTPException(
            status_code=401,
            detail="Session not found or has been invalidated."
        )

    if session_row["is_revoked"] == 1:
        conn.close()
        raise HTTPException(
            status_code=401,
            detail="Session has been revoked. Please log in again."
        )

    # Check employee record & lockout
    cursor.execute("""
        SELECT status, locked_until, failed_login_attempts 
        FROM employees 
        WHERE company_id = ? AND employee_id = ?
    """, (comp_id, emp_id))
    emp_row = cursor.fetchone()

    if not emp_row:
        conn.close()
        raise HTTPException(status_code=401, detail="Employee record not found.")

    if emp_row["status"] != "Active":
        conn.close()
        raise HTTPException(status_code=403, detail="Employee account is deactivated.")

    # Check if locked
    locked_until = emp_row["locked_until"]
    if locked_until:
        try:
            lock_dt = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) < lock_dt:
                conn.close()
                raise HTTPException(
                    status_code=423,
                    detail=f"Account is temporarily locked until {locked_until}."
                )
        except ValueError:
            pass

    # Update session last_activity
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    cursor.execute("UPDATE sessions SET last_activity = ? WHERE session_id = ?", (now_str, session_id))
    conn.commit()
    conn.close()

    identity = resolve_identity(comp_id, emp_id, session_id=session_id)
    if not identity:
        raise HTTPException(status_code=401, detail="Could not resolve employee identity.")

    return identity

