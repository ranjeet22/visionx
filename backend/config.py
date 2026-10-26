"""
VisionX Configuration Module
Loads and validates environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Disable telemetry and online checks for fast, offline startup
os.environ["YOLO_OFFLINE"] = "True"
os.environ["ULTRALYTICS_OFFLINE"] = "True"
os.environ["NEEDLE_TELEMETRY"] = "0"

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")

# LLM / Grok credentials
GROK_API = os.getenv("GROK_API") or os.getenv("XAI_API_KEY") or os.getenv("GROQ_API_KEY")

# Roboflow Configuration
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "").strip()
ROBOFLOW_WORKSPACE = os.getenv("ROBOFLOW_WORKSPACE", "ting-ting-s-workspace").strip()
ROBOFLOW_PROJECT = os.getenv("ROBOFLOW_PROJECT", "yolo-waste-detection-28enj").strip()
ROBOFLOW_VERSION = os.getenv("ROBOFLOW_VERSION", "1").strip()

# Ultralytics Configuration
ULTRALYTICS_MODEL = os.getenv("ULTRALYTICS_MODEL", "yolov8n.pt").strip()

# Device selection (defaults to CPU for predictable latency; override via VISIONX_DEVICE)
DEVICE = os.getenv("VISIONX_DEVICE", "cpu").strip()
