import urllib.request
import urllib.parse
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def post_json(endpoint: str, data: dict) -> dict:
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode())

def run_stage3_tests():
    print("==================================================")
    print("Testing Stage 3: Upload, Multilingual & Speech")
    print("==================================================")

    # 1. Test Dynamic File Upload (TXT Document)
    print("\n[Test 1] Testing Document Upload (POST /api/upload)...")
    sample_doc = (
        "NOVATECH REMOTE WORK SUPPLEMENT 2026\n"
        "Document: Remote_Stipend_Policy.txt\n\n"
        "SECTION 1: HOME OFFICE HIGH-SPEED INTERNET STIPEND\n"
        "Full-time approved remote employees receive an internet reimbursement subsidy of $75 per month.\n"
    )
    boundary = "----WebKitFormBoundaryKnoQuestStage3"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="Remote_Stipend_Policy.txt"\r\n'
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
        file_id = upload_data.get("file_id")
        chunks_count = upload_data.get("chunks_count", 0)
        print(f"File ID: {file_id}, Chunks: {chunks_count}")
        assert file_id is not None, "file_id missing in upload response!"
        assert chunks_count > 0, "No chunks generated for uploaded document!"
    print("[PASS] Test 1: Document uploaded and indexed successfully.")

    # 2. Test Grounded Session Q&A over Uploaded File
    print("\n[Test 2] Testing Grounded Q&A over Uploaded Document...")
    session_res = post_json("/api/chat", {
        "message": "What is the monthly internet reimbursement subsidy?",
        "session_file_id": file_id
    })
    print(f"Answer: {session_res['answer']}")
    print(f"Sources: {[s['source'] for s in session_res['sources']]}")
    assert "75" in session_res['answer'], "Answer did not retrieve $75 subsidy from uploaded document!"
    assert any("Remote_Stipend_Policy" in s['source'] for s in session_res['sources']), "Uploaded document citation missing!"
    print("[PASS] Test 2: Session document grounded Q&A verified.")

    # 3. Test Multilingual Localization (Hindi, Punjabi, Spanish, French)
    print("\n[Test 3] Testing Multilingual Responses (Hindi, Punjabi, Spanish, French)...")
    
    # 3a. Hindi
    res_hi = post_json("/api/chat", {
        "message": "वर्क फ्रॉम होम की नीति क्या है?",
        "language": "hi"
    })
    print(f"Hindi Response: {res_hi['answer'][:80]}...")
    assert "वर्क फ्रॉम होम" in res_hi['answer'] or "नोवाटेक" in res_hi['answer'], "Hindi response not localized!"

    # 3b. Punjabi
    res_pa = post_json("/api/chat", {
        "message": "ਵਰਕ ਫਰਾਮ ਹੋਮ ਪਾਲਿਸੀ ਕੀ ਹੈ?",
        "language": "pa"
    })
    print(f"Punjabi Response: {res_pa['answer'][:80]}...")
    assert any(w in res_pa['answer'] for w in ["ਨੋਵਾਟੈਕ", "ਘਰ ਤੋਂ ਕੰਮ", "ਵਰਕ ਫਰਾਮ ਹੋਮ", "ਪਾਲਿਸੀ", "ਰਿਮੋਟ"]), "Punjabi response not localized!"

    # 3c. Spanish
    res_es = post_json("/api/chat", {
        "message": "¿Cuál es la política de vacaciones anuales?",
        "language": "es"
    })
    print(f"Spanish Response: {res_es['answer'][:80]}...")
    assert "vacaciones" in res_es['answer'].lower() or "20 días" in res_es['answer'].lower(), "Spanish response not localized!"

    # 3d. French
    res_fr = post_json("/api/chat", {
        "message": "Quelle est la politique de télétravail?",
        "language": "fr"
    })
    print(f"French Response: {res_fr['answer'][:80]}...")
    assert "télétravailler" in res_fr['answer'].lower() or "novatech" in res_fr['answer'].lower(), "French response not localized!"
    print("[PASS] Test 3: Multilingual localization verified in 4 languages.")

    # 4. Test Speech Transcription Endpoint
    print("\n[Test 4] Testing Speech Transcription Endpoint (POST /api/speech/transcribe)...")
    dummy_audio = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    speech_boundary = "----WebKitFormBoundarySpeechTest"
    speech_body = (
        f"--{speech_boundary}\r\n"
        f'Content-Disposition: form-data; name="audio"; filename="audio.wav"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode("utf-8") + dummy_audio + f"\r\n--{speech_boundary}--\r\n".encode("utf-8")

    speech_req = urllib.request.Request(
        f"{BASE_URL}/api/speech/transcribe",
        data=speech_body,
        headers={"Content-Type": f"multipart/form-data; boundary={speech_boundary}"}
    )
    with urllib.request.urlopen(speech_req, timeout=10) as speech_res:
        speech_data = json.loads(speech_res.read().decode())
        print(f"Transcribed Text: '{speech_data.get('text')}'")
        assert "text" in speech_data, "Text field missing in speech transcription response!"
        assert len(speech_data["text"]) > 0, "Empty speech transcription returned!"
    print("[PASS] Test 4: Speech transcription endpoint verified.")

    print("\n==================================================")
    print(">>> STAGE 3 COMPLETED & 100% VERIFIED! <<<")
    print("==================================================")
    return True

if __name__ == "__main__":
    success = run_stage3_tests()
    sys.exit(0 if success else 1)
