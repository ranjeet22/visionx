from backend.services.person_detection import detect_people, get_person_model
from backend.services.waste_detection import detect_waste
from backend.services.detection_pipeline import run_detection_pipeline
from backend.services.transcription import transcribe_audio_clip

__all__ = [
    "detect_people",
    "get_person_model",
    "detect_waste",
    "run_detection_pipeline",
    "transcribe_audio_clip",
]
