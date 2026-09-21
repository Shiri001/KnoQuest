import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def post_chat(message: str, conversation_id: str = None) -> dict:
    payload = json.dumps({"message": message, "conversation_id": conversation_id}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode())

def get_health() -> dict:
    req = urllib.request.Request(f"{BASE_URL}/api/health", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as res:
        return json.loads(res.read().decode())

def run_stage2_tests():
    print("==================================================")
    print("Testing Stage 2: Knowledge Base, RAG & Anti-Hallucination")
    print("==================================================")

    # 1. Health check & Docs count
    print("\n[Test 1] Health Check & Enterprise Document Indexing...")
    health = get_health()
    print(f"Health Status: {health['status']}")
    print(f"Enterprise Chunks Loaded: {health['enterprise_docs_loaded']}")
    assert health['enterprise_docs_loaded'] > 0, "No enterprise chunks loaded!"
    print("[PASS] Test 1: Knowledge chunks indexed successfully.")

    # 2. Annual Leave Query (RAG + Citation)
    print("\n[Test 2] Query: 'How many annual leave days do employees receive?'")
    res = post_chat("How many annual leave days do employees receive?")
    print(f"Answer: {res['answer']}")
    print(f"Sources: {[s['source'] for s in res['sources']]}")
    assert ("20" in res['answer'] and "day" in res['answer'].lower()) or "twenty" in res['answer'].lower(), "Answer did not state 20 days"
    assert any("Leave_Holiday_Policy" in s['source'] or "HR_Policy" in s['source'] for s in res['sources']), "Source missing!"
    print("[PASS] Test 2: Annual leave RAG & citation verified.")

    # 3. Work From Home Policy
    print("\n[Test 3] Query: 'What is the work from home policy?'")
    res = post_chat("What is the work from home policy?")
    print(f"Answer: {res['answer']}")
    print(f"Sources: {[s['source'] for s in res['sources']]}")
    assert ("2" in res['answer'] and "day" in res['answer'].lower()) or "two" in res['answer'].lower(), "Answer did not state 2 remote days"
    assert any("Work_From_Home_Policy" in s['source'] for s in res['sources']), "Source missing!"
    print("[PASS] Test 3: WFH policy RAG & citation verified.")

    # 4. IT Security Minimum Password
    print("\n[Test 4] Query: 'What is the minimum password length?'")
    res = post_chat("What is the minimum password length?")
    print(f"Answer: {res['answer']}")
    print(f"Sources: {[s['source'] for s in res['sources']]}")
    assert "12" in res['answer'], "Answer did not state 12 characters"
    assert any("IT_Security_Policy" in s['source'] for s in res['sources']), "Source missing!"
    print("[PASS] Test 4: IT Security password length verified.")

    # 5. Anti-Hallucination Guardrail: Company Car Policy
    print("\n[Test 5] Query: 'What is the company car policy?' (Anti-Hallucination Test)")
    res = post_chat("What is the company car policy?")
    print(f"Answer: {res['answer']}")
    print(f"Sources Count: {len(res['sources'])}")
    assert "couldn't find" in res['answer'].lower() or "not found" in res['answer'].lower(), "Failed to prevent hallucination!"
    assert len(res['sources']) == 0, "Citations returned for nonexistent policy!"
    print("[PASS] Test 5: Anti-hallucination successfully prevented policy fabrication.")

    # 6. IT Ticket Tool Invocation
    print("\n[Test 6] Tool Query: 'My laptop screen is broken. Please create an IT ticket.'")
    res = post_chat("My laptop screen is broken. Please create an IT ticket.")
    print(f"Answer:\n{res['answer']}")
    print(f"Tool Calls: {res.get('tool_calls')}")
    assert len(res.get('tool_calls', [])) > 0, "Tool call not triggered!"
    assert "IT-1024" in res['answer'] or "IT-" in res['answer'], "Ticket ID not generated!"
    print("[PASS] Test 6: IT Ticket Tool invocation verified.")

    print("\n==================================================")
    print(">>> STAGE 2 COMPLETED & 100% VERIFIED! <<<")
    print("==================================================")
    return True

if __name__ == "__main__":
    success = run_stage2_tests()
    sys.exit(0 if success else 1)
