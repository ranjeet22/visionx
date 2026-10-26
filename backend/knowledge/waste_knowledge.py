"""
VisionX Knowledge Mapping Engine
Maps dual-model detections (Ultralytics Person + Roboflow Waste) to structured disposal intelligence.
Ensures strict separation between waste items, non-waste (Person), and unverified classes.
"""

import re
from typing import Dict, Any, List, Optional
from backend.schemas.detection import BoundingBox, DetectedObject

# Structured waste knowledge repository for verified municipal waste classes
WASTE_KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    "plastic_bottle": {
        "display_name": "Plastic Beverage Bottle",
        "waste_category": "recyclable",
        "material": "Polyethylene Terephthalate (PET #1)",
        "material_verified": False,  # Polymer grade cannot be 100% verified purely from visual scan
        "disposal_method": "Recycle in curbside plastic recycling bin",
        "recycling_guidance": "Clear and translucent PET bottles are widely recyclable. Empty all liquids completely and replace the cap tightly.",
        "preparation_steps": [
            "Empty all liquid contents completely",
            "Rinse briefly with clean water to remove sugary residue",
            "Crush the bottle flat to conserve bin space",
            "Screw the plastic cap back on securely before binning"
        ],
        "contamination_warning": "Residual liquids contaminate dry paper and cardboard bales during collection compactions.",
        "reusability": "Can be refilled if rated food-safe, though single-use PET bottles degrade with repeated washing.",
        "environmental_impact": "Recycling 1 ton of PET plastic saves ~3.8 barrels of crude oil and cuts CO2 emissions by up to 67%.",
        "special_handling": None,
        "policy_status": "general-guidance",
        "mapping_status": "verified",
        "source": "Association of Plastic Recyclers (APR) & EPA Recycling Guidelines",
        "source_url": "https://plasticsrecycling.org"
    },
    "plastic_wrapper": {
        "display_name": "Flexible Plastic Film / Wrapper",
        "waste_category": "special-handling",
        "material": "Low-Density Polyethylene (LDPE #4) / Polypropylene Film",
        "material_verified": False,
        "disposal_method": "Drop off at retail grocery soft-plastic collection points",
        "recycling_guidance": "Flexible plastic films cannot be sorted in municipal single-stream curbside bins as they tangle in rotating sorting disc screens.",
        "preparation_steps": [
            "Empty all crumbs and food residue",
            "Ensure the wrapper is clean and dry",
            "Perform scrunch test: if it scrunches into a ball and bounces back slowly, take to soft-plastic drop-off",
            "Do NOT place in standard curbside blue bins"
        ],
        "contamination_warning": "MAJOR SORTING HAZARD: Plastic films tangle around sorting facility trommels and disc screens, forcing facility shutdowns.",
        "reusability": "Low reusability for snack wrappers; resealable bags can be washed and reused.",
        "environmental_impact": "Plastic films take up to 500 years to decompose in landfills and fragment into persistent microplastics.",
        "special_handling": "Grocery store / supermarket drop-off collection point only.",
        "policy_status": "general-guidance",
        "mapping_status": "verified",
        "source": "EPA Municipal Solid Waste Guide & Wrap UK",
        "source_url": "https://www.epa.gov/recycle"
    },
    "plastic_container": {
        "display_name": "Rigid Plastic Container / Tub",
        "waste_category": "recyclable",
        "material": "High-Density Polyethylene (HDPE #2) / Polypropylene (PP #5)",
        "material_verified": False,
        "disposal_method": "Recycle in curbside plastics container bin",
        "recycling_guidance": "Rigid plastic food containers, yogurt tubs, and detergent bottles are accepted in most curbside programs when thoroughly scraped and rinsed.",
        "preparation_steps": [
            "Scrape out all leftover food contents",
            "Rinse clean with cold water",
            "Remove foil seal or peel-off film liners"
        ],
        "contamination_warning": "Food residue causes mold and odor, contaminating entire recycling loads.",
        "reusability": "Durable tubs make convenient reusable storage containers for home items.",
        "environmental_impact": "Recycled HDPE and PP plastics reduce virgin resin production and landfill load.",
        "special_handling": None,
        "policy_status": "general-guidance",
        "mapping_status": "verified",
        "source": "Sustainable Packaging Coalition (How2Recycle)",
        "source_url": "https://how2recycle.info"
    },
    "cardboard": {
        "display_name": "Cardboard Packaging / Box",
        "waste_category": "recyclable",
        "material": "Corrugated Cardboard / Kraft Fiberboard",
        "material_verified": True,
        "disposal_method": "Recycle in dry paper & cardboard bin",
        "recycling_guidance": "Clean, dry cardboard is highly valuable for domestic paper mills. Keep dry and flattened.",
        "preparation_steps": [
            "Remove plastic shipping tape, bubble wrap, and foam inserts",
            "Flatten all boxes completely to maximize transport efficiency",
            "Keep dry and protected from rain",
            "Tear off and discard greasy sections (e.g. pizza oil stains) into general trash"
        ],
        "contamination_warning": "Grease and food oils permanently ruin paper fibers during the water pulping process.",
        "reusability": "Sturdy boxes can be reused repeatedly for shipping and storage.",
        "environmental_impact": "Recycling 1 ton of cardboard saves 17 mature trees, 7,000 gallons of water, and 4,000 kWh of energy.",
        "special_handling": None,
        "policy_status": "general-guidance",
        "mapping_status": "verified",
        "source": "American Forest & Paper Association (AF&PA)",
        "source_url": "https://www.afandpa.org"
    },
    "paper": {
        "display_name": "Paper / Document Waste",
        "waste_category": "recyclable",
        "material": "Cellulose Paper Fiber",
        "material_verified": True,
        "disposal_method": "Recycle in dry paper bin",
        "recycling_guidance": "Newspapers, magazines, office paper, and non-waxed paper can be recycled. Keep clean and dry.",
        "preparation_steps": [
            "Remove metal clips or thick plastic binders",
            "Keep dry and clean",
            "Do not shred unless containing sensitive private information"
        ],
        "contamination_warning": "Wet or food-soiled paper cannot be processed and must be composted or placed in trash.",
        "reusability": "Single-sided printed paper can be used as scratch paper.",
        "environmental_impact": "Recycled paper reduces deforestation, water consumption, and greenhouse gas emissions.",
        "special_handling": None,
        "policy_status": "general-guidance",
        "mapping_status": "verified",
        "source": "EPA Paper Recycling Guidelines",
        "source_url": "https://www.epa.gov/recycle/how-do-i-recycle-common-recyclables"
    },
    "metal_can": {
        "display_name": "Metal / Aluminium Beverage Can",
        "waste_category": "recyclable",
        "material": "Aluminium / Tin-plated Steel",
        "material_verified": True,
        "disposal_method": "Recycle in metal / dry recyclables bin",
        "recycling_guidance": "Metals are infinitely recyclable without loss of material properties. Empty and rinse lightly.",
        "preparation_steps": [
            "Empty any remaining liquids completely",
            "Quick rinse with cold water",
            "Push metal lids inside food cans",
            "No need to crush aluminium cans if your municipality uses optical sorting"
        ],
        "contamination_warning": "Rotting food scraps inside tin cans attract pests and create sanitary hazards for MRF workers.",
        "reusability": "Aluminium cans can be remelted and back on store shelves within 60 days.",
        "environmental_impact": "Recycling aluminium saves 95% of the energy needed to make new aluminium from bauxite ore.",
        "special_handling": None,
        "policy_status": "general-guidance",
        "mapping_status": "verified",
        "source": "The Aluminum Association & Can Manufacturers Institute",
        "source_url": "https://www.aluminum.org"
    },
    "glass_bottle": {
        "display_name": "Glass Bottle / Jar",
        "waste_category": "recyclable",
        "material": "Soda-Lime Glass",
        "material_verified": True,
        "disposal_method": "Recycle in designated glass recycling bin",
        "recycling_guidance": "Container glass is 100% recyclable. Separate metal or plastic lids if required by local guidelines.",
        "preparation_steps": [
            "Empty liquids and rinse clean",
            "Remove corks or bulky pump tops",
            "Never mix with window glass, Pyrex cookware, or drinking glasses (different melting points)"
        ],
        "contamination_warning": "Ceramics, borosilicate glass (Pyrex), and lightbulbs cannot melt in standard cullet furnaces and ruin glass batches.",
        "reusability": "Glass jars can be sterilized and reused indefinitely for pantry food storage.",
        "environmental_impact": "Recycled glass cullet melts at lower temperatures, saving 20% to 30% kiln energy.",
        "special_handling": None,
        "policy_status": "general-guidance",
        "mapping_status": "verified",
        "source": "Glass Packaging Institute (GPI)",
        "source_url": "https://www.gpi.org"
    },
    "organic_waste": {
        "display_name": "Organic / Food Waste",
        "waste_category": "organic",
        "material": "Biodegradable Organic Biomass",
        "material_verified": True,
        "disposal_method": "Dispose in municipal green compost bin or home compost pile",
        "recycling_guidance": "Fruit and vegetable peelings, coffee grounds, and organic food scraps generate nutrient-rich compost.",
        "preparation_steps": [
            "Remove all plastic packaging, produce stickers, and twist ties",
            "Collect in a breathable kitchen caddy or certified BPI-compostable bag",
            "Check local rules on whether cooked meat, bones, or dairy are accepted in municipal green bins"
        ],
        "contamination_warning": "Non-compostable plastic stickers and bags contaminate organic compost, resulting in microplastic-polluted soil.",
        "reusability": "Composting converts scraps into nutrient-rich soil amendment.",
        "environmental_impact": "Diverting organics from landfills prevents anaerobic decomposition and massive methane greenhouse emissions.",
        "special_handling": None,
        "policy_status": "general-guidance",
        "mapping_status": "verified",
        "source": "US Composting Council & EPA Organics Reduction",
        "source_url": "https://www.compostingcouncil.org"
    },
    "e_waste": {
        "display_name": "Electronic Waste / Battery",
        "waste_category": "special-handling",
        "material": "Lithium-ion / Heavy Metals / Circuit Boards",
        "material_verified": False,
        "disposal_method": "Take to authorized municipal e-waste or retail battery drop-off",
        "recycling_guidance": "NEVER dispose in curbside recycling or trash bins. Lithium batteries present extreme fire hazards when crushed in garbage trucks.",
        "preparation_steps": [
            "Tape exposed terminals of loose batteries with clear non-conductive tape",
            "Store in a cool, dry place away from flammable materials",
            "Take directly to certified drop-off collection locations (e.g. Call2Recycle, Best Buy, or civic amenity depot)"
        ],
        "contamination_warning": "CRITICAL FIRE HAZARD: Crushed lithium-ion batteries ignite volatile fires in compactor trucks and sorting conveyor lines.",
        "reusability": "Working electronics can be refurbished, donated, or traded in.",
        "environmental_impact": "Recovers rare earth minerals (cobalt, lithium, gold) and prevents toxic lead/cadmium soil leaching.",
        "special_handling": "Designated hazardous / e-waste drop-off depot only.",
        "policy_status": "general-guidance",
        "mapping_status": "verified",
        "source": "Call2Recycle & EPA Universal Waste Rules",
        "source_url": "https://www.call2recycle.org"
    },
    "general_waste": {
        "display_name": "General Residual Waste / Trash",
        "waste_category": "residual",
        "material": "Composite / Non-Recyclable Residuals",
        "material_verified": False,
        "disposal_method": "Dispose in black/gray general landfill trash bin",
        "recycling_guidance": "Non-recyclable composite packaging, heavily soiled materials, and non-recoverable items belong in residual municipal trash.",
        "preparation_steps": [
            "Ensure no hazardous materials or batteries are mixed in",
            "Bag securely to prevent litter and odor"
        ],
        "contamination_warning": "Attempting to 'wishcycle' non-recyclable trash into blue recycling bins degrades legitimate recyclables.",
        "reusability": None,
        "environmental_impact": "Landfilled waste contributes to long-term landfill volume and municipal disposal costs.",
        "special_handling": None,
        "policy_status": "general-guidance",
        "mapping_status": "verified",
        "source": "Municipal Solid Waste Management Guidelines",
        "source_url": None
    }
}

# Alias map for normalized class name lookup
CLASS_ALIASES: Dict[str, str] = {
    # Plastic bottle aliases
    "plasticbottle": "plastic_bottle",
    "bottle": "plastic_bottle",
    "petbottle": "plastic_bottle",
    "waterbottle": "plastic_bottle",
    "plasticbeveragebottle": "plastic_bottle",
    
    # Wrapper / Film
    "plasticwrapper": "plastic_wrapper",
    "wrapper": "plastic_wrapper",
    "plasticfilm": "plastic_wrapper",
    "film": "plastic_wrapper",
    "plasticbag": "plastic_wrapper",
    "bag": "plastic_wrapper",
    "softplastic": "plastic_wrapper",
    "pouch": "plastic_wrapper",
    
    # Plastic containers
    "plasticcontainer": "plastic_container",
    "plastic": "plastic_container",
    "cup": "plastic_container",
    "tub": "plastic_container",
    "clamshell": "plastic_container",
    "disposablecontainer": "plastic_container",
    "jug": "plastic_container",
    
    # Cardboard & paper
    "cardboard": "cardboard",
    "cardboardbox": "cardboard",
    "box": "cardboard",
    "corrugatedcardboard": "cardboard",
    "papercardboard": "cardboard",
    "paper": "paper",
    "document": "paper",
    "newspaper": "paper",
    "carton": "cardboard",
    "packaging": "cardboard",
    
    # Metal
    "metal": "metal_can",
    "metalcan": "metal_can",
    "can": "metal_can",
    "tin": "metal_can",
    "tincan": "metal_can",
    "aluminumcan": "metal_can",
    "aluminiumcan": "metal_can",
    "beveragecan": "metal_can",
    "metalwaste": "metal_can",
    "foil": "metal_can",
    
    # Glass
    "glass": "glass_bottle",
    "glassbottle": "glass_bottle",
    "glassjar": "glass_bottle",
    "jar": "glass_bottle",
    "glasswaste": "glass_bottle",
    
    # Organics
    "organic": "organic_waste",
    "organicwaste": "organic_waste",
    "food": "organic_waste",
    "foodwaste": "organic_waste",
    "peel": "organic_waste",
    "fruit": "organic_waste",
    
    # E-Waste
    "battery": "e_waste",
    "ewaste": "e_waste",
    "electronic": "e_waste",
    "electronics": "e_waste",
    "cell": "e_waste",
    "cable": "e_waste",
    "wire": "e_waste",
    
    # General waste
    "trash": "general_waste",
    "waste": "general_waste",
    "garbage": "general_waste",
    "residual": "general_waste",
    "litter": "general_waste"
}


def normalize_class_name(name: str) -> str:
    """Safely normalizes a model class label by lowering, stripping, and removing non-alphanumeric chars."""
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower().strip())


def is_person_class(class_name: str, class_id: Optional[int] = None) -> bool:
    """Checks whether the detected class represents a human person."""
    norm = normalize_class_name(class_name)
    return norm in ["person", "human", "people"] or (class_id == 0 and norm in ["person", "0"])


def resolve_person_item(
    confidence: float,
    box: BoundingBox,
    instance_index: int = 1,
    model_source: str = "ultralytics_person"
) -> DetectedObject:
    """
    Creates a non-waste DetectedObject for a detected person.
    A person is NOT a waste item, so waste disposal guidance does not apply.
    """
    display_name = "Person" if instance_index <= 1 else f"Person #{instance_index}"
    explanation = "Person detected. This is not a waste item, so waste disposal guidance does not apply."
    stable_id = f"person-{instance_index}"

    return DetectedObject(
        id=stable_id,
        instance_index=instance_index,
        model_source=model_source,
        class_id=0,
        model_class_name="person",
        display_name=display_name,
        confidence=round(confidence, 4),
        box=box,
        bbox=box,
        waste_category=None,
        material=None,
        material_verified=False,
        disposal_method=None,
        recycling_guidance=None,
        guidance=explanation,
        preparation_steps=[],
        contamination_warning=None,
        reusability=None,
        environmental_impact=None,
        special_handling=None,
        policy_status="unknown",
        mapping_status="verified",
        source="Ultralytics Pretrained COCO Detector",
        source_url=None
    )


def resolve_unknown_waste_item(
    model_class_name: str,
    confidence: float,
    class_id: Optional[int],
    box: BoundingBox,
    instance_index: int = 1,
    model_source: str = "roboflow_waste"
) -> DetectedObject:
    """
    Creates a cautious DetectedObject for an unknown or unmapped waste class.
    Preserves original model label for traceability without guessing disposal methods.
    """
    norm = normalize_class_name(model_class_name)
    stable_id = f"waste-unknown-{norm or 'item'}-{instance_index}"
    display = f"{model_class_name} (Unverified Item)"
    cautious_msg = f"Item detected as '{model_class_name}', but its disposal classification has not been verified. Physical inspection and local municipal confirmation are required before sorting."

    return DetectedObject(
        id=stable_id,
        instance_index=instance_index,
        model_source=model_source,
        class_id=class_id,
        model_class_name=model_class_name,
        display_name=display,
        confidence=round(confidence, 4),
        box=box,
        bbox=box,
        waste_category="uncertain",
        material="Unverified Material",
        material_verified=False,
        disposal_method="Inspect physically and check local municipal sorting regulations",
        recycling_guidance=cautious_msg,
        guidance=cautious_msg,
        preparation_steps=[
            "Inspect physical item for resin identification codes (#1 - #7) or recycling stamps",
            "Verify local sanitation authority rules before placing in recycling bins"
        ],
        contamination_warning="Sorting unverified materials into recycling streams risks contaminating batches.",
        reusability=None,
        environmental_impact="Proper segregation prevents non-recyclables from degrading high-grade recycled commodities.",
        special_handling="Manual inspection required",
        policy_status="unknown",
        mapping_status="unverified",
        source="VisionX Deterministic Guardrails",
        source_url=None
    )


def resolve_waste_item(
    model_class_name: str,
    confidence: float,
    box: BoundingBox,
    class_id: Optional[int] = None,
    instance_index: int = 1,
    model_source: str = "roboflow_waste"
) -> DetectedObject:
    """
    Resolves any detected object into a standardized DetectedObject.
    - If person, delegates to resolve_person_item.
    - If known waste class, retrieves verified knowledge.
    - If unknown, delegates to resolve_unknown_waste_item.
    """
    # 1. Check for Person detection
    if is_person_class(model_class_name, class_id):
        return resolve_person_item(
            confidence=confidence,
            box=box,
            instance_index=instance_index,
            model_source=model_source
        )

    # 2. Normalize and check aliases
    norm = normalize_class_name(model_class_name)
    canonical_key = CLASS_ALIASES.get(norm)

    if not canonical_key:
        # Check direct match in WASTE_KNOWLEDGE_BASE
        if norm in WASTE_KNOWLEDGE_BASE:
            canonical_key = norm
        else:
            # Substring heuristic for compound labels
            for alias_key, target in CLASS_ALIASES.items():
                if alias_key in norm or norm in alias_key:
                    canonical_key = target
                    break

    # 3. If still not matched, handle as unmapped/unknown
    if not canonical_key or canonical_key not in WASTE_KNOWLEDGE_BASE:
        return resolve_unknown_waste_item(
            model_class_name=model_class_name,
            confidence=confidence,
            class_id=class_id,
            box=box,
            instance_index=instance_index,
            model_source=model_source
        )

    # 4. Known waste class resolution
    k = WASTE_KNOWLEDGE_BASE[canonical_key]
    display_title = k["display_name"]
    if instance_index > 1:
        display_title = f"{display_title} #{instance_index}"

    stable_id = f"waste-{canonical_key}-{instance_index}"

    return DetectedObject(
        id=stable_id,
        instance_index=instance_index,
        model_source=model_source,
        class_id=class_id,
        model_class_name=model_class_name,
        display_name=display_title,
        confidence=round(confidence, 4),
        box=box,
        bbox=box,
        waste_category=k["waste_category"],
        material=k["material"],
        material_verified=k["material_verified"],
        disposal_method=k["disposal_method"],
        recycling_guidance=k["recycling_guidance"],
        guidance=f"{k['disposal_method']} - {k['recycling_guidance']}",
        preparation_steps=list(k["preparation_steps"]),
        contamination_warning=k.get("contamination_warning"),
        reusability=k.get("reusability"),
        environmental_impact=k["environmental_impact"],
        special_handling=k.get("special_handling"),
        policy_status=k["policy_status"],
        mapping_status=k["mapping_status"],
        source=k["source"],
        source_url=k.get("source_url")
    )
