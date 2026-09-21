import urllib.request
import urllib.parse
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def get_json(endpoint: str) -> dict:
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode())

def post_json(endpoint: str, data: dict) -> dict:
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode())

def run_stage4_tests():
    print("==================================================")
    print("Testing Stage 4: MCP Tools & Agent Tool Invocation")
    print("==================================================")

    # 1. Test IT Ticket Direct API Endpoint
    print("\n[Test 1] Testing POST /api/tools/ticket (Direct Tool Endpoint)...")
    ticket_payload = {
        "issue": "External monitor flickering in HQ meeting room 3B",
        "priority": "High",
        "user_name": "Shiwang Sharma",
        "department": "Engineering"
    }
    ticket_res = post_json("/api/tools/ticket", ticket_payload)
    print(f"Created Ticket: {ticket_res.get('ticket_id')}, Status: {ticket_res.get('status')}")
    assert ticket_res.get("ticket_id") is not None and "IT-" in ticket_res["ticket_id"], "Ticket ID not generated!"
    assert ticket_res.get("priority") == "High", "Ticket priority not preserved!"
    print("[PASS] Test 1: Direct IT ticket creation endpoint verified.")

    # 2. Test Listing IT Tickets
    print("\n[Test 2] Testing GET /api/tools/tickets (List Tickets)...")
    list_res = get_json("/api/tools/tickets")
    tickets = list_res.get("tickets", [])
    print(f"Total Tickets in System: {len(tickets)}")
    assert len(tickets) > 0, "No tickets found in ticket store!"
    assert any(t.get("ticket_id") == ticket_res["ticket_id"] for t in tickets), "Newly created ticket not listed!"
    print("[PASS] Test 2: IT tickets listing verified.")

    # 3. Test Employee Directory Direct API Endpoint
    print("\n[Test 3] Testing GET /api/tools/directory (Employee Directory Search)...")
    dir_res = get_json("/api/tools/directory?q=CISO")
    employees = dir_res.get("employees", [])
    print(f"Employees Found for query 'CISO': {len(employees)}")
    assert len(employees) > 0, "No employees returned for CISO search!"
    assert any("David Kumar" in e["name"] for e in employees), "David Kumar (CISO) not returned!"
    print(f"Found: {employees[0]['name']} — {employees[0]['role']} ({employees[0]['email']})")
    print("[PASS] Test 3: Direct employee directory endpoint verified.")

    # 4. Test Conversational Agent Tool Calling: IT Ticket
    print("\n[Test 4] Conversational Agent Tool Invocation: IT Ticket Request...")
    chat_ticket_q = "My keyboard spilled with water and stopped working. Please raise an IT ticket."
    chat_res = post_json("/api/chat", {"message": chat_ticket_q})
    print(f"Answer: {chat_res.get('answer')[:90]}...")
    tool_calls = chat_res.get("tool_calls", [])
    assert len(tool_calls) > 0, "Tool calls missing in chat response!"
    assert tool_calls[0]["tool_name"] == "create_it_ticket", f"Unexpected tool invoked: {tool_calls[0]['tool_name']}"
    assert "ticket_id" in tool_calls[0]["result"], "ticket_id missing in tool result!"
    print(f"[PASS] Test 4: Natural language IT ticket tool call verified ({tool_calls[0]['result']['ticket_id']}).")

    # 5. Test Conversational Agent Tool Calling: Employee Directory Search
    print("\n[Test 5] Conversational Agent Tool Invocation: Directory Lookup...")
    chat_dir_q = "Who is the Vice President of People & HR?"
    chat_dir_res = post_json("/api/chat", {"message": chat_dir_q})
    print(f"Answer:\n{chat_dir_res.get('answer')}")
    dir_tool_calls = chat_dir_res.get("tool_calls", [])
    assert len(dir_tool_calls) > 0, "Directory tool call not triggered in conversational agent!"
    assert dir_tool_calls[0]["tool_name"] == "search_employee_directory", f"Unexpected tool invoked: {dir_tool_calls[0]['tool_name']}"
    assert "Sarah Jenkins" in chat_dir_res["answer"], "Sarah Jenkins not mentioned in directory response!"
    print("[PASS] Test 5: Natural language employee directory tool call verified.")

    print("\n==================================================")
    print(">>> STAGE 4 COMPLETED & 100% VERIFIED! <<<")
    print("==================================================")
    return True

if __name__ == "__main__":
    success = run_stage4_tests()
    sys.exit(0 if success else 1)
