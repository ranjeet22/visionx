"""
VisionX Dual-Model Detection Pipeline
Coordinates Ultralytics Person Detection (Model A) and Roboflow Waste Detection (Model B).
Merges detections into a single schema, handles partial failures gracefully,
and preserves overlapping person/waste detections.
"""

import time
import logging
from typing import List, Dict, Any, Tuple
from PIL import Image

from backend.schemas.detection import (
    DetectedObject,
    ModelStatus,
    DetectionResponse,
    BoundingBox
)
from backend.services.person_detection import detect_people
from backend.services.waste_detection import detect_waste

logger = logging.getLogger("visionx.pipeline")


def compute_iou(box1: BoundingBox, box2: BoundingBox) -> float:
    """Computes Intersection-over-Union between two normalized bounding boxes."""
    xA = max(box1.x, box2.x)
    yA = max(box1.y, box2.y)
    xB = min(box1.x + box1.width, box2.x + box2.width)
    yB = min(box1.y + box1.height, box2.y + box2.height)

    inter_w = max(0.0, xB - xA)
    inter_h = max(0.0, yB - yA)
    inter_area = inter_w * inter_h

    if inter_area <= 0.0:
        return 0.0

    area1 = box1.width * box1.height
    area2 = box2.width * box2.height
    union_area = area1 + area2 - inter_area

    return inter_area / union_area if union_area > 0 else 0.0


def deduplicate_waste_boxes(
    waste_dets: List[DetectedObject],
    iou_threshold: float = 0.50
) -> List[DetectedObject]:
    """
    Suppresses duplicate overlapping detections for the same physical waste object.
    Preserves the detection with the highest confidence.
    NOTE: Never filters out person detections, only waste duplicates.
    """
    if len(waste_dets) <= 1:
        return waste_dets

    sorted_dets = sorted(waste_dets, key=lambda d: d.confidence, reverse=True)
    kept: List[DetectedObject] = []

    for candidate in sorted_dets:
        is_dup = False
        for k in kept:
            # Only deduplicate if they are similar classes and have high IoU
            if compute_iou(candidate.box, k.box) >= iou_threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(candidate)

    return kept


async def run_detection_pipeline(
    image: Image.Image,
    conf_threshold: float = 0.18
) -> DetectionResponse:
    """
    Executes the full dual-model vision pipeline on an image:
    1. Validates and records image properties.
    2. Runs Ultralytics Person Detection.
    3. Runs Roboflow Waste Detection.
    4. Merges and deduplicates waste predictions.
    5. Preserves all person detections without suppressing overlapping waste.
    6. Determines pipeline status (all_succeeded, partial_success, all_failed, no_objects_detected).
    """
    start_time = time.perf_counter()
    orig_width, orig_height = image.size

    # 1. Run Ultralytics Person Detection (Model A)
    person_detections, person_status = detect_people(
        image=image,
        conf_threshold=max(0.25, conf_threshold)
    )

    # 2. Run Roboflow Waste Detection (Model B)
    waste_detections, waste_status = await detect_waste(
        image=image,
        conf_threshold=conf_threshold
    )

    # Deduplicate waste detections intra-model
    filtered_waste = deduplicate_waste_boxes(waste_detections, iou_threshold=0.50)

    # Combine detections: Person detections first, then waste detections
    combined_detections: List[DetectedObject] = []
    combined_detections.extend(person_detections)
    combined_detections.extend(filtered_waste)

    # Calculate overall pipeline status
    model_statuses = {
        "person_model": person_status,
        "waste_model": waste_status
    }

    person_ok = person_status.status == "success"
    waste_ok = waste_status.status == "success"

    if person_ok and waste_ok:
        if len(combined_detections) == 0:
            pipeline_status = "no_objects_detected"
        else:
            pipeline_status = "all_succeeded"
    elif person_ok or waste_ok:
        pipeline_status = "partial_success"
    else:
        pipeline_status = "all_failed"

    total_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return DetectionResponse(
        success=len(combined_detections) > 0 or (person_ok and waste_ok),
        inference_time_ms=total_time_ms,
        image_width=orig_width,
        image_height=orig_height,
        confidence_threshold=conf_threshold,
        detections_count=len(combined_detections),
        detections=combined_detections,
        model_statuses=model_statuses,
        pipeline_status=pipeline_status,
        error=None if (person_ok and waste_ok) else (
            f"Person model: {person_status.error or 'OK'}; Waste model: {waste_status.error or 'OK'}"
        )
    )
