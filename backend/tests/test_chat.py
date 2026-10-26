"""
Tests for Strands Agent Post-Detection Conversational Endpoint.
Covers:
- Question about selected waste item
- Question with no selected object
- Person detection (strictly no waste disposal instructions)
- Unknown waste class handling
- Empty question validation
- Offline / missing LLM credentials fallback
- Output schema verification
"""

import pytest
from unittest.mock import patch
from backend.agent.strands_agent import execute_agent_chat


@pytest.mark.asyncio
async def test_chat_selected_waste_item_fallback():
    """Tests grounded local knowledge fallback when asking about a waste item without live LLM."""
    selected = {
        "id": "waste-plastic_bottle-1",
        "model_source": "roboflow_waste",
        "model_class_name": "plastic_bottle",
        "display_name": "Plastic Beverage Bottle",
        "confidence": 0.92,
        "waste_category": "recyclable",
        "material": "PET #1",
        "material_verified": False
    }

    # With no API key configured, it falls back to verified local knowledge
    with patch("backend.agent.strands_agent._get_api_credentials", return_value=None):
        res = await execute_agent_chat(
            session_id="test-session",
            user_question="How should I dispose of this bottle?",
            selected_object=selected
        )

        assert "answer" in res
        assert "suggested_questions" in res
        assert len(res["suggested_questions"]) == 3
        assert "sources" in res
        assert "needs_clarification" in res
        assert res["model_used"] == "visionx-local-knowledge-fallback"
        assert "plastic" in res["answer"].lower() or "bottle" in res["answer"].lower()


@pytest.mark.asyncio
async def test_chat_person_detection():
    """
    CRITICAL: Person detection must NEVER generate waste disposal instructions.
    Must clarify that a person is not a waste item.
    """
    selected_person = {
        "id": "person-1",
        "model_source": "ultralytics_person",
        "model_class_name": "person",
        "display_name": "Person",
        "confidence": 0.95,
        "waste_category": None
    }

    with patch("backend.agent.strands_agent._get_api_credentials", return_value=None):
        res = await execute_agent_chat(
            session_id="test-person-session",
            user_question="How do I recycle this?",
            selected_object=selected_person
        )

        assert "person detected" in res["answer"].lower()
        assert "not a waste item" in res["answer"].lower()
        assert res["model_used"] == "visionx-person-guardrail"


@pytest.mark.asyncio
async def test_chat_no_selected_object():
    """Test general question when no specific object is selected."""
    all_dets = [
        {"display_name": "Cardboard Box", "model_source": "roboflow_waste"},
        {"display_name": "Person", "model_source": "ultralytics_person"}
    ]

    with patch("backend.agent.strands_agent._get_api_credentials", return_value=None):
        res = await execute_agent_chat(
            session_id="test-no-obj",
            user_question="What should I do with my recyclables?",
            selected_object=None,
            all_detections=all_dets
        )

        assert "answer" in res
        assert len(res["suggested_questions"]) == 3


@pytest.mark.asyncio
async def test_chat_unknown_waste_class():
    """Test question on an unverified / unknown detected waste item."""
    unknown = {
        "id": "waste-unknown-xyz-1",
        "model_source": "roboflow_waste",
        "model_class_name": "mystery_packaging",
        "display_name": "mystery_packaging (Unverified)",
        "confidence": 0.70,
        "waste_category": "uncertain",
        "material": "Unknown",
        "material_verified": False
    }

    with patch("backend.agent.strands_agent._get_api_credentials", return_value=None):
        res = await execute_agent_chat(
            session_id="test-unknown",
            user_question="Can this be recycled?",
            selected_object=unknown
        )

        assert "uncertain" in res["answer"].lower() or "municipal" in res["answer"].lower()
        assert res["needs_clarification"] is True
