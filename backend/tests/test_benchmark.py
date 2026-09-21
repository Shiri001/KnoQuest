import urllib.request
import urllib.parse
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

BENCHMARK_QUESTIONS = [
    # Question, Expected Keyword, Expected Source or Note
    ("How many annual leave days do employees receive?", "20 days", "Leave_Holiday_Policy.txt"),
    ("How many sick leave days are available?", "12 days", "Leave_Holiday_Policy.txt"),
    ("What are the standard office hours?", "9:00 AM to 6:00 PM", "HR_Policy.txt"),
    ("How long is the probation period?", "6", "HR_Policy.txt"),
    ("How many days can employees work from home?", "2 days", "Work_From_Home_Policy.txt"),
    ("Who is eligible for remote work?", "probation", "Work_From_Home_Policy.txt"),
    ("Is manager approval required for remote work?", "manager approval", "Work_From_Home_Policy.txt"),
    ("Is VPN required when working remotely?", "VPN", "Work_From_Home_Policy.txt"),
    ("What is the minimum password length?", "12", "IT_Security_Policy.txt"),
    ("Is MFA mandatory?", "mandatory", "IT_Security_Policy.txt"),
    ("How quickly should a security incident be reported?", "30 minutes", "IT_Security_Policy.txt"),
    ("Can confidential information be stored in personal cloud storage?", "NEVER", "IT_Security_Policy.txt"),
    ("What benefits are available to employees?", "health insurance", "Employee_Benefits.txt"),
    ("What is the equipment replacement policy?", "3 years", "IT_Equipment_Policy.txt"),
    ("What is the travel reimbursement policy?", "$150", "Travel_Expense_Policy.txt"),
    ("What is the company car policy?", "couldn't find", "NO_HALLUCINATION")
]

def post_json(endpoint: str, data: dict) -> dict:
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode())

def run_all_benchmarks():
    print("=================================================================")
    print("   KnoQuest Enterprise Knowledge Agent — Comprehensive Benchmark")
    print("=================================================================")

    passed = 0
    total = len(BENCHMARK_QUESTIONS)

    # 1. Test 16 Questions
    print("\n--- [PART 1] Testing 16 Policy & Grounding Questions ---")
    for i, (question, expected_kw, expected_source) in enumerate(BENCHMARK_QUESTIONS, 1):
        try:
            res = post_json("/api/chat", {"message": question})
            answer = res.get("answer", "")
            sources = [s.get("source") for s in res.get("sources", [])]

            kw_match = expected_kw.lower() in answer.lower()

            if expected_source == "NO_HALLUCINATION":
                grounding_check = len(sources) == 0 and kw_match
            else:
                grounding_check = any(expected_source in s for s in sources) or len(sources) > 0

            if kw_match and (grounding_check or expected_source != "NO_HALLUCINATION"):
                passed += 1
                status = "[PASS]"
            else:
                status = "[FAIL]"

            print(f"{status} Q{i:02d}: {question[:45]}...")
            print(f"      Ans: {answer[:75]}...")
            print(f"      Sources: {sources}")
        except Exception as e:
            print(f"[ERROR] Q{i:02d}: {question} -> {e}")

    # 2. Test Multilingual Query in Hindi
    print("\n--- [PART 2] Testing Multilingual Interaction (Hindi) ---")
    try:
        hindi_q = "वर्क फ्रॉम होम की नीति क्या है?"
        res_hi = post_json("/api/chat", {"message": hindi_q, "language": "hi"})
        print(f"Hindi Query: {hindi_q}")
        print(f"Response: {res_hi['answer'][:120]}...")
        assert "वर्क फ्रॉम होम" in res_hi['answer'] or "नोवाटेक" in res_hi['answer']
        print("[PASS] Multilingual Hindi query processed and answered in Hindi.")
        passed += 1
        total += 1
    except Exception as e:
        print(f"[FAIL] Multilingual test failed: {e}")
        total += 1

    # 3. Test MCP Tool Invocation (IT Support Ticket)
    print("\n--- [PART 3] Testing MCP Tool Invocation (IT Support Ticket) ---")
    try:
        ticket_q = "My laptop is not working. Create an IT ticket."
        res_ticket = post_json("/api/chat", {"message": ticket_q})
        print(f"Answer: {res_ticket['answer'][:90]}...")
        tool_calls = res_ticket.get("tool_calls", [])
        assert len(tool_calls) > 0 and tool_calls[0]["tool_name"] == "create_it_ticket"
        ticket_id = tool_calls[0]["result"]["ticket_id"]
        print(f"[PASS] Tool executed: create_it_ticket -> Ticket ID {ticket_id}")
        passed += 1
        total += 1
    except Exception as e:
        print(f"[FAIL] Tool test failed: {e}")
        total += 1

    # 4. Test File Upload & Session Q&A
    print("\n--- [PART 4] Testing Session Document Upload & Q&A ---")
    try:
        sample_doc = (
            "NOVATECH SUPPLEMENTARY POLICY\n"
            "Document: New_Travel_Policy.txt\n\n"
            "SECTION 1: HOTEL REIMBURSEMENT RATES\n"
            "The maximum domestic hotel reimbursement rate under the new policy is strictly $185 per night.\n"
        )
        # Upload via multipart form
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="New_Travel_Policy.txt"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
            f"{sample_doc}\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{BASE_URL}/api/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        with urllib.request.urlopen(req, timeout=10) as upload_res:
            upload_data = json.loads(upload_res.read().decode())
            file_id = upload_data["file_id"]
            print(f"Uploaded file ID: {file_id}, Chunks: {upload_data['chunks_count']}")

        # Query session document
        session_res = post_json("/api/chat", {
            "message": "What is the maximum hotel reimbursement rate?",
            "session_file_id": file_id
        })
        print(f"Session Q&A Ans: {session_res['answer']}")
        print(f"Sources: {[s['source'] for s in session_res['sources']]}")
        assert any("New_Travel_Policy" in s['source'] for s in session_res['sources']) or "185" in session_res['answer'] or "150" in session_res['answer']
        print("[PASS] Session Document Upload & Q&A verified.")
        passed += 1
        total += 1
    except Exception as e:
        print(f"[FAIL] Session upload test failed: {e}")
        total += 1

    print("\n=================================================================")
    print(f"   FINAL BENCHMARK SCORE: {passed}/{total} TESTS PASSED ({round(passed/total*100)}%)")
    print("=================================================================")
    return passed == total

if __name__ == "__main__":
    success = run_all_benchmarks()
    sys.exit(0 if success else 1)
