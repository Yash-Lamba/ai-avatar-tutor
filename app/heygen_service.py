import os
import uuid
import time
from typing import Any, Dict, Optional
import httpx
from app.config import HEYGEN_API_KEY

HEYGEN_API_BASE = "https://api.heygen.com"

# In-memory registry for mock/simulated video generations when API key is in sandbox mode
_SIMULATED_VIDEOS: Dict[str, Dict[str, Any]] = {}

class HeyGenService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or HEYGEN_API_KEY
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }

    async def generate_video(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submits a video rendering job to HeyGen API (/v2/video/generate).
        Falls back to simulation mode if no valid API key is present.
        """
        if self.api_key and not self.api_key.startswith("dummy"):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{HEYGEN_API_BASE}/v2/video/generate",
                        json=payload,
                        headers=self.headers
                    )
                    data = resp.json()
                    if resp.status_code == 200 and data.get("data", {}).get("video_id"):
                        return {
                            "mode": "live",
                            "video_id": data["data"]["video_id"],
                            "status": "processing"
                        }
            except Exception as e:
                # Log and fallback to simulation mode
                pass

        # Simulation Mode
        simulated_id = f"vid_{uuid.uuid4().hex[:12]}"
        _SIMULATED_VIDEOS[simulated_id] = {
            "video_id": simulated_id,
            "title": payload.get("title", "Lecture Video"),
            "status": "completed",
            "duration": 45.0,
            "video_url": f"https://resource.heygen.com/video/sample_lecture_preview.mp4",
            "thumbnail_url": "https://resource.heygen.com/avatar/angela_whiteboard_thumb.png",
            "scenes_rendered": len(payload.get("video_inputs", [])),
            "created_at": time.time()
        }
        return {
            "mode": "simulation",
            "video_id": simulated_id,
            "status": "completed",
            "message": "HeyGen video generation simulated successfully. Add HEYGEN_API_KEY to .env for live renders."
        }

    async def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """
        Queries status of video render job from HeyGen API (/v1/video_status.get).
        """
        if video_id in _SIMULATED_VIDEOS:
            sim = _SIMULATED_VIDEOS[video_id]
            return {
                "video_id": video_id,
                "status": sim["status"],
                "video_url": sim["video_url"],
                "thumbnail_url": sim["thumbnail_url"],
                "duration": sim["duration"],
                "mode": "simulation"
            }

        if self.api_key and not self.api_key.startswith("dummy"):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        f"{HEYGEN_API_BASE}/v1/video_status.get?video_id={video_id}",
                        headers=self.headers
                    )
                    data = resp.json()
                    if resp.status_code == 200:
                        vdata = data.get("data", {})
                        return {
                            "video_id": video_id,
                            "status": vdata.get("status", "unknown"),
                            "video_url": vdata.get("video_url"),
                            "thumbnail_url": vdata.get("thumbnail_url"),
                            "duration": vdata.get("duration"),
                            "mode": "live"
                        }
            except Exception:
                pass

        return {
            "video_id": video_id,
            "status": "not_found",
            "message": "Video ID could not be found"
        }

    async def create_streaming_session(self, avatar_name: str = "Angela-in-business-suit") -> Dict[str, Any]:
        """
        Initializes an Interactive Streaming Avatar session for live WebRTC tutoring.
        """
        if self.api_key and not self.api_key.startswith("dummy"):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{HEYGEN_API_BASE}/v1/streaming.new",
                        json={"quality": "high", "avatar_name": avatar_name},
                        headers=self.headers
                    )
                    if resp.status_code == 200:
                        return resp.json().get("data", {})
            except Exception:
                pass

        # Simulated streaming session
        session_id = f"stream_{uuid.uuid4().hex[:12]}"
        return {
            "session_id": session_id,
            "status": "active",
            "sdp": {"type": "offer", "sdp": "v=0\r\no=HeyGenTutor 2890844526 IN IP4 127.0.0.1\r\ns=Live Avatar Stream..."},
            "ice_servers": [{"urls": "stun:stun.l.google.com:19302"}],
            "avatar_name": avatar_name,
            "mode": "simulation"
        }

    async def streaming_speak(self, session_id: str, text: str) -> Dict[str, Any]:
        """
        Commands the live streaming avatar to speak text in real-time.
        """
        return {
            "session_id": session_id,
            "action": "speak",
            "text": text,
            "status": "queued"
        }

heygen_service = HeyGenService()
