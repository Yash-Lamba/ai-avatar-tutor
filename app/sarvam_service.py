import io
import json
import time
from typing import Any, Dict, List, Optional
from sarvamai import SarvamAI
from sarvamai.core.api_error import ApiError

from app.config import SARVAM_API_KEY

def get_sarvam_client() -> SarvamAI:
    if not SARVAM_API_KEY:
        raise ValueError("SARVAM_API_KEY is not configured in .env")
    return SarvamAI(api_subscription_key=SARVAM_API_KEY)


def digitize_notes(
    file_bytes: bytes,
    filename: str,
    content_type: str = "mixed",
    language: str = "en-IN",
) -> str:
    """
    Digitizes handwritten or printed notes using Sarvam Vision / Document AI.
    """
    client = get_sarvam_client()
    file_tuple = [(filename, file_bytes)]
    
    # Start digitization job
    job = client.doc_ai.digitise(
        file=file_tuple,
        content_type=content_type,
        language=language,
    )
    job_id = job.job_id

    # Poll status until terminal state
    terminal_states = {"completed", "partially_completed", "failed", "rejected"}
    max_retries = 30
    for _ in range(max_retries):
        status_resp = client.doc_ai.get_status(job_id=job_id)
        if status_resp.status in terminal_states:
            if status_resp.status in {"failed", "rejected"}:
                raise RuntimeError(f"Document digitization failed with status: {status_resp.status}")
            break
        time.sleep(2)

    # Fetch markdown results
    results = client.doc_ai.get_results(job_id=job_id, format="md")
    
    # Extract markdown text from pages
    extracted_text = ""
    if hasattr(results, "documents") and results.documents:
        for doc in results.documents:
            if hasattr(doc, "pages") and doc.pages:
                for page in doc.pages:
                    extracted_text += (page.content or "") + "\n\n"
    return extracted_text.strip() or "No text could be extracted."


def generate_lecture_script(
    extracted_text: str,
    target_language: str = "en-IN",
    teaching_style: str = "interactive",
) -> Dict[str, Any]:
    """
    Uses Sarvam's conversational LLM to transform raw notes into a 
    structured video lecture plan with whiteboard cues, gestures, and check-in questions.
    """
    client = get_sarvam_client()

    prompt = f"""You are a master AI tutor designing a multimodal video lecture.
A student uploaded the following study notes:
---
{extracted_text}
---

Your task is to transform these notes into a complete structured video lecture script.
Teaching style: {teaching_style}. Target language/accent: {target_language}.

Return ONLY a valid JSON object matching this schema (no markdown fences, no extra text):
{{
  "title": "Lesson Title",
  "summary": "1-2 sentence overview of the topic",
  "scenes": [
    {{
      "scene_id": 1,
      "title": "Scene Heading",
      "narration": "What the AI avatar speaks aloud to the student with clear, engaging, conversational tone.",
      "avatar_gesture": "warm_welcome | pointing_left | explaining_hands | encouraging_nod",
      "whiteboard_action": {{
        "type": "diagram | bullet_points | formula | code",
        "title": "Whiteboard Title",
        "content": "Text, key points, equation or Mermaid diagram to draw on the visual whiteboard",
        "highlight": "Specific phrase or formula term to emphasize"
      }},
      "duration_sec": 25
    }}
  ],
  "adaptive_questions": [
    {{
      "id": 1,
      "question": "A conceptual check-in question to test comprehension",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Why this is correct and reinforces the concept."
    }}
  ]
}}
"""

    response = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[
            {"role": "system", "content": "You are an expert educational curriculum and video script designer. Respond strictly in JSON format."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )

    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:].strip()

    try:
        return json.loads(content)
    except Exception:
        return {
            "title": "Generated Lecture",
            "summary": "Structured lesson from notes",
            "scenes": [
                {
                    "scene_id": 1,
                    "title": "Introduction",
                    "narration": content,
                    "avatar_gesture": "warm_welcome",
                    "whiteboard_action": {
                        "type": "bullet_points",
                        "title": "Core Concepts",
                        "content": extracted_text[:300],
                        "highlight": ""
                    },
                    "duration_sec": 30
                }
            ],
            "adaptive_questions": []
        }


def synthesize_narration_audio(
    text: str,
    language_code: str = "en-IN",
    speaker: str = "shubh",
    model: str = "bulbul:v3"
) -> List[str]:
    """
    Synthesizes speech audio for a scene narration using Sarvam Bulbul TTS.
    Returns base64 encoded audio strings.
    """
    client = get_sarvam_client()
    
    # Clip text if above max limit for safety
    trimmed_text = text[:2400]
    
    response = client.text_to_speech.convert(
        text=trimmed_text,
        language_code=language_code,
        speaker=speaker,
        model=model,
        output_audio_codec="mp3"
    )
    return response.audios
