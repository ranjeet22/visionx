"""
Unit tests for the VisionX Knowledge Base and Normalization Engine.
Tests:
- Known waste classes (plastic bottle, cardboard, metal can, glass, organic)
- Robust normalization (case, hyphens, underscores, extra spaces)
- Person detection (strictly classified as non-waste with null category)
- Unknown waste classes (cautious fallback, unverified material, no guessed disposal method)
"""

import pytest
from backend.schemas.detection import BoundingBox
from backend.knowledge.waste_knowledge import (
    resolve_waste_item,
    resolve_person_item,
    resolve_unknown_waste_item,
    normalize_class_name,
    is_person_class,
    WASTE_KNOWLEDGE_BASE
)

DUMMY_BOX = BoundingBox(x=0.1, y=0.1, width=0.5, height=0.5)


def test_normalize_class_name():
    assert normalize_class_name("Plastic_Bottle") == "plasticbottle"
    assert normalize_class_name("cardboard-box") == "cardboardbox"
    assert normalize_class_name("  ALUMINUM CAN  ") == "aluminumcan"
    assert normalize_class_name("") == ""


def test_person_special_handling():
    # Person detection must NEVER be classified as waste
    person_obj = resolve_person_item(
        confidence=0.92,
        box=DUMMY_BOX,
        instance_index=1
    )

    assert person_obj.display_name == "Person"
    assert person_obj.model_class_name == "person"
    assert person_obj.waste_category is None
    assert person_obj.material is None
    assert person_obj.material_verified is False
    assert person_obj.disposal_method is None
    assert person_obj.recycling_guidance is None
    assert len(person_obj.preparation_steps) == 0
    assert "not a waste item" in person_obj.guidance.lower()
    assert person_obj.model_source == "ultralytics_person"


def test_person_via_resolve_waste_item():
    # Test routing to person when passed to resolve_waste_item
    item = resolve_waste_item("person", confidence=0.88, box=DUMMY_BOX)
    assert item.model_class_name == "person"
    assert item.waste_category is None
    assert "not a waste item" in item.guidance.lower()


def test_known_waste_classes():
    # Plastic bottle
    bottle = resolve_waste_item("PlasticBottle", confidence=0.95, box=DUMMY_BOX)
    assert bottle.waste_category == "recyclable"
    assert "PET" in bottle.material
    assert bottle.material_verified is False  # Cannot verify plastic resin from vision alone
    assert len(bottle.preparation_steps) > 0
    assert "curbside" in bottle.disposal_method.lower()

    # Cardboard
    cardboard = resolve_waste_item("cardboard", confidence=0.89, box=DUMMY_BOX)
    assert cardboard.waste_category == "recyclable"
    assert cardboard.material_verified is True
    assert "Cardboard" in cardboard.display_name

    # Metal can
    metal = resolve_waste_item("metal_can", confidence=0.91, box=DUMMY_BOX)
    assert metal.waste_category == "recyclable"
    assert "Aluminium" in metal.material

    # Glass
    glass = resolve_waste_item("glass_bottle", confidence=0.85, box=DUMMY_BOX)
    assert glass.waste_category == "recyclable"
    assert "Glass" in glass.display_name

    # Organic
    organic = resolve_waste_item("organic_waste", confidence=0.87, box=DUMMY_BOX)
    assert organic.waste_category == "organic"
    assert "compost" in organic.disposal_method.lower()


def test_case_and_delimiter_insensitivity():
    variants = ["Plastic_Bottle", "plastic-bottle", "PLASTIC BOTTLE", "plasticbottle"]
    for v in variants:
        res = resolve_waste_item(v, confidence=0.9, box=DUMMY_BOX)
        assert res.waste_category == "recyclable", f"Failed for variant: {v}"
        assert "Bottle" in res.display_name


def test_unknown_waste_class():
    unknown = resolve_waste_item("quantum_flux_widget_xyz", confidence=0.77, box=DUMMY_BOX)
    assert unknown.model_class_name == "quantum_flux_widget_xyz"
    assert unknown.waste_category == "uncertain"
    assert unknown.material_verified is False
    assert unknown.mapping_status == "unverified"
    assert "not been verified" in unknown.guidance.lower()
    # Does not invent a disposal bin
    assert "check local municipal" in unknown.disposal_method.lower()
