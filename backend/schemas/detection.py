"""
Detection and VisionX schemas.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: float = Field(..., description="Normalized top-left x coordinate (0..1)")
    y: float = Field(..., description="Normalized top-left y coordinate (0..1)")
    width: float = Field(..., description="Normalized width (0..1)")
    height: float = Field(..., description="Normalized height (0..1)")


class ModelStatus(BaseModel):
    status: Literal["success", "failed", "skipped"]
    model_name: str
    error: Optional[str] = None
    inference_time_ms: Optional[float] = None
    detections_count: int = 0


class DetectedObject(BaseModel):
    id: str = Field(..., description="Globally unique detection ID")
    instance_index: int = 1
    model_source: str = Field(..., description="Source model identifier (e.g. ultralytics_person, roboflow_waste)")
    class_id: Optional[int] = None
    model_class_name: str
    display_name: str
    confidence: float
    box: BoundingBox
    # Alias / mirror for bbox convention requested in prompt
    bbox: Optional[BoundingBox] = None
    waste_category: Optional[str] = None
    material: Optional[str] = None
    material_verified: bool = False
    disposal_method: Optional[str] = None
    recycling_guidance: Optional[str] = None
    guidance: Optional[str] = None
    preparation_steps: List[str] = Field(default_factory=list)
    contamination_warning: Optional[str] = None
    reusability: Optional[str] = None
    environmental_impact: Optional[str] = None
    special_handling: Optional[str] = None
    policy_status: str = "general-guidance"
    mapping_status: str = "verified"
    source: str = "VisionX Knowledge Engine"
    source_url: Optional[str] = None


class DetectionResponse(BaseModel):
    success: bool
    inference_time_ms: float
    image_width: int
    image_height: int
    confidence_threshold: float
    detections_count: int
    detections: List[DetectedObject]
    model_statuses: Dict[str, ModelStatus]
    pipeline_status: Literal["all_succeeded", "partial_success", "all_failed", "no_objects_detected"]
    error: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: Optional[str] = "default-session"
    user_question: str
    selected_detection_id: Optional[str] = None
    selected_object: Optional[Dict[str, Any]] = None
    all_detections: Optional[List[Dict[str, Any]]] = None
    history: Optional[List[Dict[str, str]]] = None
    locality: Optional[str] = "General Municipal"


class TranscribeResponse(BaseModel):
    success: bool
    text: str
    language: Optional[str] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
