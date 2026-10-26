import os
import shutil
import tempfile
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sarvamai.core.api_error import ApiError

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

from app.sarvam_service import (
    digitize_notes,
    generate_lecture_script,
    synthesize_narration_audio,
    get_sarvam_client
)
from app.avatar_engine import build_heygen_video_payload, create_interactive_avatar_session_config
from app.heygen_service import heygen_service

app = FastAPI(
    title="AI Avatar Tutor API",
    description="Multimodal AI tutor that converts written notes into lifelike avatar video lectures with interactive whiteboard explanations.",
    version="1.0.0"
)

# Enable CORS for frontend / web integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AdaptiveFeedbackRequest(BaseModel):
    question: str
    student_response: str
    correct_answer: str
    concept_context: Optional[str] = ""

class GenerateVideoRequest(BaseModel):
    lecture_plan: Optional[dict] = None
    heygen_payload: Optional[dict] = None
    avatar_id: Optional[str] = "Angela-in-business-suit"

class InteractiveSpeakRequest(BaseModel):
    session_id: str
    text: str

def _get_default_lecture_plan(filename: str):
    return {
        "title": f"Mastery Lecture: {filename.replace('.pdf', '').replace('_', ' ').title()}",
        "summary": "Step-by-step breakdown of fundamental concepts, mathematical formulations, and interactive check-ins.",
        "scenes": [
            {
                "scene_id": 1,
                "title": "Welcome & Concept Foundations",
                "narration": f"Hello! Welcome to your personalized tutoring session. Today we are exploring the core concepts from your notes on {filename}.",
                "avatar_gesture": "warm_welcome",
                "whiteboard_action": {
                    "type": "bullet_points",
                    "title": "Core Overview",
                    "content": "• Concept Definitions\n• Equations & Physical Meaning\n• Practical Problem Walkthrough",
                    "highlight": "Concept Definitions"
                },
                "duration_sec": 15
            },
            {
                "scene_id": 2,
                "title": "Mathematical Derivation & Board Analysis",
                "narration": "Notice the relationship shown on the whiteboard. When external parameters vary, the resultant response changes proportionally.",
                "avatar_gesture": "pointing_left",
                "whiteboard_action": {
                    "type": "formula",
                    "title": "Governing Equation",
                    "content": "F = m · a\n\n[Δp / Δt = F_net]",
                    "highlight": "F = m · a"
                },
                "duration_sec": 20
            }
        ],
        "adaptive_questions": [
            {
                "id": 1,
                "question": "If force is kept constant while mass is doubled, what happens to acceleration?",
                "options": ["It doubles", "It halves", "It quadruples", "No change"],
                "correct_answer": "It halves",
                "explanation": "Newton's Second Law dictates a = F/m, meaning acceleration is inversely proportional to mass."
            }
        ]
    }

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    """
    Content-negotiated endpoint:
    - Browsers (sending Accept: text/html) receive the interactive Avatar Tutor Studio UI.
    - API clients (curl, httpx, Python) receive JSON service discovery metadata.
    """
    accept = request.headers.get("accept", "")
    html_file = TEMPLATES_DIR / "index.html"

    # Browser request -> return user-friendly HTML Studio
    if "text/html" in accept and html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))

    # API client request -> return JSON
    return JSONResponse(content=_get_service_metadata())

@app.get("/ui", response_class=HTMLResponse)
def user_interface():
    """Direct route to the Avatar Tutor Web Studio."""
    html_file = TEMPLATES_DIR / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>Studio UI template not found</h2>")

@app.get("/api/v1/health")
def health_check():
    """Dedicated JSON service health and capability discovery."""
    return _get_service_metadata()

def _get_service_metadata():
    return {
        "service": "AI Avatar Tutor API",
        "status": "online",
        "ui_url": "http://127.0.0.1:8000/",
        "documentation": "/docs",
        "supported_pipeline": [
            "1. Upload handwritten notes / PDFs",
            "2. Sarvam Document AI digitization",
            "3. Sarvam LLM pedagogy & whiteboard storyboard",
            "4. Sarvam Bulbul TTS voice synthesis",
            "5. HeyGen lifelike avatar video lecture generation"
        ]
    }

@app.post("/api/v1/upload-notes")
async def upload_notes(
    file: UploadFile = File(..., description="Uploaded notes (PDF, PNG, JPG)"),
    target_language: str = Form("en-IN", description="Language code: en-IN, hi-IN, te-IN, ta-IN, etc."),
    teaching_style: str = Form("interactive", description="Teaching style: interactive, conceptual, accelerated"),
    speaker: str = Form("shubh", description="Sarvam TTS voice speaker: shubh, aditya, priya, etc."),
    generate_audio: bool = Form(False, description="Synthesize TTS audio immediately via Sarvam Bulbul"),
    dry_run: bool = Form(False, description="Use sample digitization to test pipeline without consuming API credits")
):
    """
    Core pipeline endpoint:
    1. Ingests uploaded handwritten or printed notes.
    2. Digitizes content using Sarvam Document AI.
    3. Generates lecture scenes with spoken narration and whiteboard actions using Sarvam LLM.
    4. Optionally synthesizes voice audio with Sarvam Bulbul TTS.
    5. Formats the full payload ready for HeyGen avatar video rendering.
    """
    file_bytes = await file.read()
    filename = file.filename or "notes.pdf"
    
    extracted_text = ""
    
    # 1. Document Digitization (Sarvam Doc AI)
    if not dry_run:
        try:
            extracted_text = digitize_notes(
                file_bytes=file_bytes,
                filename=filename,
                content_type="mixed",
                language=target_language
            )
        except ApiError as e:
            if e.status_code == 402:
                # Quota exceeded / no credits; provide helpful fallback in prototype
                extracted_text = (
                    f"## Note Topic: Concept Explanation (Extracted from {filename})\n\n"
                    "Key concepts identified:\n"
                    "- Core principles and definitions\n"
                    "- Diagrammatic representations and relationship flows\n"
                    "- Key mathematical/logical formulas and practical examples\n"
                )
            else:
                raise HTTPException(status_code=e.status_code, detail=f"Sarvam Doc AI error: {e.body}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Digitization error: {str(e)}")
    else:
        extracted_text = (
            f"Sample digitized text from uploaded {filename}:\n"
            "Newton's Laws of Motion:\n"
            "1. First Law: An object remains at rest unless acted on by a net external force.\n"
            "2. Second Law: F = m * a (Force equals mass times acceleration).\n"
            "3. Third Law: For every action, there is an equal and opposite reaction."
        )

    # 2. Pedagogical Scripting & Whiteboard Generation (Sarvam LLM)
    if not dry_run:
        try:
            lecture_plan = generate_lecture_script(
                extracted_text=extracted_text,
                target_language=target_language,
                teaching_style=teaching_style
            )
        except ApiError as e:
            if e.status_code == 402:
                # Fallback mock plan for zero-credit accounts
                lecture_plan = _get_default_lecture_plan(filename)
            else:
                raise HTTPException(status_code=e.status_code, detail=f"Sarvam LLM error: {e.body}")
        except Exception as e:
            # If network error or quota error occurs, fallback gracefully
            lecture_plan = _get_default_lecture_plan(filename)
    else:
        lecture_plan = _get_default_lecture_plan(filename)

    # 3. Optional Audio Synthesis (Sarvam Bulbul TTS)
    audio_clips = []
    if generate_audio:
        try:
            for scene in lecture_plan.get("scenes", []):
                narration = scene.get("narration", "")
                if narration:
                    audios = synthesize_narration_audio(
                        text=narration,
                        language_code=target_language,
                        speaker=speaker
                    )
                    audio_clips.append({"scene_id": scene.get("scene_id"), "audios": audios})
        except Exception as e:
            # Continue even if TTS fails (e.g. credit limit)
            audio_clips.append({"error": f"Audio synthesis skipped: {str(e)}"})

    # 4. Construct HeyGen Avatar Video Payload
    heygen_payload = build_heygen_video_payload(lecture_plan=lecture_plan)

    return {
        "status": "success",
        "file_processed": filename,
        "extracted_notes": extracted_text,
        "lecture_plan": lecture_plan,
        "heygen_video_payload": heygen_payload,
        "audio_samples": audio_clips,
        "next_step": "Send 'heygen_video_payload' to HeyGen API (POST https://api.heygen.com/v2/video/generate) to render the final MP4."
    }

@app.post("/api/v1/adaptive-feedback")
def evaluate_student_feedback(req: AdaptiveFeedbackRequest):
    """
    Evaluates student answers during the tutoring session, provides instant feedback,
    and returns personalized reinforcement guidance.
    """
    is_correct = req.student_response.strip().lower() == req.correct_answer.strip().lower()
    
    return {
        "is_correct": is_correct,
        "feedback": (
            "Spot on! Great intuition." if is_correct 
            else f"Not quite. The correct answer is '{req.correct_answer}'."
        ),
        "explanation": f"In this context, understanding '{req.concept_context or 'this concept'}' is crucial for the next topic.",
        "recommended_next_action": "proceed_to_next_scene" if is_correct else "review_whiteboard_diagram"
    }

@app.get("/api/v1/interactive-avatar/session-config")
def get_interactive_session_config():
    """
    Provides streaming WebRTC configuration for real-time interactive avatar tutoring.
    """
    return create_interactive_avatar_session_config()

@app.post("/api/v1/generate-video")
async def generate_avatar_video(req: GenerateVideoRequest):
    """
    Integrates with HeyGen Video Generation API to produce the final MP4 video lecture
    with the lifelike tutor on one side and the interactive whiteboard on the other.
    """
    if req.heygen_payload:
        payload = req.heygen_payload
    elif req.lecture_plan:
        payload = build_heygen_video_payload(
            lecture_plan=req.lecture_plan,
            avatar_id=req.avatar_id or "Angela-in-business-suit"
        )
    else:
        raise HTTPException(status_code=400, detail="Either 'lecture_plan' or 'heygen_payload' is required.")

    result = await heygen_service.generate_video(payload)
    return {
        "status": "success",
        "video_generation": result,
        "poll_status_endpoint": f"/api/v1/video-status/{result['video_id']}"
    }

@app.get("/api/v1/video-status/{video_id}")
async def get_video_status(video_id: str):
    """
    Polls the rendering status and retrieves the streamable video URL once rendering is complete.
    """
    status = await heygen_service.get_video_status(video_id)
    return status

@app.post("/api/v1/interactive-avatar/session")
async def start_interactive_session(avatar_name: str = "Angela-in-business-suit"):
    """
    Initializes a live interactive avatar WebRTC session for real-time tutoring conversations.
    """
    session = await heygen_service.create_streaming_session(avatar_name=avatar_name)
    return {
        "status": "success",
        "session": session
    }

@app.post("/api/v1/interactive-avatar/speak")
async def interactive_speak(req: InteractiveSpeakRequest):
    """
    Commands the live avatar in an active WebRTC session to speak with natural gestures.
    """
    result = await heygen_service.streaming_speak(session_id=req.session_id, text=req.text)
    return result
