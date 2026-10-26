"""
VisionX Post-Detection Conversational Agent
Powered by Strands Agents framework (Agent, tools, and OpenAIModel provider).
Provides grounded, object-aware waste sorting assistance, material safety intelligence,
and strict non-waste handling for person detections.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from strands import Agent, tool
from strands.models.openai import OpenAIModel

from backend import config
from backend.knowledge.waste_knowledge import (
    WASTE_KNOWLEDGE_BASE,
    CLASS_ALIASES,
    is_person_class,
    resolve_waste_item,
    resolve_person_item
)

logger = logging.getLogger("visionx.agent")

# In-memory session store for frame detection contexts
SESSION_DETECTIONS: Dict[str, Dict[str, Any]] = {}


# --- Pydantic Schema for Structured Response ---
class AgentChatResponse(BaseModel):
    answer: str = Field(
        ...,
        description="Comprehensive, helpful, grounded answer regarding waste disposal or detection context in GitHub-flavored Markdown."
    )
    suggested_questions: List[str] = Field(
        default_factory=list,
        description="Exactly 3 dynamic, context-relevant follow-up questions the user can ask next."
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Authoritative sources or knowledge bases referenced in the response."
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if physical material composition cannot be definitively identified from visual inspection alone."
    )
    uncertainty_note: Optional[str] = Field(
        default=None,
        description="Explanatory note if material identification or local municipal policy is ambiguous."
    )


def register_session_detections(session_id: str, detections: List[Dict[str, Any]]):
    """Stores the latest detections for a given session."""
    SESSION_DETECTIONS[session_id] = {
        "detections": {str(d.get("id", i)): d for i, d in enumerate(detections)}
    }


# --- Controlled Strands Tools ---

@tool
def get_detection_context(session_id: str, detection_id: str) -> Dict[str, Any]:
    """
    Retrieves the detection details (model source, class name, bounding box coordinates,
    confidence score, and waste category) for a given object in the session.
    """
    session_data = SESSION_DETECTIONS.get(session_id)
    if not session_data:
        return {"found": False, "error": f"No detection session registered with ID '{session_id}'."}

    dets = session_data.get("detections", {})
    if detection_id in dets:
        d = dets[detection_id]
        return {
            "found": True,
            "id": d.get("id"),
            "model_source": d.get("model_source"),
            "display_name": d.get("display_name"),
            "model_class_name": d.get("model_class_name"),
            "confidence": d.get("confidence"),
            "box": d.get("box") or d.get("bbox"),
            "waste_category": d.get("waste_category"),
            "material": d.get("material"),
            "material_verified": d.get("material_verified", False)
        }

    # Fallback to primary detection if specific ID not found
    if dets:
        first_d = next(iter(dets.values()))
        return {
            "found": True,
            "id": first_d.get("id"),
            "model_source": first_d.get("model_source"),
            "display_name": first_d.get("display_name"),
            "confidence": first_d.get("confidence"),
            "note": "Exact ID not matched, returned primary detection in frame."
        }

    return {"found": False, "error": "No objects found in session."}


@tool
def get_waste_guidance(item_or_category: str) -> Dict[str, Any]:
    """
    Retrieves official waste sorting instructions, recommended cleaning/preparation steps,
    and recyclability status from the VisionX Knowledge Base.
    """
    query = item_or_category.lower().strip()

    # Search in knowledge base keys or display names
    for key, data in WASTE_KNOWLEDGE_BASE.items():
        if (
            query in key.lower()
            or query in data.get("display_name", "").lower()
            or query in str(data.get("waste_category", "")).lower()
        ):
            return {
                "matched_item": data.get("display_name"),
                "waste_category": data.get("waste_category"),
                "disposal_method": data.get("disposal_method"),
                "recycling_guidance": data.get("recycling_guidance"),
                "preparation_steps": data.get("preparation_steps", []),
                "contamination_warning": data.get("contamination_warning"),
                "environmental_impact": data.get("environmental_impact"),
                "source": data.get("source")
            }

    return {
        "matched_item": item_or_category,
        "waste_category": "uncertain",
        "disposal_method": "Inspect item for resin identification codes (#1-#7) and verify with local municipal guidelines.",
        "recycling_guidance": "Uncertain items should not be placed in curbside recycling without confirming facility acceptance.",
        "preparation_steps": ["Inspect for recyclability symbols", "Confirm with local waste authority"],
        "source": "VisionX Standard Sanitation Protocol"
    }


@tool
def search_material_safety(material_name: str) -> Dict[str, Any]:
    """
    Returns material safety hazards, contamination risks, and handling precautions
    (e.g., lithium batteries, broken glass, chemical containers).
    """
    m = (material_name or "").lower().strip()
    if any(k in m for k in ["battery", "lithium", "electronic", "cell"]):
        return {
            "hazard_level": "CRITICAL FIRE HAZARD",
            "risks": "Lithium batteries ignite volatile fires when crushed inside municipal compactor trucks.",
            "safety_instructions": "Tape both terminals with non-conductive electrical tape. Take immediately to certified battery or e-waste drop-off. NEVER put in curbside bins.",
            "source": "Call2Recycle & EPA Universal Waste Regulations"
        }
    elif any(k in m for k in ["glass", "broken", "jar", "bottle"]):
        return {
            "hazard_level": "MODERATE LACERATION HAZARD",
            "risks": "Broken glass presents severe injury risks to manual sorting facility workers.",
            "safety_instructions": "If intact, recycle in curbside glass bin. If broken, wrap securely in cardboard or newspaper and dispose in non-recyclable trash.",
            "source": "Occupational Safety and Health Guidelines for MRFs"
        }
    elif any(k in m for k in ["plastic", "pet", "film", "wrapper", "bag"]):
        return {
            "hazard_level": "EQUIPMENT DAMAGE & MICROPLASTIC HAZARD",
            "risks": "Thin films jam disc screen axles in MRF sorting facilities. Unrecycled plastics break down into microplastics.",
            "safety_instructions": "Separate rigid containers (curbside) from thin plastic films (drop-off at participating supermarkets).",
            "source": "Association of Plastic Recyclers (APR)"
        }
    elif any(k in m for k in ["organic", "food", "grease", "oil"]):
        return {
            "hazard_level": "COMMODITY CONTAMINATION",
            "risks": "Grease and food oils permanently ruin dry paper and cardboard pulping.",
            "safety_instructions": "Compost food scraps or use green organic bin. Thoroughly rinse containers before recycling.",
            "source": "Municipal Composting Protocols"
        }
    else:
        return {
            "hazard_level": "LOW TO STANDARD",
            "risks": "General municipal solid waste handling.",
            "safety_instructions": "Keep materials clean and dry. Avoid mixing unknown chemical residues.",
            "source": "VisionX Safety Database"
        }


@tool
def get_local_disposal_guidance(locality: str, category: str) -> Dict[str, Any]:
    """
    Provides regional municipal recycling standards, container deposit scheme guidance,
    and drop-off instructions for a given locality.
    """
    loc = (locality or "").lower().strip()
    cat = (category or "").lower().strip()

    has_deposit = any(k in loc for k in ["california", "oregon", "michigan", "new york", "germany", "australia"])

    return {
        "locality": locality or "Standard Municipal Framework",
        "category": category,
        "deposit_return_eligible": has_deposit and "recyclable" in cat,
        "deposit_refund_amount": "5-10 cents per beverage container where applicable" if has_deposit else None,
        "curbside_rules": "Single-stream blue bin for clean rigid containers and dry paper. Green bin for organics. Black/gray bin for landfill residual.",
        "drop_off_programs": "Supermarket drop-off bins accept clean soft plastic films. Municipal civic amenity sites accept e-waste and batteries.",
        "source": "Global Recycling Directory & Municipal Waste Guidelines"
    }


def _get_api_credentials() -> Optional[tuple[str, str, List[str]]]:
    """Resolves API key, endpoint URL, and candidate models without exposing secrets."""
    key = config.GROK_API
    if not key or key == "your_api_key_here":
        return None

    if key.startswith("gsk_"):
        # Groq endpoint
        base_url = "https://api.groq.com/openai/v1"
        candidate_models = [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b",
        ]
    elif key.startswith("xai-"):
        # Official xAI Grok endpoint
        base_url = "https://api.x.ai/v1"
        candidate_models = ["grok-beta", "grok-2-latest"]
    else:
        base_url = "https://api.groq.com/openai/v1"
        candidate_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]

    return key, base_url, candidate_models


SYSTEM_PROMPT = """You are VisionX Assistant, an expert AI environmental engineer and waste classification specialist.
You work inside the VisionX platform, helping users understand how to properly recycle, compost, reuse, or dispose of items detected in their camera or uploaded photos by the dual-model computer vision pipeline (Ultralytics Person Detection and Roboflow Waste Detection).

CRITICAL OPERATIONAL RULES:
1. OBJECT AWARENESS & GROUNDING:
   - You are informed of the current object the user selected, its model source, classification, confidence score, and waste category.
   - You also know all other detected objects present in the same frame.
2. SPECIAL RULE FOR PERSON DETECTIONS:
   - A person is NOT a waste item!
   - If the selected object is a Person or has model_source 'ultralytics_person':
     - Explain clearly that a person was detected by the computer vision model.
     - State explicitly: "Person detected. This is not a waste item, so waste disposal guidance does not apply."
     - NEVER provide recycling instructions, bin colors, or disposal methods for a person.
     - If other waste items exist in the frame, you may point them out (e.g., "However, there is also a plastic bottle in the image that can be recycled!").
3. ACCURACY & UNCERTAINTY:
   - Never guess polymer grades from appearance alone. If material is not verified, note that physical inspection of the resin stamp (#1-#7) is needed.
   - For unknown waste classes, advise caution and local sanitation verification.
4. OUTPUT SCHEMA:
   - Your response must strictly contain: answer, suggested_questions (exactly 3 relevant follow-ups), sources, needs_clarification (bool), uncertainty_note (optional string).
"""


def _generate_grounded_fallback(
    selected_object: Optional[Dict[str, Any]],
    user_question: str,
    all_detections: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generates a deterministic, verified grounded fallback when the cloud LLM is unavailable.
    Guarantees no false claims of live LLM inference.
    """
    if not selected_object:
        # General question with no selected item
        other_items = [d.get("display_name") for d in (all_detections or []) if d.get("display_name")]
        summary = f"Detected in frame: {', '.join(other_items)}." if other_items else "No objects currently selected."
        return {
            "answer": (
                f"**VisionX Offline Assistant (Local Knowledge Base)**\n\n"
                f"{summary}\n\n"
                f"To get specific disposal instructions, select an object from the detections panel or ensure your live AI assistant credentials (`GROK_API`) are configured in `.env`."
            ),
            "suggested_questions": [
                "How do I recycle plastic bottles?",
                "What can go into the green compost bin?",
                "Where should electronic waste and batteries be dropped off?"
            ],
            "sources": ["VisionX Local Knowledge Base"],
            "needs_clarification": False,
            "uncertainty_note": "Cloud LLM unavailable; response generated from local verified knowledge base.",
            "model_used": "visionx-local-knowledge-fallback"
        }

    is_person = (
        selected_object.get("model_source") == "ultralytics_person"
        or is_person_class(str(selected_object.get("model_class_name", "")), selected_object.get("class_id"))
    )

    if is_person:
        return {
            "answer": (
                "### Detection: Person\n\n"
                "**Person detected.** This is a human detected by the Ultralytics computer vision model, not a waste item. "
                "Waste disposal guidance does not apply to people.\n\n"
                "If you intended to scan a waste item, please point the camera directly at the item or select the item's bounding box from the scan results."
            ),
            "suggested_questions": [
                "Why was a person detected in the image?",
                "Are there any waste items detected in this photo?",
                "How does the dual-model detection pipeline work?"
            ],
            "sources": ["Ultralytics COCO Person Detection"],
            "needs_clarification": False,
            "uncertainty_note": None,
            "model_used": "visionx-person-guardrail"
        }

    # Waste item fallback
    disp_name = selected_object.get("display_name", "Waste Item")
    guidance = get_waste_guidance(disp_name)
    safety = search_material_safety(selected_object.get("material", ""))

    prep_list = guidance.get("preparation_steps", ["Empty completely", "Inspect for recyclability symbol"])
    prep_md = "\n".join([f"- {s}" for s in prep_list])

    hazard_section = ""
    if safety.get("hazard_level") and "LOW" not in safety.get("hazard_level", ""):
        hazard_section = f"\n\n**Safety Alert ({safety.get('hazard_level')}):** {safety.get('risks')}\n*Instructions:* {safety.get('safety_instructions')}"

    answer = (
        f"### Disposal Guidance: {disp_name}\n\n"
        f"**Category:** `{guidance.get('waste_category', 'general')}`\n\n"
        f"**Disposal Method:** {guidance.get('disposal_method')}\n\n"
        f"**Recycling Guidance:** {guidance.get('recycling_guidance')}\n\n"
        f"**Preparation Steps:**\n{prep_md}"
        f"{hazard_section}"
    )

    suggested = [
        f"How should I clean this {disp_name} before disposal?",
        "What happens if food residue is left on recyclables?",
        "Where can I find my nearest specialized drop-off point?"
    ]

    return {
        "answer": answer,
        "suggested_questions": suggested,
        "sources": [guidance.get("source", "VisionX Knowledge Engine")],
        "needs_clarification": not selected_object.get("material_verified", False),
        "uncertainty_note": "Cloud LLM unavailable; response generated from local verified knowledge base. Visual inspection cannot confirm resin codes without stamp verification.",
        "model_used": "visionx-local-knowledge-fallback"
    }


async def execute_agent_chat(
    session_id: str,
    user_question: str,
    selected_object: Optional[Dict[str, Any]] = None,
    all_detections: Optional[List[Dict[str, Any]]] = None,
    history: Optional[List[Dict[str, str]]] = None,
    locality: Optional[str] = "United States / General Municipal"
) -> Dict[str, Any]:
    """
    Executes a post-detection conversational turn using Strands Agents SDK.
    Grounds context server-side, queries live LLM, and gracefully falls back to verified knowledge.
    """
    if all_detections:
        register_session_detections(session_id, all_detections)

    creds = _get_api_credentials()
    if not creds:
        logger.info("No LLM API credentials configured; using structured verified local fallback.")
        return _generate_grounded_fallback(selected_object, user_question, all_detections)

    api_key, base_url, candidate_models = creds

    # Build detection-aware context server-side
    active_name = selected_object.get("display_name", "N/A") if selected_object else "None"
    active_source = selected_object.get("model_source", "N/A") if selected_object else "N/A"
    active_class = selected_object.get("model_class_name", "N/A") if selected_object else "N/A"
    active_conf = f"{int(float(selected_object.get('confidence', 0)) * 100)}%" if selected_object else "N/A"
    active_cat = selected_object.get("waste_category", "N/A") if selected_object else "N/A"
    active_mat = selected_object.get("material", "N/A") if selected_object else "N/A"
    is_person = (
        active_source == "ultralytics_person"
        or is_person_class(str(active_class), selected_object.get("class_id") if selected_object else None)
    )

    frame_context_str = "None"
    if all_detections and len(all_detections) > 0:
        other_items = [
            f"{d.get('display_name')} (Source: {d.get('model_source')}, Conf: {int(float(d.get('confidence', 0)) * 100)}%)"
            for d in all_detections
        ]
        frame_context_str = "; ".join(other_items)

    detection_context_prompt = f"""
CURRENT SCAN CONTEXT:
- Selected Object: {active_name}
- Model Source: {active_source}
- Original Model Class: {active_class}
- Confidence: {active_conf}
- Waste Category: {active_cat}
- Material: {active_mat}
- Is Person: {is_person}
- All Detections In Frame: {frame_context_str}
- Locality: {locality or 'General Municipal'}
"""

    full_system = f"{SYSTEM_PROMPT}\n{detection_context_prompt}"

    # Try live Strands Agent with candidate models
    last_error = None
    for model_name in candidate_models:
        try:
            strands_model = OpenAIModel(
                model_id=model_name,
                client_args={
                    "api_key": api_key,
                    "base_url": base_url,
                }
            )

            agent = Agent(
                model=strands_model,
                tools=[
                    get_detection_context,
                    get_waste_guidance,
                    search_material_safety,
                    get_local_disposal_guidance
                ],
                system_prompt=full_system,
                structured_output_model=AgentChatResponse
            )

            # Build user prompt with history if provided
            history_text = ""
            if history:
                turns = []
                for turn in history[-4:]:
                    sender = "User" if turn.get("sender") == "user" else "Assistant"
                    turns.append(f"{sender}: {turn.get('text', '')}")
                history_text = "Previous conversation:\n" + "\n".join(turns) + "\n\n"

            prompt_content = f"{history_text}User Question: {user_question}"
            agent_result = await agent.invoke_async(prompt_content)

            # Extract structured response
            if hasattr(agent_result, "structured_output") and agent_result.structured_output:
                res: AgentChatResponse = agent_result.structured_output
                return {
                    "answer": res.answer,
                    "suggested_questions": res.suggested_questions[:3],
                    "sources": res.sources,
                    "needs_clarification": res.needs_clarification,
                    "uncertainty_note": res.uncertainty_note,
                    "model_used": f"strands-{model_name}"
                }
            elif hasattr(agent_result, "output") and agent_result.output:
                # Text output parsed or converted
                text_out = str(agent_result.output)
                try:
                    data = json.loads(text_out)
                    return {
                        "answer": data.get("answer", text_out),
                        "suggested_questions": data.get("suggested_questions", [])[:3],
                        "sources": data.get("sources", ["VisionX Knowledge Engine"]),
                        "needs_clarification": bool(data.get("needs_clarification", False)),
                        "uncertainty_note": data.get("uncertainty_note"),
                        "model_used": f"strands-{model_name}"
                    }
                except Exception:
                    return {
                        "answer": text_out,
                        "suggested_questions": [
                            f"How should I clean this {active_name}?",
                            "What bin does this item belong in?",
                            "What are the local rules for this material?"
                        ],
                        "sources": ["VisionX Knowledge Engine"],
                        "needs_clarification": False,
                        "uncertainty_note": None,
                        "model_used": f"strands-{model_name}"
                    }

        except Exception as e:
            last_error = f"{model_name}: {str(e)}"
            logger.warning(f"Strands Agent attempt with {model_name} failed: {e}")

    # If live agent calls failed, safely return the verified grounded fallback
    logger.error(f"All Strands model attempts failed ({last_error}). Providing grounded fallback.")
    fallback = _generate_grounded_fallback(selected_object, user_question, all_detections)
    fallback["uncertainty_note"] = f"Live LLM unavailable ({last_error}). Grounded in verified local knowledge base."
    return fallback
