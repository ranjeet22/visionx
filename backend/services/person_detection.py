"""
Ultralytics Person Detection Service (Model A)
Exclusively detects humans/people using an official pretrained Ultralytics COCO model.
Filters out all non-person classes (bottles, cars, chairs, etc.).
"""

import time
import logging
from typing import List, Tuple, Optional
from PIL import Image
import torch
from ultralytics import YOLO

from backend import config
from backend.schemas.detection import BoundingBox, DetectedObject, ModelStatus
from backend.knowledge.waste_knowledge import resolve_person_item

logger = logging.getLogger("visionx.person_detection")

# Cached YOLO model instance
_PERSON_MODEL: Optional[YOLO] = None


def get_person_model() -> YOLO:
    """Initializes or returns cached Ultralytics model."""
    global _PERSON_MODEL
    if _PERSON_MODEL is None:
        model_name = config.ULTRALYTICS_MODEL or "yolov8n.pt"
        logger.info(f"Loading Ultralytics person detection model: {model_name}")
        _PERSON_MODEL = YOLO(model_name)
    return _PERSON_MODEL


def detect_people(
    image: Image.Image,
    conf_threshold: float = 0.25
) -> Tuple[List[DetectedObject], ModelStatus]:
    """
    Runs inference on an image and returns only person detections (COCO class ID 0).
    Non-person classes are strictly discarded.
    """
    start_time = time.perf_counter()
    model_name = config.ULTRALYTICS_MODEL or "yolov8n.pt"

    try:
        model = get_person_model()
    except Exception as e:
        logger.error(f"Failed to load Ultralytics person model: {e}")
        return [], ModelStatus(
            status="failed",
            model_name=model_name,
            error=f"Ultralytics model loading error: {str(e)}",
            inference_time_ms=0.0,
            detections_count=0
        )

    orig_width, orig_height = image.size
    if orig_width <= 0 or orig_height <= 0:
        return [], ModelStatus(
            status="failed",
            model_name=model_name,
            error="Invalid image dimensions for inference.",
            inference_time_ms=0.0,
            detections_count=0
        )

    try:
        # COCO class 0 is "person"
        results = model.predict(
            source=image,
            classes=[0],
            conf=conf_threshold,
            device=config.DEVICE,
            verbose=False
        )
    except Exception as e:
        logger.error(f"Ultralytics inference failed: {e}")
        inference_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return [], ModelStatus(
            status="failed",
            model_name=model_name,
            error=f"Inference error: {str(e)}",
            inference_time_ms=inference_ms,
            detections_count=0
        )

    inference_ms = round((time.perf_counter() - start_time) * 1000, 2)
    person_detections: List[DetectedObject] = []

    if results and len(results) > 0:
        boxes = results[0].boxes
        if boxes is not None and len(boxes) > 0:
            for idx, box in enumerate(boxes):
                class_id = int(box.cls[0].item())
                # Strictly enforce person class ID 0
                if class_id != 0:
                    continue

                confidence = float(box.conf[0].item())
                coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                x1, y1, x2, y2 = coords

                norm_x = max(0.0, min(1.0, x1 / orig_width))
                norm_y = max(0.0, min(1.0, y1 / orig_height))
                norm_w = max(0.0, min(1.0, (x2 - x1) / orig_width))
                norm_h = max(0.0, min(1.0, (y2 - y1) / orig_height))

                bbox = BoundingBox(
                    x=round(norm_x, 4),
                    y=round(norm_y, 4),
                    width=round(norm_w, 4),
                    height=round(norm_h, 4)
                )

                person_obj = resolve_person_item(
                    confidence=confidence,
                    box=bbox,
                    instance_index=idx + 1,
                    model_source="ultralytics_person"
                )
                person_detections.append(person_obj)

    status = ModelStatus(
        status="success",
        model_name=model_name,
        inference_time_ms=inference_ms,
        detections_count=len(person_detections)
    )

    return person_detections, status
