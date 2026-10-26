import os
import sys
from pathlib import Path

# Ensure environment variables are set immediately before any modules load
os.environ["YOLO_OFFLINE"] = "true"
os.environ["ULTRALYTICS_OFFLINE"] = "true"
os.environ["NEEDLE_TELEMETRY"] = "0"
os.environ["VISIONX_DEVICE"] = "cpu"

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
