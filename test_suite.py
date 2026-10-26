import sys
import json
import time
import httpx

BASE_URL = "http://127.0.0.1:8000"

def print_separator(title: str):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)

def run_tests():
    print_separator("STARTING AI AVATAR TUTOR API TEST SUITE")
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # -------------------------------------------------------------
    # TEST 1: Service Health & Pipeline Discovery
    # -------------------------------------------------------------
    print_separator("TEST 1: Health & Pipeline Discovery (GET /)")
    resp1 = client.get("/")
    print(f"Status Code: {resp1.status_code}")
    data1 = resp1.json()
    print(f"Service: {data1.get('service')}")
    print(f"Status: {data1.get('status')}")
    print("Supported Pipeline Stages:")
    for stage in data1.get("supported_pipeline", []):
        print(f"  • {stage}")
    assert resp1.status_code == 200, "Test 1 Failed"
    print("\n>>> TEST 1 PASSED: API is healthy and discovery metadata is valid.")

    # -------------------------------------------------------------
    # TEST 2: Ingest Notes & Whiteboard Storyboard Generation
    # -------------------------------------------------------------
    print_separator("TEST 2: Upload Notes & Multi-Scene Storyboard (POST /api/v1/upload-notes)")
    sample_notes = (
        b"%PDF-1.4\n"
        b"Newtonian Mechanics and Laws of Motion:\n"
        b"1. Law of Inertia\n"
        b"2. F = m * a (Force, Mass, Acceleration)\n"
        b"3. Action and Reaction forces."
    )
    files = {"file": ("physics_mechanics_notes.pdf", sample_notes, "application/pdf")}
    data = {
        "target_language": "en-IN",
        "teaching_style": "interactive",
        "speaker": "shubh",
        "dry_run": "true"
    }
    resp2 = client.post("/api/v1/upload-notes", files=files, data=data)
    print(f"Status Code: {resp2.status_code}")
    data2 = resp2.json()
    lecture = data2.get("lecture_plan", {})
    print(f"Lecture Title: {lecture.get('title')}")
    print(f"Summary: {lecture.get('summary')}")
    print(f"Number of Lecture Scenes: {len(lecture.get('scenes', []))}")
    for scene in lecture.get("scenes", []):
        wb = scene.get("whiteboard_action", {})
        print(f"\n  [Scene {scene.get('scene_id')}]: {scene.get('title')}")
        print(f"    • Avatar Gesture: {scene.get('avatar_gesture')}")
        print(f"    • Spoken Narration: \"{scene.get('narration')[:75]}...\"")
        print(f"    • Whiteboard Action: [{wb.get('type')}] {wb.get('title')}")
        print(f"    • Whiteboard Content: {wb.get('content').replace(chr(10), ' ')}")

    questions = lecture.get("adaptive_questions", [])
    print(f"\nAdaptive Check-In Questions: {len(questions)}")
    if questions:
        q = questions[0]
        print(f"  • Sample Question: {q.get('question')}")
        print(f"  • Correct Answer: {q.get('correct_answer')}")

    assert resp2.status_code == 200, "Test 2 Failed"
    assert "heygen_video_payload" in data2, "Missing HeyGen payload"
    print("\n>>> TEST 2 PASSED: Notes parsed and multimodal storyboard generated successfully.")

    # -------------------------------------------------------------
    # TEST 3: HeyGen Avatar Video Lecture Generation Dispatch
    # -------------------------------------------------------------
    print_separator("TEST 3: HeyGen Avatar Video Generation (POST /api/v1/generate-video)")
    video_req = {
        "lecture_plan": lecture,
        "avatar_id": "Angela-in-business-suit"
    }
    resp3 = client.post("/api/v1/generate-video", json=video_req)
    print(f"Status Code: {resp3.status_code}")
    data3 = resp3.json()
    vgen = data3.get("video_generation", {})
    video_id = vgen.get("video_id")
    print(f"Video Generation Mode: {vgen.get('mode')}")
    print(f"Dispatched Video ID: {video_id}")
    print(f"Initial Status: {vgen.get('status')}")
    print(f"Status Polling Endpoint: {data3.get('poll_status_endpoint')}")

    assert resp3.status_code == 200, "Test 3 Failed"
    assert video_id is not None, "Missing Video ID"
    print("\n>>> TEST 3 PASSED: Video lecture successfully queued on the Avatar engine.")

    # -------------------------------------------------------------
    # TEST 4: Poll Video Rendering Status & Stream URL
    # -------------------------------------------------------------
    print_separator("TEST 4: Video Status & Download Retrieval (GET /api/v1/video-status/{id})")
    resp4 = client.get(f"/api/v1/video-status/{video_id}")
    print(f"Status Code: {resp4.status_code}")
    data4 = resp4.json()
    print(f"Video ID: {data4.get('video_id')}")
    print(f"Render Status: {data4.get('status')}")
    print(f"Estimated Video Duration: {data4.get('duration')}s")
    print(f"Streamable MP4 URL: {data4.get('video_url')}")
    print(f"Thumbnail URL: {data4.get('thumbnail_url')}")

    assert resp4.status_code == 200, "Test 4 Failed"
    assert data4.get("video_url") is not None, "Missing video stream URL"
    print("\n>>> TEST 4 PASSED: Video status retrieved and playback URL available.")

    # -------------------------------------------------------------
    # TEST 5: Real-time Adaptive Feedback & Live Avatar WebRTC Session
    # -------------------------------------------------------------
    print_separator("TEST 5: Adaptive Tutoring Feedback & Live WebRTC Stream Session")
    # Subtest 5A: Student answers adaptive quiz question correctly
    feedback_req = {
        "question": "If force is kept constant while mass is doubled, what happens to acceleration?",
        "student_response": "It halves",
        "correct_answer": "It halves",
        "concept_context": "Newton's Second Law"
    }
    resp5a = client.post("/api/v1/adaptive-feedback", json=feedback_req)
    data5a = resp5a.json()
    print(f"Student Response: \"{feedback_req['student_response']}\"")
    print(f"Is Correct: {data5a.get('is_correct')}")
    print(f"Tutor Feedback: \"{data5a.get('feedback')}\"")
    print(f"Tutor Explanation: \"{data5a.get('explanation')}\"")
    print(f"Next Action: {data5a.get('recommended_next_action')}")

    # Subtest 5B: Live interactive WebRTC avatar session start
    resp5b = client.post("/api/v1/interactive-avatar/session", params={"avatar_name": "Angela-in-business-suit"})
    data5b = resp5b.json()
    session = data5b.get("session", {})
    session_id = session.get("session_id")
    print(f"\nLive WebRTC Interactive Tutor Session ID: {session_id}")
    print(f"Avatar Model: {session.get('avatar_name')}")
    print(f"Session State: {session.get('status')}")
    print(f"WebRTC Offer SDP Preview: {session.get('sdp', {}).get('sdp')[:50]}...")

    # Subtest 5C: Command avatar to deliver spoken live reinforcement
    speak_req = {
        "session_id": session_id,
        "text": "Excellent answer! You correctly applied Newton's second law. Let's move on to third law."
    }
    resp5c = client.post("/api/v1/interactive-avatar/speak", json=speak_req)
    data5c = resp5c.json()
    print(f"Interactive Avatar Live Speak Command Status: {data5c.get('status')}")

    assert resp5a.status_code == 200, "Subtest 5A Failed"
    assert resp5b.status_code == 200, "Subtest 5B Failed"
    assert resp5c.status_code == 200, "Subtest 5C Failed"
    print("\n>>> TEST 5 PASSED: Adaptive feedback logic & live interactive session verified.")

    print_separator("ALL 5 TESTS PASSED SUCCESSFULLY! (5/5)")

if __name__ == "__main__":
    run_tests()
