import os
import logging
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from .config import settings
from .knowledge import knowledge_base
from .tools.ticket_tool import create_it_ticket, list_it_tickets
from .tools.directory_tool import search_employee_directory
from .models.schemas import ChatRequest, ChatResponse, HealthResponse, TicketRequest, TicketResponse
from .chat import conversation_manager
from .agent import foundry_agent
from .upload import upload_router
from .speech import speech_router
from .admin import admin_router, auth_router
from .auth import get_current_identity, check_permission, IdentityContext
from .mcp.registry import mcp_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("knoquest.main")

app = FastAPI(
    title="KnoQuest — Enterprise Knowledge & Employee Agent API",
    description="Backend API powering enterprise knowledge retrieval, RAG, speech, company employee access management, and MCP tools.",
    version="2.0.0"
)

# Enable CORS for React frontend (supports local dev and cloud deployments)
cors_origins = settings.cors_origin_list
if "*" in cors_origins or not cors_origins or settings.CORS_ORIGINS.strip() == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(upload_router)
app.include_router(speech_router)
app.include_router(auth_router)
app.include_router(admin_router)

@app.get("/", tags=["General"])
async def root():
    return {
        "service": "KnoQuest Enterprise Knowledge Agent",
        "tagline": "Ask. Retrieve. Know. With Enterprise Role-Based Access Control.",
        "version": "2.0.0",
        "docs_url": "/docs"
    }

@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Returns system status, active mode, and loaded enterprise policy count."""
    return HealthResponse(
        status="ok",
        service="KnoQuest — Enterprise Knowledge Agent",
        version="2.0.0",
        mode="azure_foundry" if foundry_agent.is_azure_ready else "local_sandbox",
        azure_configured=foundry_agent.is_azure_ready,
        enterprise_docs_loaded=len(knowledge_base.chunks)
    )

@app.get("/api/mcp/tools", tags=["MCP Tools"])
async def list_registered_mcp_tools(identity: IdentityContext = Depends(get_current_identity)):
    """Returns all enterprise MCP connectors and required permission keys."""
    tools = mcp_registry.list_all_tools()
    return {
        "total_tools": len(tools),
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "required_permission": t.required_permission
            }
            for t in tools
        ]
    }

@app.post("/api/tools/ticket", response_model=TicketResponse, tags=["Tools"])
@app.post("/api/tools/tickets", response_model=TicketResponse, tags=["Tools"])
async def create_ticket_endpoint(
    request: TicketRequest,
    identity: IdentityContext = Depends(get_current_identity)
):
    """Explicit endpoint for IT ticket creation."""
    if not check_permission(identity, "it.create_ticket"):
        raise HTTPException(status_code=403, detail="Permission denied: 'it.create_ticket' required.")
    res = create_it_ticket(
        issue=request.issue,
        priority=request.priority or "Medium",
        user_name=identity.name,
        department=identity.department,
        company_id=identity.company_id,
        employee_id=identity.employee_id
    )
    return TicketResponse(**res)

@app.get("/api/tools/tickets", tags=["Tools"])
async def list_tickets_endpoint(identity: IdentityContext = Depends(get_current_identity)):
    """List IT tickets scoped by permission (all tickets if it.view_all_tickets, else own tickets)."""
    if check_permission(identity, "it.view_all_tickets"):
        return {"tickets": list_it_tickets()}
    elif check_permission(identity, "it.view_own_ticket"):
        return {"tickets": list_it_tickets(identity.company_id, identity.employee_id)}
    else:
        raise HTTPException(status_code=403, detail="Permission denied: IT ticket viewing permission required.")

@app.patch("/api/tools/tickets/{ticket_id}", tags=["Tools"])
async def update_ticket_endpoint(
    ticket_id: str,
    payload: dict,
    identity: IdentityContext = Depends(get_current_identity)
):
    """Updates IT ticket status or assignment. Requires 'it.update_ticket' permission (IT Specialist or Admin)."""
    if not check_permission(identity, "it.update_ticket"):
        raise HTTPException(status_code=403, detail="Permission denied: 'it.update_ticket' required.")

    from .mcp.tools.it_tools import handle_update_it_ticket
    params = {"ticket_id": ticket_id, **payload}
    res = handle_update_it_ticket(identity, params)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res["message"])
    return res

@app.get("/api/tools/directory", tags=["Tools"])
async def search_directory_endpoint(
    q: str = "",
    identity: IdentityContext = Depends(get_current_identity)
):
    """Search NovaTech employee directory."""
    if not check_permission(identity, "employee_directory.read"):
        raise HTTPException(status_code=403, detail="Permission denied: 'employee_directory.read' required.")
    return {"employees": search_employee_directory(q)}

@app.get("/api/tools/communications", tags=["Tools"])
async def list_communications_endpoint(
    folder: Optional[str] = None,
    identity: IdentityContext = Depends(get_current_identity)
):
    """Lists corporate emails and messages (Inbox, Drafts, Sent) for the authenticated employee."""
    if not check_permission(identity, "communication.read"):
        raise HTTPException(status_code=403, detail="Permission denied: 'communication.read' required.")

    from .database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    if folder == "drafts":
        cursor.execute("SELECT * FROM communications WHERE sender_id = ? AND status = 'draft' ORDER BY timestamp DESC", (identity.employee_id,))
    elif folder == "sent":
        cursor.execute("SELECT * FROM communications WHERE sender_id = ? AND status = 'sent' ORDER BY timestamp DESC", (identity.employee_id,))
    else:
        cursor.execute("SELECT * FROM communications WHERE (recipient LIKE ? OR recipient = 'all-staff@novatech.com' OR sender_id = ?) ORDER BY timestamp DESC", (f"%{identity.email}%", identity.employee_id))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"communications": rows, "count": len(rows), "folder": folder or "all"}

@app.post("/api/tools/communications/send", tags=["Tools"])
async def send_communication_endpoint(
    payload: dict,
    identity: IdentityContext = Depends(get_current_identity)
):
    """Direct endpoint to send email or update draft to sent."""
    if not check_permission(identity, "communication.send"):
        raise HTTPException(status_code=403, detail="Permission denied: 'communication.send' required.")

    from .mcp.tools.communication_tools import handle_send_email
    return handle_send_email(identity, payload)

@app.post("/api/tools/communications/draft", tags=["Tools"])
async def draft_communication_endpoint(
    payload: dict,
    identity: IdentityContext = Depends(get_current_identity)
):
    """Direct endpoint to create or update a draft email."""
    if not check_permission(identity, "communication.draft"):
        raise HTTPException(status_code=403, detail="Permission denied: 'communication.draft' required.")

    from .mcp.tools.communication_tools import handle_draft_email
    return handle_draft_email(identity, payload)

@app.delete("/api/tools/communications/{comm_id}", tags=["Tools"])
async def delete_communication_endpoint(
    comm_id: str,
    identity: IdentityContext = Depends(get_current_identity)
):
    """Direct endpoint to discard/delete an email draft."""
    if not check_permission(identity, "communication.draft"):
        raise HTTPException(status_code=403, detail="Permission denied: 'communication.draft' required.")

    from .mcp.tools.communication_tools import handle_delete_communication
    res = handle_delete_communication(identity, comm_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res["message"])
    return res

@app.get("/api/tools/calendar", tags=["Tools"])
async def get_calendar_endpoint(identity: IdentityContext = Depends(get_current_identity)):
    """Get schedule for authenticated employee."""
    if not check_permission(identity, "calendar.read"):
        raise HTTPException(status_code=403, detail="Permission denied: 'calendar.read' required.")
    from .mcp.tools.calendar_tools import handle_get_my_calendar
    return handle_get_my_calendar(identity, {})

@app.post("/api/tools/calendar/book", tags=["Tools"])
async def book_calendar_endpoint(
    payload: dict,
    identity: IdentityContext = Depends(get_current_identity)
):
    """Book a calendar meeting."""
    if not check_permission(identity, "calendar.create"):
        raise HTTPException(status_code=403, detail="Permission denied: 'calendar.create' required.")
    from .mcp.tools.calendar_tools import handle_schedule_meeting
    res = handle_schedule_meeting(identity, payload)
    if res.get("status") == "conflict":
        raise HTTPException(status_code=409, detail=res["message"])
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res["message"])
    return res

@app.delete("/api/tools/calendar/{event_id}", tags=["Tools"])
async def delete_calendar_meeting_endpoint(
    event_id: str,
    identity: IdentityContext = Depends(get_current_identity)
):
    """Cancel and delete a scheduled calendar meeting."""
    if not check_permission(identity, "calendar.create"):
        raise HTTPException(status_code=403, detail="Permission denied: 'calendar.create' required.")
    from .mcp.tools.calendar_tools import handle_delete_meeting
    res = handle_delete_meeting(identity, {"event_id": event_id})
    if res.get("status") == "permission_denied":
        raise HTTPException(status_code=403, detail=res["message"])
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res["message"])
    return res

@app.get("/api/tools/hr/profile", tags=["Tools"])
async def get_hr_profile_endpoint(identity: IdentityContext = Depends(get_current_identity)):
    """Get personal HR record and leave balances."""
    if not check_permission(identity, "hr.self"):
        raise HTTPException(status_code=403, detail="Permission denied: 'hr.self' required.")
    from .mcp.tools.hr_tools import handle_get_my_hr_profile
    return handle_get_my_hr_profile(identity, {})

@app.get("/api/tools/hr/team", tags=["Tools"])
async def get_team_hr_endpoint(identity: IdentityContext = Depends(get_current_identity)):
    """Get departmental HR summary (Manager/Admin)."""
    if not check_permission(identity, "hr.team"):
        raise HTTPException(status_code=403, detail="Permission denied: 'hr.team' required.")
    from .mcp.tools.hr_tools import handle_get_team_hr_summary
    return handle_get_team_hr_summary(identity, {})

@app.get("/api/tools/hr/payroll", tags=["Tools"])
async def get_all_hr_payroll_endpoint(identity: IdentityContext = Depends(get_current_identity)):
    """Get all company payroll records (HR/Admin only)."""
    if not check_permission(identity, "hr.all"):
        raise HTTPException(status_code=403, detail="Permission denied: 'hr.all' required.")
    from .mcp.tools.hr_tools import handle_get_all_hr_payroll
    return handle_get_all_hr_payroll(identity, {})

@app.post("/api/tools/hr/leave", tags=["Tools"])
async def request_leave_endpoint(
    payload: dict,
    identity: IdentityContext = Depends(get_current_identity)
):
    """Request time off or sick leave."""
    if not check_permission(identity, "hr.self"):
        raise HTTPException(status_code=403, detail="Permission denied: 'hr.self' required.")
    from .mcp.tools.hr_tools import handle_request_leave
    return handle_request_leave(identity, payload)

@app.get("/api/tools/documents/policies", tags=["Tools"])
async def get_policies_endpoint(identity: IdentityContext = Depends(get_current_identity)):
    """List loaded enterprise policies authorized strictly for the authenticated employee's role."""
    if not check_permission(identity, "documents.read"):
        raise HTTPException(status_code=403, detail="Permission denied: 'documents.read' required.")
    from .knowledge import DOCUMENT_ROLE_ACCESS, is_document_authorized_for_role
    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "enterprise_docs"))
    policies = []
    total_docs = 0
    if os.path.exists(docs_dir):
        all_files = sorted([f for f in os.listdir(docs_dir) if f.endswith(".txt")])
        total_docs = len(all_files)
        for fname in all_files:
            # Enforce Zero-Trust RBAC: only return documents authorized for this role
            if not is_document_authorized_for_role(fname, identity.role):
                continue
            fpath = os.path.join(docs_dir, fname)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            meta = DOCUMENT_ROLE_ACCESS.get(fname, {})
            category = meta.get("category", "General Enterprise")
            tier = meta.get("tier", "Tier 1 - General Enterprise")
            title = fname.replace("_", " ").replace(".txt", "")
            policies.append({
                "filename": fname,
                "title": title,
                "category": category,
                "tier": tier,
                "length": len(content),
                "summary": content[:280].strip() + ("..." if len(content) > 280 else ""),
                "content": content
            })
    return {
        "policies": policies,
        "count": len(policies),
        "authorized_count": len(policies),
        "total_enterprise_documents": total_docs,
        "user_role": identity.role
    }

@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(
    request: ChatRequest,
    identity: IdentityContext = Depends(get_current_identity)
):
    """
    Main conversational endpoint.
    Strictly verifies employee identity via server session token.
    Ignores any client-supplied employee_id headers or body overrides.
    """
    if not check_permission(identity, "knowledge.read"):
        raise HTTPException(status_code=403, detail="Access Denied: Your role lacks 'knowledge.read' permission.")

    try:
        session = conversation_manager.get_or_create_session(request.conversation_id)
        history_context = session.get_history_context()

        # Record user turn in memory
        session.add_message("user", request.message)

        # Process through agent with server-verified authenticated identity
        response = foundry_agent.process_message(
            message=request.message,
            conversation_id=session.conversation_id,
            history_context=history_context,
            language=request.language or "en",
            session_file_id=request.session_file_id,
            identity=identity
        )

        # Record assistant turn in memory
        session.add_message("assistant", response.answer, [s.model_dump() for s in response.sources])

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
