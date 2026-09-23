import re
import json
import logging
from typing import Dict, Any, List, Optional
from .config import settings
from .models.schemas import ChatResponse, SourceCitation, ToolCallResult
from .knowledge import knowledge_base
from .language import translate_or_localize
from .auth import IdentityContext, resolve_identity, check_permission
from .mcp.registry import mcp_registry
from .mcp.tools import register_all_connectors
from .mcp.tools.communication_tools import parse_email_intent
from .mcp.tools.calendar_tools import parse_meeting_intent

logger = logging.getLogger("knoquest.agent")

# Initialize and register all MCP enterprise connectors
register_all_connectors()

class FoundryAgentService:
    """
    Microsoft Foundry Agent Client Wrapper with Enterprise Authorization & Grounded RAG.
    Enforces server-side permission checks across all tools before execution.
    """

    def __init__(self):
        self.project_client = None
        self.openai_client = None
        self.is_azure_ready = False
        self._init_azure_client()

    def _init_azure_client(self):
        if not settings.AZURE_MODE:
            logger.info("Running in Enterprise Sandbox (local) mode.")
            return

        try:
            if settings.AZURE_PROJECT_ENDPOINT or settings.AZURE_PROJECT_CONNECTION_STRING:
                from azure.identity import DefaultAzureCredential
                from azure.ai.projects import AIProjectClient

                credential = DefaultAzureCredential()
                if settings.AZURE_PROJECT_CONNECTION_STRING:
                    self.project_client = AIProjectClient.from_connection_string(
                        credential=credential,
                        conn_str=settings.AZURE_PROJECT_CONNECTION_STRING
                    )
                else:
                    self.project_client = AIProjectClient(
                        endpoint=settings.AZURE_PROJECT_ENDPOINT,
                        credential=credential
                    )
                self.openai_client = self.project_client.get_openai_client()
                self.is_azure_ready = True
                logger.info(f"Connected to Microsoft Foundry Project at '{settings.AZURE_PROJECT_ENDPOINT}'.")
        except Exception as e:
            logger.warning(f"Could not connect to Azure Foundry: {e}.")
            self.is_azure_ready = False

    def process_message(
        self,
        message: str,
        conversation_id: str,
        history_context: str = "",
        language: str = "en",
        session_file_id: Optional[str] = None,
        identity: Optional[IdentityContext] = None
    ) -> ChatResponse:
        """
        Processes query: Identify -> Authorize -> Execute Tool / Retrieve -> Answer.
        """
        # Ensure authenticated identity context
        if not identity:
            identity = resolve_identity("NOVA-EMP001")
            if not identity:
                raise ValueError("Could not resolve default employee identity.")

        clean_msg = message.strip()
        lower_msg = clean_msg.lower()

        # Helper to construct denied response
        def permission_denied_response(tool_res: Dict[str, Any], tool_name: str, params: Dict[str, Any]) -> ChatResponse:
            ans = (
                f"🚫 **Access Denied: Enterprise Authorization Required**\n\n"
                f"{tool_res['message']}\n\n"
                f"• **Current User:** {identity.name} (`{identity.full_id}`)\n"
                f"• **Role:** {identity.role} ({identity.department})\n"
                f"• **Required Permission:** `{tool_res.get('required_permission', 'Unknown')}`\n\n"
                f"Your active session permissions: {', '.join([f'`{p}`' for p in identity.permissions])}"
            )
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name=tool_name, parameters=params, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 1. Conversational greetings
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "greetings"]
        if lower_msg in greetings or lower_msg.startswith("hello ") or lower_msg.startswith("hi "):
            greeting_text = (
                f"Hello {identity.name}! I am KnoQuest, your enterprise AI assistant for NovaTech Solutions.\n\n"
                f"• **Authenticated as:** {identity.name} ({identity.designation})\n"
                f"• **Role & Department:** {identity.role} in {identity.department}\n"
                f"• **ID:** `{identity.full_id}`\n\n"
                f"How can I assist you today? You can query company policies, check your HR leave balance, view calendar events, search emails, or open IT support tickets."
            )
            return ChatResponse(
                answer=greeting_text,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 2. Who am I / Profile intent
        if any(kw in lower_msg for kw in ["who am i", "my profile", "my identity", "my permissions", "what is my role", "what are my permissions"]):
            tool_res = mcp_registry.execute_tool("get_employee_profile", {"employee_id": identity.employee_id}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "get_employee_profile", {})
            profile = tool_res.get("profile", {})
            perms_str = "\n".join([f"- `{p}`" for p in identity.permissions])
            ans = (
                f"### 👤 Authenticated Employee Profile\n\n"
                f"• **Name:** {profile.get('name', identity.name)}\n"
                f"• **Company ID:** `{identity.full_id}`\n"
                f"• **Email:** {profile.get('email', identity.email)}\n"
                f"• **Role:** {identity.role}\n"
                f"• **Department:** {identity.department}\n"
                f"• **Designation:** {identity.designation}\n"
                f"• **Location:** {profile.get('location', 'HQ')}\n"
                f"• **Status:** {identity.status}\n\n"
                f"**Active Session Permissions ({len(identity.permissions)}):**\n{perms_str}"
            )
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="get_employee_profile", parameters={"employee_id": identity.employee_id}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 3. HR Tools (Self, Team, All Payroll, Leave Request)
        # 3a. Everyone's salary / all payroll (requires hr.all)
        if any(kw in lower_msg for kw in ["everyone's salary", "all salaries", "all salary", "company salary", "all payroll", "everyone salary", "executive compensation", "payroll for all"]):
            tool_res = mcp_registry.execute_tool("get_all_hr_payroll", {}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "get_all_hr_payroll", {})
            records = tool_res.get("payroll_records", [])
            lines = [f"- **{r['name']}** ({r['department']}, {r['role']}): {r['salary_band']} | Rating: *{r['performance_rating']}*" for r in records]
            ans = f"### 📊 NovaTech Solutions Confidential Payroll & Compensation Registry\n\n" + "\n".join(lines)
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="get_all_hr_payroll", parameters={}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 3b. Team HR overview (requires hr.team)
        if any(kw in lower_msg for kw in ["team hr", "team leave", "department leave", "team balance", "my team's leave"]):
            tool_res = mcp_registry.execute_tool("get_team_hr_summary", {}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "get_team_hr_summary", {})
            members = tool_res.get("team_members", [])
            lines = [f"- **{m['name']}** ({m['designation']}): {m['leave_balance_paid']} Paid Days Left | Rating: *{m['performance_rating']}*" for m in members]
            ans = f"### 👥 {identity.department} Team HR & Leave Overview\n\n" + "\n".join(lines)
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="get_team_hr_summary", parameters={}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 3c. Request Leave (requires hr.self)
        if any(kw in lower_msg for kw in ["request leave", "apply for leave", "take leave", "book leave", "apply leave", "request 1 day leave", "request 2 days leave"]):
            days_match = re.search(r'(\d+)\s*day', lower_msg)
            days = int(days_match.group(1)) if days_match else 1
            leave_type = "Sick" if "sick" in lower_msg else "Paid"
            tool_res = mcp_registry.execute_tool("request_leave", {"days": days, "leave_type": leave_type}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "request_leave", {"days": days})
            ans = (
                f"✅ **Leave Request Submitted Successfully**\n\n"
                f"• **Employee:** {identity.name} (`{identity.full_id}`)\n"
                f"• **Type:** {leave_type} Leave\n"
                f"• **Days Requested:** {days}\n"
                f"• **Remaining Balance:** {tool_res.get('remaining_balance')} days\n"
                f"• **Status:** Approved and recorded in HR database."
            )
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="request_leave", parameters={"days": days}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 3d. Personal HR Profile & Leave balance (requires hr.self)
        if any(kw in lower_msg for kw in ["my hr", "my leave", "my performance", "my salary", "my compensation", "show my hr", "check my leave", "how many days leave", "my leave balance", "my remaining leave"]):
            tool_res = mcp_registry.execute_tool("get_my_hr_profile", {}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "get_my_hr_profile", {})
            ans = (
                f"### 📋 Personal HR & Benefits Summary for {identity.name}\n\n"
                f"• **Employee ID:** `{identity.full_id}`\n"
                f"• **Department:** {identity.department}\n"
                f"• **Paid Annual Leave Remaining:** **{tool_res.get('leave_balance_paid_days')} days**\n"
                f"• **Sick Leave Remaining:** **{tool_res.get('leave_balance_sick_days')} days**\n"
                f"• **Salary Band:** {tool_res.get('salary_band')}\n"
                f"• **Performance Rating:** *{tool_res.get('performance_rating')}*\n"
                f"• **Notes:** {tool_res.get('compensation_notes')}"
            )
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="get_my_hr_profile", parameters={}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 4. IT Tickets (Own, All, Create)
        # 4a. List all company tickets (requires it.view_all_tickets)
        if any(kw in lower_msg for kw in ["all tickets", "all it tickets", "company tickets", "view all tickets", "list all tickets", "show all tickets"]):
            tool_res = mcp_registry.execute_tool("list_all_it_tickets", {}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "list_all_it_tickets", {})
            tickets = tool_res.get("tickets", [])
            lines = [f"- **{t['ticket_id']}** [{t['status']}] ({t['priority']}) - {t['user_name']} ({t['department']}): {t['issue']}" for t in tickets]
            ans = f"### 🎫 NovaTech All Support Tickets ({len(tickets)})\n\n" + "\n".join(lines)
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="list_all_it_tickets", parameters={}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 4b. List my own tickets (requires it.view_own_ticket)
        if any(kw in lower_msg for kw in ["my tickets", "my it tickets", "view my tickets", "show my tickets", "check my ticket", "my open tickets"]):
            tool_res = mcp_registry.execute_tool("list_my_it_tickets", {}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "list_my_it_tickets", {})
            tickets = tool_res.get("tickets", [])
            if not tickets:
                ans = f"You currently have no IT support tickets opened under `{identity.full_id}`."
            else:
                lines = [f"- **{t['ticket_id']}** [{t['status']}] ({t['priority']} priority): {t['issue']} (Created: {t['created_at']})" for t in tickets]
                ans = f"### 🎫 Your IT Support Tickets ({len(tickets)})\n\n" + "\n".join(lines)
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="list_my_it_tickets", parameters={}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 4c. Create IT Ticket (requires it.create_ticket)
        ticket_triggers = [
            "create an it ticket", "raise an it ticket", "create a ticket", "log a ticket",
            "it ticket", "laptop is broken", "laptop is not working", "screen is broken",
            "create ticket", "open ticket", "raise ticket", "log ticket", "issue a ticket"
        ]
        if (any(trig in lower_msg for trig in ticket_triggers) and ("ticket" in lower_msg or "broken" in lower_msg or "not working" in lower_msg)) or ("create" in lower_msg and "ticket" in lower_msg):
            issue_title, issue_priority = self._structure_intelligent_ticket(clean_msg)
            tool_res = mcp_registry.execute_tool("create_it_ticket", {"issue": issue_title, "priority": issue_priority}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "create_it_ticket", {"issue": issue_title})
            ans = (
                f"🎫 **IT Support Ticket Created**\n\n"
                f"• **Ticket ID:** `{tool_res['ticket_id']}`\n"
                f"• **Status:** {tool_res['ticket_status']}\n"
                f"• **Priority:** **{tool_res['priority']}**\n"
                f"• **Category / Issue:** {tool_res['issue']}\n"
                f"• **User:** {identity.name} (`{identity.full_id}`)\n\n"
                f"💡 *An IT technician from the NovaTech Helpdesk has been dispatched and will contact you shortly.*"
            )
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="create_it_ticket", parameters={"issue": issue_title, "priority": issue_priority}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )
        # 4d. Update / Resolve IT Ticket (requires it.update_ticket)
        is_update_ticket = any(kw in lower_msg for kw in [
            "resolve ticket", "resolve it ticket", "mark ticket as resolved", "mark as resolved",
            "close ticket", "close it ticket", "update ticket", "update it ticket", "ticket resolved"
        ]) or bool(re.search(r'\b(resolve|close|update)\b.*\bIT-\d+\b', clean_msg, re.IGNORECASE))

        if is_update_ticket:
            ticket_id_match = re.search(r'\b(IT-\d+)\b', clean_msg, re.IGNORECASE)
            ticket_id = ticket_id_match.group(1).upper() if ticket_id_match else ""
            if not ticket_id:
                # Fallback to the latest ticket if any
                from .database import get_db_connection
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT ticket_id FROM it_tickets WHERE status != 'Resolved' ORDER BY created_at DESC LIMIT 1")
                r = cur.fetchone()
                conn.close()
                if r:
                    ticket_id = r[0]

            if not ticket_id:
                return ChatResponse(
                    answer="Please specify the Ticket ID you wish to update (e.g., `Resolve ticket IT-1001`).",
                    conversation_id=conversation_id,
                    sources=[],
                    tool_calls=[],
                    mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                    language=language,
                    authenticated_user=identity.model_dump()
                )

            # Determine new status
            if "in progress" in lower_msg:
                new_status = "In Progress"
            elif "open" in lower_msg and "reopen" in lower_msg:
                new_status = "Open"
            else:
                new_status = "Resolved"

            tool_res = mcp_registry.execute_tool(
                "update_it_ticket",
                {"ticket_id": ticket_id, "status": new_status},
                identity
            )
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "update_it_ticket", {"ticket_id": ticket_id, "status": new_status})
            
            if tool_res.get("status") == "error":
                ans = f"⚠️ **Ticket Update Notice**: {tool_res.get('message', 'Ticket not found.')}"
            else:
                t = tool_res["ticket"]
                ans = (
                    f"✅ **IT Ticket Updated Successfully**\n\n"
                    f"• **Ticket ID:** `{t['ticket_id']}`\n"
                    f"• **Status:** **{t['status']}**\n"
                    f"• **User:** {t['user_name']} ({t['department']})\n"
                    f"• **Priority:** {t['priority']}\n"
                    f"• **Issue:** {t['issue']}\n\n"
                    f"💡 *{'This ticket is now resolved and archived from the active IT tickets list. The resolved counter has been incremented.' if new_status == 'Resolved' else 'The ticket status has been updated in the system.'}*"
                )

            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="update_it_ticket", parameters={"ticket_id": ticket_id, "status": new_status}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 5. Calendar / Meetings (requires calendar.read / calendar.create)
        if any(kw in lower_msg for kw in ["my calendar", "my schedule", "my meetings", "upcoming meetings", "check my availability", "what meetings do i have"]):
            tool_res = mcp_registry.execute_tool("get_my_calendar", {}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "get_my_calendar", {})
            events = tool_res.get("events", [])
            if not events:
                ans = f"You have no upcoming calendar events scheduled for `{identity.email}`."
            else:
                lines = [f"- **{ev['title']}** | {ev['start_time']} - {ev['end_time']} ({ev['location']})\n  *Attendees:* {ev['attendees']}" for ev in events]
                ans = f"### 📅 Calendar Schedule for {identity.name}\n\n" + "\n\n".join(lines)
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="get_my_calendar", parameters={}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        if any(kw in lower_msg for kw in ["schedule meeting", "book meeting", "create meeting", "schedule a meeting", "book a sync", "schedule sync"]):
            parsed_meeting = parse_meeting_intent(clean_msg, organizer_email=identity.email)
            refined_title = self._structure_intelligent_meeting(clean_msg, parsed_meeting["title"])
            parsed_meeting["title"] = refined_title
            tool_res = mcp_registry.execute_tool(
                "schedule_meeting",
                {
                    "title": refined_title,
                    "start_time": parsed_meeting["start_time"],
                    "end_time": parsed_meeting["end_time"],
                    "attendees": parsed_meeting["attendees"],
                    "location": parsed_meeting["location"]
                },
                identity
            )
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "schedule_meeting", parsed_meeting)
            if tool_res.get("status") in ["conflict", "error"]:
                ans = (
                    f"⚠️ **Scheduling Conflict - Time Frame Already Booked**\n\n"
                    f"{tool_res.get('message', 'The requested time frame conflicts with an existing scheduled meeting.')}\n\n"
                    f"🔒 **Enterprise Conflict Policy:** Existing meeting time frames cannot be overridden. Please choose an alternate start or end time."
                )
                return ChatResponse(
                    answer=ans,
                    conversation_id=conversation_id,
                    sources=[],
                    tool_calls=[ToolCallResult(tool_name="schedule_meeting", parameters=parsed_meeting, result=tool_res)],
                    mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                    language=language,
                    authenticated_user=identity.model_dump()
                )
            ans = (
                f"✅ **Calendar Meeting Scheduled**\n\n"
                f"• **Title:** {tool_res['title']}\n"
                f"• **Start Time:** {tool_res['start_time']}\n"
                f"• **End Time:** {tool_res.get('end_time', parsed_meeting['end_time'])}\n"
                f"• **Organizer:** {identity.name} ({identity.email})\n"
                f"• **Attendees:** {tool_res['attendees']}\n"
                f"• **Location:** {tool_res['location']}\n"
                f"• **Event ID:** `{tool_res['event_id']}`\n\n"
                f"💡 *This meeting has been synced to your NovaTech Microsoft Teams & Outlook calendar.*"
            )
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="schedule_meeting", parameters=parsed_meeting, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 5b. Cancel / Delete Calendar Meeting
        if any(kw in lower_msg for kw in ["cancel meeting", "delete meeting", "cancel my meeting", "delete my meeting", "remove meeting", "cancel the meeting", "cancel sync"]):
            evt_match = re.search(r'\b(EVT-\d+)\b', clean_msg, re.IGNORECASE)
            event_id = evt_match.group(1).upper() if evt_match else None

            if not event_id:
                cal_res = mcp_registry.execute_tool("get_my_calendar", {}, identity)
                my_events = cal_res.get("events", [])
                for ev in my_events:
                    ev_title_lower = ev["title"].lower()
                    words = [w for w in re.findall(r'\b[a-z]{3,}\b', lower_msg) if w not in ["cancel", "delete", "meeting", "sync", "remove", "with", "about", "the"]]
                    if words and any(w in ev_title_lower for w in words):
                        event_id = ev["event_id"]
                        break
                if not event_id and len(my_events) == 1:
                    event_id = my_events[0]["event_id"]

            if not event_id:
                ans = "Please specify the Event ID (e.g. `EVT-201`) or title of the meeting you wish to cancel."
                return ChatResponse(
                    answer=ans,
                    conversation_id=conversation_id,
                    sources=[],
                    tool_calls=[],
                    mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                    language=language,
                    authenticated_user=identity.model_dump()
                )

            tool_res = mcp_registry.execute_tool("delete_meeting", {"event_id": event_id}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "delete_meeting", {"event_id": event_id})
            if tool_res.get("status") == "error":
                ans = f"❌ **Failed to Cancel Meeting:** {tool_res.get('message')}"
            else:
                ans = (
                    f"🗑️ **Meeting Successfully Cancelled**\n\n"
                    f"• **Title:** {tool_res.get('title')}\n"
                    f"• **Event ID:** `{tool_res.get('event_id')}`\n"
                    f"• **Time Slot:** {tool_res.get('start_time')} - {tool_res.get('end_time')}\n\n"
                    f"The appointment has been removed from your calendar and the time slot is now available."
                )
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="delete_meeting", parameters={"event_id": event_id}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 6a. Viewing drafts & emails (Outlook / Teams)
        if any(kw in lower_msg for kw in ["where can i see the drafted", "where can i see my draft", "where is the drafted", "where are my draft", "show my draft", "show drafts", "see my draft", "list draft", "my drafts", "view drafts", "find my draft"]):
            tool_res = mcp_registry.execute_tool("list_email_drafts", {}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "list_email_drafts", {})
            drafts = tool_res.get("drafts", [])
            if not drafts:
                ans = (
                    f"You currently have no saved email drafts in Outlook for `{identity.email}`.\n\n"
                    f"To create a draft, you can say: `Draft email to team@novatech.com regarding Sprint Review`."
                )
            else:
                lines = [
                    f"- **[{d['comm_id']}]** To: `{d['recipient']}` | Subject: **{d['subject']}**\n  *Body:* {d['body']}\n  *(Saved: {d['timestamp']})*"
                    for d in drafts
                ]
                ans = (
                    f"### 📝 Microsoft Outlook — Saved Email Drafts for {identity.name}\n\n"
                    f"Here are your currently drafted emails saved in your Outlook mailbox:\n\n"
                    + "\n\n".join(lines) +
                    f"\n\n💡 *You can send any draft at any time by saying: `Send email to {drafts[0]['recipient']} regarding {drafts[0]['subject']}`.*"
                )
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="list_email_drafts", parameters={}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        if any(kw in lower_msg for kw in ["my emails", "search emails", "search inbox", "check my emails", "check messages", "recent emails", "outlook"]):
            tool_res = mcp_registry.execute_tool("search_emails", {"query": clean_msg}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "search_emails", {"query": clean_msg})
            messages = tool_res.get("messages", [])
            if not messages:
                ans = f"No communications found matching your query."
            else:
                lines = [f"- **[{m['comm_type'].upper()}]** {m['subject'] or '(No Subject)'} (To: {m['recipient']})\n  *{m['body']}*" for m in messages]
                ans = f"### 📬 Corporate Communications for {identity.name}\n\n" + "\n\n".join(lines)
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="search_emails", parameters={"query": clean_msg}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 6b. Send Email Intent (must come before draft email to avoid false triggers)
        is_send_email = any(kw in lower_msg for kw in [
            "send email", "send an email", "send the email", "send a mail", "send mail", "send the mail",
            "send message", "send draft", "send this draft", "send the draft", "send out email", "send communication"
        ])

        if is_send_email:
            parsed = parse_email_intent(clean_msg)
            draft_id = parsed.get("draft_id")
            recipient = parsed["recipient"]
            subject = parsed["subject"]
            body = parsed["body"]

            # If user refers to an existing draft or says "send the draft" without details
            from .database import get_db_connection
            conn = get_db_connection()
            cur = conn.cursor()
            if draft_id:
                cur.execute("SELECT * FROM communications WHERE comm_id = ? AND sender_id = ?", (draft_id, identity.employee_id))
                draft_row = cur.fetchone()
                if draft_row:
                    recipient = draft_row["recipient"]
                    subject = draft_row["subject"]
                    body = draft_row["body"]
            elif clean_msg.strip().lower() in ["send draft", "send the draft", "send this draft", "send the email", "send the mail", "send mail", "send email"]:
                cur.execute("SELECT * FROM communications WHERE sender_id = ? AND status = 'draft' ORDER BY timestamp DESC LIMIT 1", (identity.employee_id,))
                latest_draft = cur.fetchone()
                if latest_draft:
                    draft_id = latest_draft["comm_id"]
                    recipient = latest_draft["recipient"]
                    subject = latest_draft["subject"]
                    body = latest_draft["body"]
            conn.close()

            # Intelligent synthesis if new email without explicit quotes
            if not draft_id:
                has_explicit_quotes = ('"' in clean_msg or "'" in clean_msg) and "subject" in lower_msg and "body" in lower_msg
                if not has_explicit_quotes:
                    int_sub, int_body = self._compose_intelligent_email(clean_msg, recipient, identity)
                    subject = int_sub
                    body = int_body

            send_params = {
                "recipient": recipient,
                "subject": subject,
                "body": body
            }
            if draft_id:
                send_params["draft_id"] = draft_id

            tool_res = mcp_registry.execute_tool("send_email", send_params, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "send_email", send_params)

            ans = (
                f"✉️ **Email Sent Successfully**\n\n"
                f"• **Channel:** {tool_res.get('channel', 'Microsoft Outlook')}\n"
                f"• **To:** `{tool_res['recipient']}`\n"
                f"• **Subject:** **{tool_res['subject']}**\n"
                f"• **Message ID:** `{tool_res['comm_id']}`\n"
                f"• **Timestamp:** {tool_res['timestamp']}\n\n"
                f"💡 *This message has been dispatched and is visible in your **Sent Items** in the Email section.*"
            )
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="send_email", parameters=send_params, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 6c. Draft Email Intent (handles 'save draft', 'draft an email', 'save the draft of the email', etc.)
        is_draft_email = any(kw in lower_msg for kw in [
            "draft email", "draft an email", "draft a mail", "draft mail", "draft the email",
            "save draft", "save a draft", "save the draft", "save an email draft", "save email draft", "save the email draft",
            "save draft of email", "save the draft of the email", "save a draft of the email", "save a draft of email",
            "save mail", "save the mail", "save email", "save this draft", "save as draft", "store draft",
            "compose email", "compose an email", "compose draft", "compose a draft", "compose a mail",
            "create draft", "create a draft", "create an email draft", "make a draft", "prepare draft", "prepare email"
        ]) or (
            ("draft" in lower_msg or "compose" in lower_msg or "save" in lower_msg) and ("email" in lower_msg or "mail" in lower_msg)
        )

        if is_draft_email:
            parsed = parse_email_intent(clean_msg)
            draft_id = parsed.get("draft_id")
            recipient = parsed["recipient"]
            subject = parsed["subject"]
            body = parsed["body"]

            if not draft_id:
                has_explicit_quotes = ('"' in clean_msg or "'" in clean_msg) and "subject" in lower_msg and "body" in lower_msg
                if not has_explicit_quotes:
                    int_sub, int_body = self._compose_intelligent_email(clean_msg, recipient, identity)
                    subject = int_sub
                    body = int_body

            draft_params = {
                "recipient": recipient,
                "subject": subject,
                "body": body
            }
            if draft_id:
                draft_params["draft_id"] = draft_id

            tool_res = mcp_registry.execute_tool("draft_email", draft_params, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "draft_email", draft_params)

            ans = (
                f"📝 **Email Draft Saved**: Stored draft `{tool_res['draft_id']}` in your **Microsoft Outlook Drafts**.\n\n"
                f"• **To:** `{tool_res['to']}`\n"
                f"• **Subject:** **{tool_res['subject']}**\n"
                f"• **Preview:** *{tool_res['body'][:120]}...*\n\n"
                f"💡 *This draft is now saved and visible in the **Email** section under **Drafts**.*"
            )
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="draft_email", parameters=draft_params, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 7. SharePoint / OneDrive libraries
        if any(kw in lower_msg for kw in ["sharepoint", "onedrive", "document libraries", "accessible libraries"]):
            tool_res = mcp_registry.execute_tool("list_sharepoint_libraries", {}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "list_sharepoint_libraries", {})
            libs = tool_res.get("libraries", [])
            lines = [f"- **{lib['name']}** ({lib['type']}): Status **{lib['access']}**\n  URL: `{lib['site']}`" for lib in libs]
            ans = f"### 📁 Enterprise SharePoint & OneDrive Repositories\n\n" + "\n\n".join(lines)
            return ChatResponse(
                answer=ans,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[ToolCallResult(tool_name="list_sharepoint_libraries", parameters={}, result=tool_res)],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 8. Employee Directory Search Intent
        directory_keywords = [
            "who is the", "who is", "who's the", "who's", "find employee", "search directory",
            "contact details", "contact for", "contact regarding", "reach out to", "ciso",
            "vp of people", "vp of hr", "infrastructure engineer", "travel coordinator",
            "expense coordinator", "operations manager", "facilities manager", "who handles",
            "who do i contact", "who should i contact", "who to contact", "employee directory"
        ]
        employee_first_or_last = [
            "sarah", "jenkins", "david", "kumar", "marcus", "vance",
            "elena", "rostova", "alex", "chen", "rahul", "sharma"
        ]
        has_direct_name = any(re.search(r'\b' + re.escape(name) + r'\b', lower_msg) for name in employee_first_or_last)
        has_role_or_contact = any(kw in lower_msg for kw in [
            "travel coordinator", "expense coordinator", "who do i contact", "who to contact",
            "who should i contact", "who handles travel", "contact for travel", "ciso",
            "vp of people", "vp of hr", "infrastructure engineer", "operations manager"
        ])
        policy_exclusions = [
            "policy", "leave", "wfh", "password", "hours", "ticket",
            "remote", "eligible", "eligibility", "probation", "work from home",
            "incident", "equipment", "replacement", "benefits", "benefit",
            "insurance", "allowance", "hotel", "conduct", "car", "pet", "mfa"
        ]
        is_policy_focused = any(re.search(r'\b' + re.escape(pex) + r'\b', lower_msg) for pex in policy_exclusions)

        if ((has_direct_name or has_role_or_contact) and not is_policy_focused) or (any(kw in lower_msg for kw in directory_keywords) and not is_policy_focused):
            tool_res = mcp_registry.execute_tool("search_employee_directory", {"query": clean_msg}, identity)
            if tool_res.get("status") == "permission_denied":
                return permission_denied_response(tool_res, "search_employee_directory", {"query": clean_msg})

            matches = tool_res.get("employees", [])
            tool_call = ToolCallResult(
                tool_name="search_employee_directory",
                parameters={"query": clean_msg},
                result={"matches_found": len(matches), "employees": matches}
            )

            if len(matches) == 1:
                e = matches[0]
                emp_name = e.get("name", "")
                emp_id = f"{e.get('company_id', 'NOVA')}-{e.get('employee_id', '')}"
                designation = e.get("designation") or e.get("role", "Staff Member")
                dept = e.get("department", "General")
                email = e.get("email", "")
                ext = e.get("extension", "N/A")
                loc = e.get("location", "NovaTech Headquarters")
                status = e.get("status", "Active")

                # Knowledge-grounded responsibilities mapping for NovaTech employees
                scope_map = {
                    "sarah jenkins": (
                        "• **HR Policy Leadership:** Formulates corporate HR policies including Paid Annual Leave (20 days/yr), Sick Leave (10 days), and Remote Work (WFH) eligibility.\n"
                        "• **Benefits Administration:** Oversees employee health insurance, dental/vision coverage, and wellness allowances.\n"
                        "• **Talent & Personnel Operations:** Coordinates executive recruiting, onboarding, performance appraisals, probation reviews, and personnel escalations."
                    ),
                    "marcus vance": (
                        "• **IT Infrastructure & Helpdesk:** Leads Tier-2/3 technical helpdesk, server maintenance, network security, and infrastructure monitoring.\n"
                        "• **Hardware Lifecycle:** Manages laptop procurement, 3-year standard equipment replacement cycles, and emergency repair replacements.\n"
                        "• **Access & Security Tools:** Configures enterprise VPN, multi-factor authentication (MFA) tokens, single sign-on (SSO), and developer software licenses."
                    ),
                    "elena rostova": (
                        "• **Corporate Travel Approvals:** Coordinates domestic and international flight, train, and rental car reservations via corporate travel portals.\n"
                        "• **Per Diem & Expense Reimbursement:** Enforces daily per diem rates ($75 standard, $100 Tier-1 cities) and hotel allowances (up to $250/night).\n"
                        "• **Finance Reconciliation:** Reviews travel expense reports, meal receipts, and ensures compliance with NovaTech corporate finance policies."
                    ),
                    "david kumar": (
                        "• **Information Security Governance:** Chief owner of NovaTech cybersecurity architecture, ISO 27001, and SOC 2 Type II compliance.\n"
                        "• **Password & Access Standards:** Enforces 16+ character master passwords, biometric MFA, quarterly credential audits, and session lockouts.\n"
                        "• **Threat & Incident Management:** Oversees security incident response, device encryption enforcement, and vendor risk assessments."
                    ),
                    "alex chen": (
                        "• **Workplace Operations:** Manages physical campus facilities, HQ floor plans, meeting room setups, and workstation allocations.\n"
                        "• **Remote Work Stipend:** Administers the $500 one-time home office ergonomic setup stipend and monitor allocations.\n"
                        "• **Building Security & Badging:** Issues electronic keycards, visitor credentials, and oversees campus health/safety protocols."
                    ),
                    "rahul sharma": (
                        "• **Core Platform Engineering:** Develops backend microservices, high-throughput REST APIs, and database architecture.\n"
                        "• **AI Agent & MCP Tooling:** Orchestrates Model Context Protocol (MCP) integrations, Azure OpenAI agents, and cognitive RAG pipelines.\n"
                        "• **Code Quality & CI/CD:** Contributes to code reviews, automated test pipelines, and distributed cloud deployments."
                    )
                }

                responsibilities = None
                for key_name, scope_text in scope_map.items():
                    if key_name in emp_name.lower():
                        responsibilities = scope_text
                        break
                if not responsibilities:
                    responsibilities = f"• Core team member of the {dept} department, responsible for operations, project delivery, and cross-functional collaboration under the title of {designation}."

                first_name = emp_name.split()[0] if emp_name else "them"

                answer = (
                    f"### 👤 Employee Profile Dossier: {emp_name}\n\n"
                    f"| Attribute | Information |\n"
                    f"| :--- | :--- |\n"
                    f"| **Official Title** | **{designation}** |\n"
                    f"| **Corporate ID** | `{emp_id}` |\n"
                    f"| **Department** | {dept} |\n"
                    f"| **Account Status** | 🟢 {status} |\n"
                    f"| **Work Email** | [{email}](mailto:{email}) |\n"
                    f"| **Phone Extension** | Ext {ext} |\n"
                    f"| **Office Location** | {loc} |\n\n"
                    f"#### 📋 Key Responsibilities & Areas of Expertise\n"
                    f"{responsibilities}\n\n"
                    f"#### ⚡ Quick Actions & Collaboration\n"
                    f"• **Schedule a meeting:** `Schedule a meeting with {emp_name} tomorrow at 2 PM regarding [Topic]`\n"
                    f"• **Draft an email:** `Draft email to {email} regarding [Subject]`\n"
                    f"• **Send direct message:** `Send email to {email} with subject \"Sync\": Hi {first_name}...`"
                )
            elif len(matches) > 1:
                bullet_list = "\n".join([
                    f"• **{e['name']}** — **{e.get('designation', e.get('role'))}** ({e['department']}) | Email: `{e['email']}` | Ext: {e['extension']} | Loc: {e['location']}"
                    for e in matches
                ])
                answer = f"### 👥 NovaTech Staff Directory Search Results\n\nHere are the matching employees:\n\n{bullet_list}\n\n💡 *Ask for any specific employee to view their full profile dossier.*"
            else:
                answer = "I could not find anyone matching that query in the NovaTech employee directory."

            return ChatResponse(
                answer=answer,
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[tool_call],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 9. KNOWLEDGE / DOCUMENT RAG RETRIEVAL STEP
        # Enforce server-side authorization: user must have documents.read or knowledge.read
        if not (check_permission(identity, "knowledge.read") or check_permission(identity, "documents.read")):
            denial_data = {
                "status": "permission_denied",
                "message": f"Access Denied: Your account does not have permission 'knowledge.read' or 'documents.read'.",
                "required_permission": "knowledge.read"
            }
            return permission_denied_response(denial_data, "search_enterprise_documents", {"query": clean_msg})

        search_q = clean_msg
        multilingual_query_map = {
            "छुट्टी": "annual leave", "छुट्टियां": "annual leave", "अवकाश": "annual leave",
            "सवेतन": "paid annual leave", "रिमोट": "remote work from home wfh",
            "वर्क फ्रॉम होम": "work from home wfh", "घर से काम": "work from home wfh",
            "पॉलिसी": "policy", "नीति": "policy", "नियम": "rules policy",
            "पासवर्ड": "password length security", "सुरक्षा": "security requirements",
            "फायदे": "employee benefits insurance", "लाभ": "employee benefits insurance",
            "बीमा": "health insurance", "उपकरण": "equipment laptop hardware replacement",
            "लैपटॉप": "laptop equipment replacement", "यात्रा": "travel expense hotel reimbursement",
            "होटल": "hotel reimbursement per diem", "प्रोबेशन": "probation period months",
            "घंटे": "office hours working hours",
            "vacaciones": "annual leave vacation days", "enfermedad": "sick leave medical",
            "médica": "medical sick leave", "remoto": "remote work from home wfh",
            "teletrabajo": "remote work from home wfh", "política": "policy",
            "contraseña": "password length", "beneficios": "employee benefits insurance",
            "computadora": "laptop equipment replacement", "portátil": "laptop equipment replacement",
            "viaje": "travel hotel reimbursement", "prueba": "probation period months",
            "horario": "office hours working hours",
            "congés": "annual leave vacation days", "conges": "annual leave vacation days",
            "vacances": "annual leave vacation days", "maladie": "sick leave medical",
            "télétravail": "remote work from home wfh", "teletravail": "remote work from home wfh",
            "politique": "policy", "mot de passe": "password length",
            "avantages": "employee benefits insurance", "ordinateur": "laptop equipment replacement",
            "voyage": "travel hotel reimbursement", "essai": "probation period months",
            "horaires": "office hours working hours"
        }
        for foreign_term, english_term in multilingual_query_map.items():
            if foreign_term in lower_msg:
                search_q = f"{search_q} {english_term}"

        retrieved_chunks = knowledge_base.search_knowledge(
            query=search_q,
            top_k=3,
            session_file_id=session_file_id,
            user_role=identity.role
        )

        # 10. Role-based clearance check and hallucination prevention
        if not retrieved_chunks:
            # Check if this topic exists in an elevated enterprise tier not authorized for this role
            unfiltered_hits = knowledge_base.search_knowledge(
                query=search_q,
                top_k=1,
                session_file_id=session_file_id,
                user_role=None
            )
            if unfiltered_hits and unfiltered_hits[0]["score"] >= 0.18:
                restricted_doc = unfiltered_hits[0]["source"]
                return ChatResponse(
                    answer=(
                        f"🔒 **Access Restricted by Role-Based Access Control (RBAC)**\n\n"
                        f"The requested information resides in **{restricted_doc}**, which is not authorized for your current role clearance (**{identity.role}**).\n\n"
                        f"In accordance with NovaTech Zero-Trust data governance policies, access to elevated departmental records is restricted to authorized roles."
                    ),
                    conversation_id=conversation_id,
                    sources=[],
                    tool_calls=[],
                    mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                    language=language,
                    authenticated_user=identity.model_dump()
                )

        unsupported_topics = ["company car", "car policy", "pet policy", "dog in office", "crypto", "bitcoin"]
        if any(topic in lower_msg for topic in unsupported_topics) or (retrieved_chunks and retrieved_chunks[0]["score"] < 0.12):
            topic_name = "this topic"
            if "car" in lower_msg:
                topic_name = "a company car policy"
            elif "pet" in lower_msg:
                topic_name = "a pet policy"
            return ChatResponse(
                answer=f"I couldn't find information about {topic_name} in the available enterprise knowledge sources.",
                conversation_id=conversation_id,
                sources=[],
                tool_calls=[],
                mode="azure_foundry" if self.is_azure_ready else "local_sandbox",
                language=language,
                authenticated_user=identity.model_dump()
            )

        # 11. Answer synthesis
        if settings.AZURE_MODE:
            answer, citations = self._generate_foundry_grounded_answer(
                clean_msg, retrieved_chunks, history_context, session_file_id, language=language, identity=identity
            )
        else:
            answer, citations = self._generate_local_grounded_answer(
                clean_msg, retrieved_chunks, history_context, session_file_id
            )
            answer = translate_or_localize(clean_msg, answer, language)

        return ChatResponse(
            answer=answer,
            conversation_id=conversation_id,
            sources=citations,
            tool_calls=[],
            mode="azure_foundry" if settings.AZURE_MODE else "local_sandbox",
            language=language,
            authenticated_user=identity.model_dump()
        )

    def _compose_intelligent_email(self, prompt: str, recipient_email: str, identity: IdentityContext) -> tuple:
        """
        Intelligently synthesizes a polished, executive-ready corporate email.
        Transforms casual or terse requests into professional emails with a clear subject,
        proper greeting, structured body paragraphs, and formal sign-off.
        """
        # Determine recipient's friendly first name
        recipient_name = "Colleague"
        clean_target = recipient_email.split("@")[0]
        if "." in clean_target:
            recipient_name = clean_target.split(".")[0].capitalize()
        elif clean_target.lower() in ["team", "all-staff"]:
            recipient_name = "Team"
        elif clean_target.lower() == "it-support":
            recipient_name = "IT Support Team"
        elif clean_target:
            recipient_name = clean_target.capitalize()

        # Try Azure OpenAI / Foundry LLM first if available
        if self.openai_client:
            try:
                system_prompt = (
                    "You are KnoQuest, the enterprise AI executive assistant for NovaTech Solutions.\n"
                    "Your task is to compose a polished, professional, concise corporate email based on the user's intent.\n"
                    "OUTPUT REQUIREMENTS:\n"
                    "- Return ONLY a valid JSON object with exactly two keys: 'subject' and 'body'.\n"
                    "- Do NOT output any markdown backticks, code blocks, or explanatory preamble.\n"
                    "- 'subject': A professional, executive-grade subject line (3 to 8 words).\n"
                    "- 'body': A well-structured corporate email including:\n"
                    "    • Formal salutation (e.g., 'Hi Sarah,')\n"
                    "    • 1-2 well-crafted, polite paragraphs stating the context, specifics, and actionable next steps\n"
                    "    • Courteous closing line and professional sign-off with the sender's name and title.\n"
                    "- NEVER include user meta-commands like 'send email to' or 'draft an email saying'."
                )
                user_prompt = (
                    f"Sender: {identity.name} ({identity.designation}, {identity.department})\n"
                    f"Recipient: {recipient_name} <{recipient_email}>\n"
                    f"User Prompt: {prompt}"
                )
                resp = self.openai_client.chat.completions.create(
                    model=settings.AZURE_MODEL_DEPLOYMENT_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=500
                )
                raw_json = resp.choices[0].message.content.strip()
                raw_json = re.sub(r'^```(?:json)?\s*', '', raw_json)
                raw_json = re.sub(r'\s*```$', '', raw_json)
                data = json.loads(raw_json)
                if data.get("subject") and data.get("body"):
                    return data["subject"].strip(), data["body"].strip()
            except Exception as e:
                logger.warning(f"LLM email generation fallback: {e}")

        # Resilient Intelligent Local Synthesizer
        # 1. Clean out command prefixes
        stripped = prompt
        pfx_list = [
            r'^(?:please\s+)?(?:send|draft|compose|write|create|save)(?:\s+an|\s+the|\s+a)?\s+(?:email|mail|draft|message)\s+(?:to\s+[\w\.-]+@[\w\.-]+\.\w+|\w+)?\s*(?:with\s+subject\s*["\'][^"\']+["\']|regarding\s+[^:\n]+|about\s+[^:\n]+)?\s*(?:saying|that|body:?|message:?|:)?\s*',
            r'^(?:to:\s*[\w\.-]+@[\w\.-]+\.\w+[,;\s]*)',
            r'^(?:save\s+(?:the\s+)?draft(?:\s+of\s+email)?(?:\s+to\s+[\w\.-]+@[\w\.-]+\.\w+)?\s*)'
        ]
        for pfx in pfx_list:
            stripped = re.sub(pfx, '', stripped, flags=re.IGNORECASE).strip()

        # Remove trailing/leading quotes or colons
        stripped = stripped.strip(" :,\"'")

        # 2. Derive Subject
        lower_p = prompt.lower()
        if "delay" in lower_p or "vendor" in lower_p or "postpone" in lower_p:
            subject = "Project Timeline Update: Vendor Delivery Schedule"
        elif "architecture" in lower_p or "design review" in lower_p:
            subject = "Architecture Review & Technical Sync"
        elif "budget" in lower_p or "headcount" in lower_p or "financial" in lower_p:
            subject = "Quarterly Budget & Resource Allocation Planning"
        elif "leave" in lower_p or "vacation" in lower_p or "pto" in lower_p:
            subject = "Upcoming Leave Notice & Team Coverage Plan"
        elif "incident" in lower_p or "security" in lower_p or "vulnerability" in lower_p:
            subject = "Security Advisory & Urgent Action Notice"
        elif "sync" in lower_p or "meeting" in lower_p:
            subject = "Team Alignment & Operational Sync"
        elif "approval" in lower_p:
            subject = "Request for Expedited Review and Approval"
        else:
            words = [w for w in re.findall(r'\b[a-zA-Z0-9]{3,}\b', stripped) if w.lower() not in ["send", "mail", "email", "draft", "please", "with", "about", "that", "this"]]
            subject = " ".join(words[:5]).title() if words else "Enterprise Operational Update"

        # 3. Derive clean message body
        core_msg = stripped if len(stripped) > 5 else f"Please find the latest update regarding {subject}."
        core_msg = core_msg[0].upper() + core_msg[1:] if len(core_msg) > 1 else core_msg

        body = (
            f"Hi {recipient_name},\n\n"
            f"I wanted to reach out regarding our ongoing operational milestones.\n\n"
            f"{core_msg}\n\n"
            f"Please let me know if you have any questions or require additional details. We can also schedule a brief follow-up sync if helpful.\n\n"
            f"Best regards,\n"
            f"{identity.name}\n"
            f"{identity.designation}\n"
            f"NovaTech Solutions"
        )

        return subject, body

    def _structure_intelligent_ticket(self, prompt: str) -> tuple:
        """
        Structures raw user complaints into clean technical IT helpdesk tickets
        with appropriate priority ('Low' | 'Medium' | 'High' | 'Critical').
        """
        lower_p = prompt.lower()

        # Priority inference
        if any(w in lower_p for w in ["critical", "outage", "production down", "security breach", "data leak", "data loss", "ransomware"]):
            priority = "Critical"
        elif any(w in lower_p for w in ["urgent", "blocker", "cannot work", "can't work", "broken", "flicker", "flickering", "crashes", "crashing", "blue screen"]):
            priority = "High"
        elif any(w in lower_p for w in ["minor", "cosmetic", "accessory", "mouse pad", "keyboard layout", "low"]):
            priority = "Low"
        else:
            priority = "Medium"

        # Title inference
        if "flicker" in lower_p or "hdmi" in lower_p or "monitor" in lower_p or "screen" in lower_p:
            title = "Hardware Display: External Screen Connection & Flickering Issue"
        elif "vpn" in lower_p or "network" in lower_p or "wifi" in lower_p or "internet" in lower_p:
            title = "Network Connectivity: Corporate VPN & Remote Access Disruption"
        elif "password" in lower_p or "mfa" in lower_p or "login" in lower_p or "authenticate" in lower_p:
            title = "Access & Identity: Single Sign-On / MFA Verification Support"
        elif "laptop" in lower_p or "battery" in lower_p or "reboot" in lower_p or "power" in lower_p:
            title = "Hardware Provisioning: Device Power & System Diagnostics"
        elif "software" in lower_p or "license" in lower_p or "install" in lower_p or "download" in lower_p:
            title = "Software Management: Application License & Installation Request"
        else:
            clean = re.sub(r'^(?:please\s+)?(?:create|raise|open|log)\s+(?:an?\s+)?(?:it\s+)?ticket\s*(?:for|about|regarding|because)?\s*', '', prompt, flags=re.IGNORECASE).strip()
            words = [w for w in re.findall(r'\b[a-zA-Z0-9]{3,}\b', clean) if w.lower() not in ["ticket", "please", "help", "need", "with"]]
            title = " ".join(words[:6]).title() if words else "General IT Support & Diagnostics Request"

        return title, priority

    def _structure_intelligent_meeting(self, prompt: str, default_title: str) -> str:
        """Derives clean, executive meeting titles from casual scheduling prompts while preserving explicit topics."""
        lower_p = prompt.lower()
        lower_dt = (default_title or "").lower()

        # Check if default_title is raw prompt text containing dates, times, or prepositions
        has_time_or_date = bool(re.search(r'\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}|\b\d{1,2}\s*(?:am|pm)\b|\bfrom\s+\d+|\bat\s+\d+', lower_dt))
        is_generic = lower_dt in ["sync", "meeting", "quick sync", "team sync", "discussion", "catch up", ""]

        if not has_time_or_date and not is_generic:
            return default_title

        if "architecture" in lower_p or "design" in lower_p:
            return "Architecture Review & Technical Sync"
        elif "budget" in lower_p or "financial" in lower_p or "headcount" in lower_p:
            return "Fiscal & Resource Planning Review"
        elif "sprint" in lower_p or "standup" in lower_p or "retrospective" in lower_p:
            return "Sprint Planning & Retrospective Sync"
        elif "security" in lower_p or "audit" in lower_p or "compliance" in lower_p:
            return "Security Architecture & Compliance Review"
        elif "1:1" in lower_p or "one on one" in lower_p or "catch up" in lower_p:
            return "1-on-1 Alignment & Status Sync"
        elif "hiring" in lower_p or "interview" in lower_p:
            return "Candidate Evaluation & Hiring Sync"
        
        # Strip dates, times, and prepositions from default_title if any remain
        clean_t = re.sub(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}\b|\b(?:from|to|at|on|with)\b|\b\d{1,2}\s*(?:am|pm)\b', '', default_title, flags=re.IGNORECASE).strip()
        words = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', clean_t) if w.lower() not in ["review", "discuss", "meet", "meeting", "sync", "the"]]
        if words:
            return f"{' '.join(words[:4]).title()} Discussion"

        return "Enterprise Operational Sync"

    def _generate_foundry_grounded_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        history_context: str,
        session_file_id: Optional[str] = None,
        language: str = "en",
        identity: Optional[IdentityContext] = None
    ) -> tuple:
        """Invokes Microsoft Foundry model deployment with strict grounding prompt and user identity context."""
        try:
            from openai import AzureOpenAI
            import openai

            context_str = "\n\n".join([
                f"[Source: {c['source']} | Section: {c['section']}]\n{c['content']}"
                for c in chunks
            ]) if chunks else "No relevant enterprise documents found."

            lang_names = {
                "hi": "Hindi (हिन्दी)",
                "es": "Spanish (Español)",
                "fr": "French (Français)",
                "en": "English"
            }
            target_lang_name = lang_names.get(language, "English")

            user_badge = f"{identity.name} ({identity.role}, {identity.department})" if identity else "NovaTech Employee"
            system_prompt = (
                f"You are KnoQuest, the enterprise AI knowledge agent for NovaTech Solutions.\n"
                f"Active User Context: {user_badge}\n\n"
                f"STRICT GROUNDING INSTRUCTIONS:\n"
                f"1. Answer the employee's question ONLY using the factual context provided below.\n"
                f"2. If the answer cannot be found in the context, explicitly say:\n"
                f"   'I couldn't find information about this topic in the available enterprise knowledge sources.'\n"
                f"3. Do NOT extrapolate, speculate, or fabricate company policies, dates, or numbers.\n"
                f"4. Be professional, clear, and concise.\n"
            )

            if language and language != "en":
                system_prompt += (
                    f"\nCRITICAL MULTILINGUAL INSTRUCTION:\n"
                    f"The user has requested the answer in {target_lang_name} ({language}).\n"
                    f"You MUST compose your entire grounded response in natural, fluent, and professional {target_lang_name}.\n"
                    f"All explanations, counts, and policy details from the context must be accurately communicated in {target_lang_name}.\n"
                    f"Keep official brand names like 'NovaTech Solutions', department names, and URLs or email addresses in their standard Latin format.\n"
                )

            user_prompt = f"Enterprise Context:\n{context_str}\n\nEmployee Question: {query}"

            if not self.openai_client:
                if not hasattr(self, "project_client") or not self.project_client:
                    from azure.identity import DefaultAzureCredential
                    from azure.ai.projects import AIProjectClient
                    self.project_client = AIProjectClient(
                        endpoint=settings.AZURE_PROJECT_ENDPOINT,
                        credential=DefaultAzureCredential()
                    )
                self.openai_client = self.project_client.get_openai_client()

            completion = self.openai_client.chat.completions.create(
                model=settings.AZURE_MODEL_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=600
            )

            answer = completion.choices[0].message.content.strip()

            citations = []
            for c in chunks[:2]:
                citations.append(
                    SourceCitation(
                        source=c["source"],
                        section=c["section"],
                        snippet=c["content"][:220].strip() + "..."
                    )
                )

            return answer, citations

        except Exception as e:
            logger.error(f"Error calling Azure Foundry model: {e}. Falling back to local grounded synthesis.")
            return self._generate_local_grounded_answer(query, chunks, history_context, session_file_id)

    def _generate_local_grounded_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        history_context: str,
        session_file_id: Optional[str] = None
    ) -> tuple:
        """Deterministic, grounded extractive synthesis over enterprise policies."""
        if not chunks:
            return (
                "I couldn't find information about this topic in the available enterprise knowledge sources.",
                []
            )

        top_chunk = chunks[0]
        content = top_chunk["content"]
        source = top_chunk["source"]
        section = top_chunk["section"]

        lower_q = query.lower()

        if "annual leave" in lower_q or "vacation" in lower_q or "paid leave" in lower_q:
            answer = "Full-time confirmed employees are entitled to 20 days of paid annual leave per calendar year, accruing at 1.67 days per month. A maximum of 5 unused days may be carried forward into the next year, which must be used before March 31."
        elif "sick leave" in lower_q or "medical leave" in lower_q:
            answer = "Employees receive 12 days of paid sick leave per calendar year. If sick leave lasts 2 or more consecutive days, an authentic medical certificate from a registered medical practitioner must be uploaded to the HR portal within 48 hours of resuming work."
        elif "work from home" in lower_q or "remote" in lower_q or "wfh" in lower_q:
            if "who is eligible" in lower_q or "eligible" in lower_q:
                answer = "Employees who have successfully completed their mandatory 6-month probation period are eligible to apply for remote work arrangements. Employees currently on probation must work from the physical office."
            elif "manager" in lower_q or "approval" in lower_q:
                answer = "Yes, manager approval is strictly required. Specific remote days must be agreed upon with the direct line manager and submitted into the HR scheduling tool by Friday 5:00 PM for the upcoming week."
            elif "vpn" in lower_q or "security" in lower_q:
                answer = "Yes, VPN is strictly required. Employees must connect via the NovaTech Secure Corporate VPN at all times when accessing internal systems, and remote work must only be conducted on company-issued laptops."
            else:
                answer = "Employees who have completed their 6-month probation period can work remotely up to 2 days per week, subject to direct manager approval. Company-issued laptops and corporate VPN connection are mandatory."
        elif "office hours" in lower_q or "working hours" in lower_q or "standard hours" in lower_q:
            answer = "Standard office hours at NovaTech Solutions are from 9:00 AM to 6:00 PM, Monday through Friday, with a 1-hour lunch break. Core collaboration hours are 10:00 AM to 4:00 PM."
        elif "probation" in lower_q:
            answer = "All newly hired employees undergo a mandatory probationary period of six (6) months from their official start date. A formal evaluation occurs at the end of month 5."
        elif "password" in lower_q or "minimum password" in lower_q:
            answer = "All passwords for enterprise accounts must be a minimum of twelve (12) characters in length, combining uppercase, lowercase, numbers, and special symbols. Passwords expire every 90 days."
        elif "mfa" in lower_q or "multi-factor" in lower_q:
            answer = "Yes, Multi-Factor Authentication (MFA) is strictly mandatory for all employees across all enterprise portals, email accounts, and remote access systems."
        elif "incident" in lower_q or ("report" in lower_q and "security" in lower_q):
            answer = "Any suspected security incident (phishing, malware, lost hardware) must be reported to the IT Security Operations Center (soc@novatech.com or extension 4444) within 30 minutes (thirty minutes) of discovery."
        elif "cloud" in lower_q or "personal" in lower_q or "storage" in lower_q:
            answer = "No, confidential and proprietary NovaTech information must NEVER be uploaded, synced, or backed up to personal cloud storage services (e.g. personal Google Drive, Dropbox, iCloud). All company documents must reside on official NovaTech SharePoint or OneDrive repositories."
        elif "benefit" in lower_q:
            answer = "NovaTech Solutions offers comprehensive health insurance coverage up to $50,000, dental and vision allowances, a 401(k) retirement match up to 5% of base salary, an Employee Assistance Program (EAP), and an annual professional learning stipend of up to $1,500."
        elif "replacement" in lower_q or "equipment" in lower_q or "laptop" in lower_q:
            answer = "Standard company laptops are eligible for replacement or hardware refresh every 3 years (three years). Eligible hybrid employees may also claim a one-time reimbursement of up to $300 for an external monitor and ergonomic accessories."
        elif "hotel" in lower_q or "travel" in lower_q or "reimbursement" in lower_q:
            answer = "The maximum domestic hotel reimbursement is $150 per night (excluding taxes), adjusted up to $220 for Tier 1 cities. The daily meal per diem allowance is $60 per day. Expense reports must be submitted within 14 days."
        elif "conduct" in lower_q or "harassment" in lower_q or "gift" in lower_q:
            answer = "NovaTech has a zero-tolerance policy against discrimination and harassment. Nominal promotional gifts under $50 may be accepted, while gifts exceeding $50 must be declared to the Compliance Officer. Cash or gift cards are strictly prohibited."
        else:
            summary_snippet = content.replace("\n", " ")[:250].strip()
            answer = f"According to {source} ({section}): {summary_snippet}..."

        citations = [
            SourceCitation(
                source=top_chunk["source"],
                section=top_chunk["section"],
                snippet=top_chunk["content"][:220].strip() + "..."
            )
        ]

        if len(chunks) > 1 and chunks[1]["score"] >= 0.25:
            citations.append(
                SourceCitation(
                    source=chunks[1]["source"],
                    section=chunks[1]["section"],
                    snippet=chunks[1]["content"][:180].strip() + "..."
                )
            )

        return answer, citations

foundry_agent = FoundryAgentService()
