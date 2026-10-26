"""
VisionX Real-Time Dual-Model Inference & AI Assistant Backend
FastAPI server providing:
- Ultralytics Person Detection (Model A)
- Roboflow Waste Detection (Model B)
- Strands Agents Object-Aware Chatbot
- Cactus Compute Whistle Speech-to-Text Transcription
"""

import io
import sys
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure repository root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, File, UploadFile, Query, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from backend import config
from backend.schemas.detection import (
    DetectionResponse,
    ChatRequest,
    TranscribeResponse,
)
from backend.knowledge.waste_knowledge import WASTE_KNOWLEDGE_BASE
from backend.services.detection_pipeline import run_detection_pipeline
from backend.services.transcription import transcribe_audio_clip
from backend.agent.strands_agent import execute_agent_chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visionx.server")

# Initialize FastAPI App
app = FastAPI(
    title="VisionX Dual-Model Waste & Person Vision API",
    description="Live dual-model object detection, Strands conversational agent, and Whistle voice transcription",
    version="2.0.0"
)

# Enable CORS for local Vite development and previews
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint reporting system readiness, model configurations,
    and runtime status without leaking credentials.
    """
    roboflow_configured = bool(config.ROBOFLOW_API_KEY and config.ROBOFLOW_API_KEY != "your_api_key_here")
    grok_configured = bool(config.GROK_API and config.GROK_API != "your_api_key_here")

    return {
        "status": "healthy",
        "service": "VisionX Dual-Model Inference & Agent Engine",
        "version": "2.0.0",
        "device": config.DEVICE,
        "models": {
            "model_a_person": {
                "name": config.ULTRALYTICS_MODEL,
                "provider": "Ultralytics",
                "target_class": "person (COCO 0)",
                "status": "ready"
            },
            "model_b_waste": {
                "workspace": config.ROBOFLOW_WORKSPACE,
                "project": config.ROBOFLOW_PROJECT,
                "version": config.ROBOFLOW_VERSION,
                "provider": "Roboflow Universe Hosted",
                "api_key_configured": roboflow_configured,
                "status": "ready" if roboflow_configured else "credentials_needed"
            },
            "speech_to_text": {
                "model": "Whistle ASR",
                "provider": "Cactus Compute needle",
                "status": "ready"
            },
            "assistant_agent": {
                "framework": "Strands Agents",
                "provider": "Grok / OpenAI-compatible",
                "api_key_configured": grok_configured,
                "status": "ready" if grok_configured else "fallback_active"
            }
        },
        "default_conf_threshold": 0.18
    }


@app.get("/api/knowledge-base")
async def get_knowledge_base():
    """Returns the complete structured waste knowledge base."""
    return {
        "count": len(WASTE_KNOWLEDGE_BASE),
        "classes": list(WASTE_KNOWLEDGE_BASE.keys()),
        "knowledge": WASTE_KNOWLEDGE_BASE
    }


@app.post("/api/detect", response_model=DetectionResponse)
async def detect_objects(
    file: UploadFile = File(...),
    conf: float = Query(0.18, ge=0.05, le=1.0, description="Confidence threshold for detection filtering")
):
    """
    Executes the dual-model vision pipeline on an uploaded image or camera frame.
    Processes:
      1. Image decoding & validation
      2. Model A: Ultralytics Person Detection (person-only)
      3. Model B: Roboflow Waste Detection
      4. Normalization to [0..1] coordinates & enrichment with disposal knowledge
      5. Preservation of both person and waste detections without destructive suppression
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Please upload an image (JPEG, PNG, WEBP)."
        )

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        if image.mode != "RGB":
            image = image.convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode image file: {str(e)}")

    if image.width < 10 or image.height < 10:
        raise HTTPException(status_code=400, detail="Image dimensions too small for object detection.")

    result = await run_detection_pipeline(image=image, conf_threshold=conf)
    return result


@app.post("/api/visionx/chat")
async def visionx_chat(req: ChatRequest):
    """
    Strands Agents post-detection conversational endpoint.
    Retrieves grounded context, enforces non-waste rules for person detections,
    and returns structured answers with dynamic follow-up chips.
    """
    if not req.user_question or not req.user_question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        response = await execute_agent_chat(
            session_id=req.session_id or "default-session",
            user_question=req.user_question.strip(),
            selected_object=req.selected_object,
            all_detections=req.all_detections,
            history=req.history,
            locality=req.locality
        )
        return {
            "success": True,
            **response
        }
    except Exception as e:
        logger.error(f"Chat execution exception: {e}")
        raise HTTPException(status_code=500, detail=f"Chat agent error: {str(e)}")


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_speech(
    file: UploadFile = File(...)
):
    """
    Transcribes recorded audio speech using Cactus Compute Whistle.
    Returns transcript text to be inserted into the chat input field for user review.
    """
    try:
        audio_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read audio file: {str(e)}")

    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Audio file was empty.")

    response = transcribe_audio_clip(audio_bytes=audio_bytes, content_type=file.content_type)
    return response


if __name__ == "__main__":
    import uvicorn
    print("[VisionX Backend] Starting FastAPI dual-model server on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
