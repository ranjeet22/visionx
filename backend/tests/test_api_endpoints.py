"""
API Integration Tests for VisionX FastAPI Backend using httpx AsyncClient.
Tests:
- GET /api/health
- GET /api/knowledge-base
- POST /api/detect
- POST /api/visionx/chat
- POST /api/transcribe
"""

import io
import pytest
import httpx
from PIL import Image

from backend.server import app


def create_dummy_png_bytes(width=100, height=100):
    img = Image.new("RGB", (width, height), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_api_health_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "models" in data
        assert "model_a_person" in data["models"]
        assert "model_b_waste" in data["models"]
        assert "speech_to_text" in data["models"]
        assert "assistant_agent" in data["models"]


@pytest.mark.asyncio
async def test_api_knowledge_base_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/knowledge-base")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] > 0
        assert "plastic_bottle" in data["knowledge"]
        assert "cardboard" in data["knowledge"]


@pytest.mark.asyncio
async def test_api_detect_invalid_mime():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/detect",
            files={"file": ("test.txt", b"plain text", "text/plain")}
        )
        assert resp.status_code == 400
        assert "Invalid file type" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_api_detect_valid_image():
    png_bytes = create_dummy_png_bytes()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/detect?conf=0.2",
            files={"file": ("test.png", png_bytes, "image/png")}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "detections" in data
        assert "model_statuses" in data
        assert "pipeline_status" in data


@pytest.mark.asyncio
async def test_api_chat_empty_question():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/visionx/chat",
            json={"user_question": "   "}
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_chat_valid_question():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/visionx/chat",
            json={
                "user_question": "How do I recycle this?",
                "selected_object": {
                    "id": "person-1",
                    "model_source": "ultralytics_person",
                    "model_class_name": "person",
                    "display_name": "Person",
                    "confidence": 0.95
                }
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "answer" in data
        assert "not a waste item" in data["answer"].lower() or "person" in data["answer"].lower()


@pytest.mark.asyncio
async def test_api_transcribe_empty():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/transcribe",
            files={"file": ("empty.wav", b"", "audio/wav")}
        )
        assert resp.status_code == 400
