import urllib.request
import json
import sys
import time

def test_stage1():
    print("==================================================")
    print("Testing Stage 1: KnoQuest Foundation & Day 1 Goal")
    print("==================================================")

    base_url = "http://127.0.0.1:8000"

    # 1. Test Health Endpoint
    print("\n[Step 1] Checking GET /api/health ...")
    try:
        req = urllib.request.Request(f"{base_url}/api/health", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as response:
            health_data = json.loads(response.read().decode())
            print(f"[PASS] Health Check: {health_data}")
            assert health_data["status"] == "ok"
    except Exception as e:
        print(f"[FAIL] Failed to connect to /api/health: {e}")
        return False

    # 2. Test Chat Endpoint with 'Hello'
    print("\n[Step 2] Checking POST /api/chat with 'Hello' (Day 1 Milestone) ...")
    payload = json.dumps({"message": "Hello"}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            chat_data = json.loads(response.read().decode())
            print("[PASS] Chat Response Received:")
            print(f"  Answer: {chat_data['answer']}")
            print(f"  Mode: {chat_data['mode']}")
            print(f"  Conversation ID: {chat_data['conversation_id']}")
            assert "Hello" in chat_data["answer"] or "KnoQuest" in chat_data["answer"]
            print("\n>>> DAY 1 MILESTONE ACHIEVED SUCCESSFULLY! <<<")
            return True
    except Exception as e:
        print(f"[FAIL] Failed to call /api/chat: {e}")
        return False

if __name__ == "__main__":
    success = test_stage1()
    sys.exit(0 if success else 1)
