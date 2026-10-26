from typing import Any, Dict, List
from app.config import HEYGEN_API_KEY

def build_heygen_video_payload(
    lecture_plan: Dict[str, Any],
    avatar_id: str = "Angela-in-business-suit",
    aspect_ratio: str = "16:9"
) -> Dict[str, Any]:
    """
    Constructs a complete HeyGen Video Generation API payload from the Sarvam-generated
    lecture plan. Places the lifelike avatar on the left and dynamic whiteboard elements
    on the right.
    """
    video_clips = []
    
    for scene in lecture_plan.get("scenes", []):
        whiteboard = scene.get("whiteboard_action", {})
        narration = scene.get("narration", "")
        
        clip = {
            "avatar": {
                "avatar_id": avatar_id,
                "avatar_style": "normal",
                "scale": 1.0,
                "offset": {"x": -0.4, "y": 0.0}  # Positioned on left side to leave space for whiteboard
            },
            "voice": {
                "type": "text",
                "input_text": narration,
                "voice_id": "1bd001e7e50f421d891986aad5158bc8" # High quality tutor voice
            },
            "background": {
                "type": "color",
                "value": "#0F172A"  # Dark modern whiteboard background
            },
            "elements": [
                # Whiteboard title banner
                {
                    "type": "text",
                    "text": whiteboard.get("title", scene.get("title", "")),
                    "style": {
                        "color": "#38BDF8",
                        "font_size": 36,
                        "bold": True
                    },
                    "position": {"x": 0.35, "y": -0.35}
                },
                # Whiteboard diagram / content block
                {
                    "type": "text",
                    "text": whiteboard.get("content", ""),
                    "style": {
                        "color": "#F8FAFC",
                        "font_size": 24,
                        "line_height": 1.4
                    },
                    "position": {"x": 0.35, "y": 0.0}
                }
            ]
        }
        video_clips.append(clip)
        
    return {
        "title": lecture_plan.get("title", "AI Tutor Lecture"),
        "dimension": {"width": 1920, "height": 1080} if aspect_ratio == "16:9" else {"width": 1080, "height": 1920},
        "video_inputs": video_clips,
        "test": True if not HEYGEN_API_KEY else False
    }


def create_interactive_avatar_session_config(avatar_name: str = "default") -> Dict[str, Any]:
    """
    Configuration for HeyGen Interactive Streaming Avatar (WebRTC) for live 
    two-way tutoring sessions with instant speech feedback.
    """
    return {
        "quality": "high",
        "avatar_name": avatar_name,
        "voice": {
            "rate": 1.0
        },
        "knowledge_base": "Sarvam AI Tutor Brain",
        "version": "v2"
    }
