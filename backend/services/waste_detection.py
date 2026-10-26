"""
Roboflow Waste Detection Service (Model B)
Connects to Roboflow Universe pretrained model:
ting-ting-s-workspace / yolo-waste-detection-28enj
Using official supported hosted inference with InferenceHTTPClient / REST API.
"""

import io
import time
import base64
import logging
from typing import List, Tuple, Dict, Any, Optional
from PIL import Image
import httpx

from backend import config
from backend.schemas.detection import BoundingBox, DetectedObject, ModelStatus
from backend.knowledge.waste_knowledge import resolve_waste_item

logger = logging.getLogger("visionx.waste_detection")


def _image_to_base64(image: Image.Image) -> str:
    """Encodes PIL Image to base64 JPEG string for inference transmission."""
    buffer = io.BytesIO()
    # Save as JPEG with good quality
    image.save(buffer, format="JPEG", quality=90)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


async def detect_waste(
    image: Image.Image,
    conf_threshold: float = 0.18
) -> Tuple[List[DetectedObject], ModelStatus]:
    """
    Runs waste detection using the Roboflow hosted inference service.
    Handles credential validation, network errors, timeouts, and result normalization.
    """
    start_time = time.perf_counter()
    model_name = f"{config.ROBOFLOW_PROJECT}/{config.ROBOFLOW_VERSION}"

    # Verify API key configuration
    api_key = config.ROBOFLOW_API_KEY
    if not api_key or api_key == "your_api_key_here":
        return [], ModelStatus(
            status="failed",
            model_name=model_name,
            error="ROBOFLOW_API_KEY is not configured in backend environment (.env).",
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

    # Encode image
    try:
        b64_img = _image_to_base64(image)
    except Exception as e:
        return [], ModelStatus(
            status="failed",
            model_name=model_name,
            error=f"Failed to encode image for Roboflow API: {str(e)}",
            inference_time_ms=0.0,
            detections_count=0
        )

    # Primary official hosted endpoint: detect.roboflow.com
    endpoint = f"https://detect.roboflow.com/{config.ROBOFLOW_PROJECT}/{config.ROBOFLOW_VERSION}"
    params = {
        "api_key": api_key,
        "confidence": conf_threshold,
        "format": "json"
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                endpoint,
                params=params,
                content=b64_img,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            inference_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if resp.status_code == 401:
                return [], ModelStatus(
                    status="failed",
                    model_name=model_name,
                    error="Roboflow authentication failed (HTTP 401). Please verify your ROBOFLOW_API_KEY.",
                    inference_time_ms=inference_ms,
                    detections_count=0
                )
            elif resp.status_code == 403:
                return [], ModelStatus(
                    status="failed",
                    model_name=model_name,
                    error="Roboflow access forbidden (HTTP 403). Check project permissions or workspace access.",
                    inference_time_ms=inference_ms,
                    detections_count=0
                )
            elif resp.status_code == 404:
                return [], ModelStatus(
                    status="failed",
                    model_name=model_name,
                    error=f"Roboflow model not found (HTTP 404): {config.ROBOFLOW_PROJECT}/{config.ROBOFLOW_VERSION}.",
                    inference_time_ms=inference_ms,
                    detections_count=0
                )
            elif resp.status_code == 429:
                return [], ModelStatus(
                    status="failed",
                    model_name=model_name,
                    error="Roboflow API rate limit exceeded (HTTP 429). Please try again shortly.",
                    inference_time_ms=inference_ms,
                    detections_count=0
                )
            elif resp.status_code != 200:
                return [], ModelStatus(
                    status="failed",
                    model_name=model_name,
                    error=f"Roboflow API returned HTTP {resp.status_code}: {resp.text[:200]}",
                    inference_time_ms=inference_ms,
                    detections_count=0
                )

            data = resp.json()
    except httpx.TimeoutException:
        inference_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return [], ModelStatus(
            status="failed",
            model_name=model_name,
            error="Roboflow inference request timed out after 20 seconds.",
            inference_time_ms=inference_ms,
            detections_count=0
        )
    except Exception as e:
        inference_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(f"Roboflow inference call exception: {e}")
        return [], ModelStatus(
            status="failed",
            model_name=model_name,
            error=f"Network/client error communicating with Roboflow: {str(e)}",
            inference_time_ms=inference_ms,
            detections_count=0
        )

    # Process returned predictions
    raw_predictions = data.get("predictions", [])
    waste_detections: List[DetectedObject] = []
    class_instance_counts: Dict[str, int] = {}

    for pred in raw_predictions:
        class_name = pred.get("class", "waste")
        confidence = float(pred.get("confidence", 0.0))
        class_id = pred.get("class_id")

        # Roboflow coordinates are center-based: x, y, width, height
        cx = float(pred.get("x", 0.0))
        cy = float(pred.get("y", 0.0))
        bw = float(pred.get("width", 0.0))
        bh = float(pred.get("height", 0.0))

        # Check if coordinates are in pixels or already normalized [0..1]
        if cx > 1.0 or cy > 1.0 or bw > 1.0 or bh > 1.0:
            top_left_x = max(0.0, min(1.0, (cx - (bw / 2.0)) / orig_width))
            top_left_y = max(0.0, min(1.0, (cy - (bh / 2.0)) / orig_height))
            norm_w = max(0.0, min(1.0, bw / orig_width))
            norm_h = max(0.0, min(1.0, bh / orig_height))
        else:
            top_left_x = max(0.0, min(1.0, cx - (bw / 2.0)))
            top_left_y = max(0.0, min(1.0, cy - (bh / 2.0)))
            norm_w = max(0.0, min(1.0, bw))
            norm_h = max(0.0, min(1.0, bh))

        bbox = BoundingBox(
            x=round(top_left_x, 4),
            y=round(top_left_y, 4),
            width=round(norm_w, 4),
            height=round(norm_h, 4)
        )

        instance_count = class_instance_counts.get(class_name, 0) + 1
        class_instance_counts[class_name] = instance_count

        resolved = resolve_waste_item(
            model_class_name=class_name,
            confidence=confidence,
            box=bbox,
            class_id=class_id,
            instance_index=instance_count,
            model_source="roboflow_waste"
        )
        waste_detections.append(resolved)

    status = ModelStatus(
        status="success",
        model_name=model_name,
        inference_time_ms=inference_ms,
        detections_count=len(waste_detections)
    )

    return waste_detections, status
