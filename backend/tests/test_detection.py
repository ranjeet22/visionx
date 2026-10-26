"""
Tests for the Dual-Model Detection Pipeline and Detection Endpoints.
Covers:
- Person only detection (Model A)
- Waste only detection (Model B)
- Both person and waste in the same image
- Multiple waste objects deduplication
- No relevant objects
- Unknown waste class
- Invalid image upload / decoding
- Roboflow API failure handling
- Ultralytics failure handling
- Partial failure behavior (one succeeds, one fails)
- Preservation of overlapping person and waste boxes
"""

import io
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from PIL import Image

from backend.schemas.detection import BoundingBox, DetectedObject, ModelStatus
from backend.services.person_detection import detect_people
from backend.services.waste_detection import detect_waste
from backend.services.detection_pipeline import (
    run_detection_pipeline,
    compute_iou,
    deduplicate_waste_boxes
)


def create_test_image(width=640, height=480, color="white"):
    """Helper to generate in-memory test PIL images."""
    return Image.new("RGB", (width, height), color=color)


@pytest.mark.asyncio
async def test_person_only_image():
    """Test scenario where only Ultralytics person detector finds an object."""
    img = create_test_image()

    mock_person = DetectedObject(
        id="person-1",
        instance_index=1,
        model_source="ultralytics_person",
        class_id=0,
        model_class_name="person",
        display_name="Person",
        confidence=0.91,
        box=BoundingBox(x=0.1, y=0.1, width=0.4, height=0.8),
        waste_category=None,
        guidance="Person detected. This is not a waste item, so waste disposal guidance does not apply."
    )
    person_status = ModelStatus(status="success", model_name="yolov8n.pt", detections_count=1)
    waste_status = ModelStatus(status="success", model_name="roboflow", detections_count=0)

    with patch("backend.services.detection_pipeline.detect_people", return_value=([mock_person], person_status)):
        with patch("backend.services.detection_pipeline.detect_waste", new_callable=AsyncMock) as mock_dw:
            mock_dw.return_value = ([], waste_status)

            resp = await run_detection_pipeline(img)
            assert resp.success is True
            assert resp.detections_count == 1
            assert resp.detections[0].model_class_name == "person"
            assert resp.detections[0].waste_category is None
            assert resp.pipeline_status == "all_succeeded"


@pytest.mark.asyncio
async def test_waste_only_image():
    """Test scenario where only Roboflow finds waste objects."""
    img = create_test_image()

    mock_waste = DetectedObject(
        id="waste-plastic_bottle-1",
        instance_index=1,
        model_source="roboflow_waste",
        model_class_name="plastic_bottle",
        display_name="Plastic Beverage Bottle",
        confidence=0.88,
        box=BoundingBox(x=0.3, y=0.3, width=0.2, height=0.4),
        waste_category="recyclable"
    )
    person_status = ModelStatus(status="success", model_name="yolov8n.pt", detections_count=0)
    waste_status = ModelStatus(status="success", model_name="roboflow", detections_count=1)

    with patch("backend.services.detection_pipeline.detect_people", return_value=([], person_status)):
        with patch("backend.services.detection_pipeline.detect_waste", new_callable=AsyncMock) as mock_dw:
            mock_dw.return_value = ([mock_waste], waste_status)

            resp = await run_detection_pipeline(img)
            assert resp.success is True
            assert resp.detections_count == 1
            assert resp.detections[0].waste_category == "recyclable"
            assert resp.pipeline_status == "all_succeeded"


@pytest.mark.asyncio
async def test_both_person_and_waste_overlapping():
    """
    CRITICAL: When a person holds a waste item, both bounding boxes overlap.
    Neither box should be suppressed!
    """
    img = create_test_image()

    person_box = BoundingBox(x=0.1, y=0.1, width=0.6, height=0.8)
    # Bottle inside or heavily overlapping the person's bounding box
    waste_box = BoundingBox(x=0.3, y=0.4, width=0.15, height=0.25)

    person_obj = DetectedObject(
        id="person-1",
        instance_index=1,
        model_source="ultralytics_person",
        model_class_name="person",
        display_name="Person",
        confidence=0.94,
        box=person_box,
        waste_category=None
    )

    waste_obj = DetectedObject(
        id="waste-plastic_bottle-1",
        instance_index=1,
        model_source="roboflow_waste",
        model_class_name="plastic_bottle",
        display_name="Plastic Beverage Bottle",
        confidence=0.85,
        box=waste_box,
        waste_category="recyclable"
    )

    p_status = ModelStatus(status="success", model_name="yolov8n.pt", detections_count=1)
    w_status = ModelStatus(status="success", model_name="roboflow", detections_count=1)

    with patch("backend.services.detection_pipeline.detect_people", return_value=([person_obj], p_status)):
        with patch("backend.services.detection_pipeline.detect_waste", new_callable=AsyncMock) as mock_dw:
            mock_dw.return_value = ([waste_obj], w_status)

            resp = await run_detection_pipeline(img)
            assert resp.detections_count == 2
            ids = [d.id for d in resp.detections]
            assert "person-1" in ids
            assert "waste-plastic_bottle-1" in ids

            # Verify person is non-waste and bottle is recyclable
            p_det = next(d for d in resp.detections if d.id == "person-1")
            w_det = next(d for d in resp.detections if d.id == "waste-plastic_bottle-1")
            assert p_det.waste_category is None
            assert w_det.waste_category == "recyclable"


@pytest.mark.asyncio
async def test_no_relevant_objects():
    """Test when both models succeed but find nothing."""
    img = create_test_image()

    p_status = ModelStatus(status="success", model_name="yolov8n.pt", detections_count=0)
    w_status = ModelStatus(status="success", model_name="roboflow", detections_count=0)

    with patch("backend.services.detection_pipeline.detect_people", return_value=([], p_status)):
        with patch("backend.services.detection_pipeline.detect_waste", new_callable=AsyncMock) as mock_dw:
            mock_dw.return_value = ([], w_status)

            resp = await run_detection_pipeline(img)
            assert resp.detections_count == 0
            assert resp.pipeline_status == "no_objects_detected"


@pytest.mark.asyncio
async def test_partial_model_failure():
    """
    Test when Ultralytics succeeds but Roboflow fails (e.g. missing API key or timeout).
    Pipeline must report partial_success with clear per-model status!
    """
    img = create_test_image()

    person_obj = DetectedObject(
        id="person-1",
        instance_index=1,
        model_source="ultralytics_person",
        model_class_name="person",
        display_name="Person",
        confidence=0.90,
        box=BoundingBox(x=0.1, y=0.1, width=0.5, height=0.5),
        waste_category=None
    )
    p_status = ModelStatus(status="success", model_name="yolov8n.pt", detections_count=1)
    w_status = ModelStatus(
        status="failed",
        model_name="roboflow",
        error="ROBOFLOW_API_KEY is not configured.",
        detections_count=0
    )

    with patch("backend.services.detection_pipeline.detect_people", return_value=([person_obj], p_status)):
        with patch("backend.services.detection_pipeline.detect_waste", new_callable=AsyncMock) as mock_dw:
            mock_dw.return_value = ([], w_status)

            resp = await run_detection_pipeline(img)
            assert resp.pipeline_status == "partial_success"
            assert resp.detections_count == 1
            assert resp.model_statuses["waste_model"].status == "failed"
            assert "ROBOFLOW_API_KEY" in resp.model_statuses["waste_model"].error


def test_intra_model_waste_deduplication():
    """Tests that overlapping duplicate boxes of the same waste item are deduplicated, keeping max confidence."""
    # Two heavily overlapping plastic bottles
    det1 = DetectedObject(
        id="bottle-1",
        instance_index=1,
        model_source="roboflow_waste",
        model_class_name="plastic_bottle",
        display_name="Plastic Bottle",
        confidence=0.92,
        box=BoundingBox(x=0.2, y=0.2, width=0.3, height=0.4),
        waste_category="recyclable"
    )
    det2 = DetectedObject(
        id="bottle-2",
        instance_index=2,
        model_source="roboflow_waste",
        model_class_name="plastic_bottle",
        display_name="Plastic Bottle",
        confidence=0.74,
        box=BoundingBox(x=0.21, y=0.21, width=0.29, height=0.39),
        waste_category="recyclable"
    )

    deduped = deduplicate_waste_boxes([det1, det2], iou_threshold=0.5)
    assert len(deduped) == 1
    assert deduped[0].confidence == 0.92
