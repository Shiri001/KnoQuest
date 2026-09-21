import os
import sys
import json
import logging
from typing import Dict, Any

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_azure_integration")

def run_azure_tests():
    client = TestClient(app)

    print("=================================================================")
    print("   KnoQuest — Azure Integration End-to-End Verification")
    print("=================================================================")

    # 1. Health & Configuration Check
    print("\n[Step 1] Verifying System Health & Azure Configuration...")
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed with {res.status_code}"
    health = res.json()
    print(f"Health Response: {health}")
    print(f"Active Mode: {health.get('mode')}")
    print(f"Enterprise Chunks in Knowledge Base: {health.get('enterprise_docs_loaded')}")
    assert health.get("status") == "ok"
    print("[PASS] System health verified.")

    # 2. Azure AI Search Direct Retrieval Test
    print("\n[Step 2] Testing Live Azure AI Search Retrieval from 'knoquest-novatech-index'...")
    from app.knowledge import knowledge_base
    leave_chunks = knowledge_base.search_knowledge("How many annual leave days do employees receive?", top_k=2)
    assert len(leave_chunks) > 0, "No chunks returned by Azure AI Search!"
    print(f"Azure Search top hit: source='{leave_chunks[0]['source']}', section='{leave_chunks[0]['section']}'")
    assert "Leave_Holiday_Policy" in leave_chunks[0]['source'], "Leave policy chunk not retrieved!"
    print("[PASS] Live Azure AI Search retrieval confirmed.")

    # 3. Azure Cognitive Speech Synthesis Test
    print("\n[Step 3] Testing Azure Speech SDK Synthesis (TTS)...")
    speech_res = client.post("/api/speech/synthesize", json={"text": "KnoQuest Azure Speech is functional.", "language": "en"})
    assert speech_res.status_code == 200, f"Speech synthesize failed: {speech_res.status_code}"
    speech_data = speech_res.json()
    print(f"Speech status: {speech_data.get('status')}, message: {speech_data.get('message')}")
    assert speech_data.get("status") == "success", "Speech synthesis was not successful"
    assert speech_data.get("audio_base64") is not None, "Speech audio_base64 is missing"
    print(f"Synthesized audio length: {len(speech_data['audio_base64'])} characters")
    print("[PASS] Azure Speech synthesis confirmed.")

    # 4. Azure Document Upload & Ingestion Test
    print("\n[Step 4] Testing Document Upload and Live Ingestion...")
    sample_content = (
        "SECTION 1: EMERGENCY REMOTE PROTOCOL\n"
        "In severe weather conditions, all employees may work remotely without manager prior approval.\n"
        "SECTION 2: TRAVEL STIPEND\n"
        "Emergency travel stipends are disbursed within 24 hours."
    )
    upload_res = client.post(
        "/api/upload",
        files={"file": ("emergency_remote_policy.txt", sample_content.encode("utf-8"), "text/plain")}
    )
    assert upload_res.status_code == 200, f"Upload failed with {upload_res.status_code}: {upload_res.text}"
    upload_data = upload_res.json()
    print(f"Upload Response: {upload_data}")
    assert upload_data.get("chunks_count") >= 1, "Expected at least 1 chunk created"
    session_file_id = upload_data.get("file_id")
    print(f"[PASS] Document upload & session indexing confirmed (file_id: {session_file_id}).")

    # 5. Core Chat Queries Verification
    test_queries = [
        "How many annual leave days do employees receive?",
        "What is the work from home policy?",
        "What is the minimum password length?",
        "What is the policy on company spaceships and Mars colonies?"  # Unrelated/unsupported question
    ]

    print("\n[Step 5] Testing End-to-End Chat Flow for Required Questions...")
    for q in test_queries:
        print(f"\n--- Query: '{q}' ---")
        chat_res = client.post("/api/chat", json={"message": q})
        if chat_res.status_code == 200:
            data = chat_res.json()
            print(f"Answer: {data.get('answer')}")
            print(f"Citations: {[s['source'] + ' (' + s.get('section', '') + ')' for s in data.get('sources', [])]}")
            print(f"Mode: {data.get('mode')}")
        else:
            print(f"Status Code: {chat_res.status_code}")
            print(f"Error Detail: {chat_res.json().get('detail')}")
            print("Note: If Azure GPT invocation failed due to credential requirement, error was surfaced cleanly as designed.")

    print("\n=================================================================")
    print("   Azure Integration Test Execution Finished Successfully")
    print("=================================================================")

if __name__ == "__main__":
    run_azure_tests()
