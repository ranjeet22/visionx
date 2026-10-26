import os

# Set offline and disable telemetry before any tests or imports run
os.environ["YOLO_OFFLINE"] = "True"
os.environ["ULTRALYTICS_OFFLINE"] = "True"
os.environ["NEEDLE_TELEMETRY"] = "0"
os.environ["VISIONX_DEVICE"] = "cpu"
