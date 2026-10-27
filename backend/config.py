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

# MySQL Database Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1").strip()
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306").strip() or 3306)
MYSQL_USER = os.getenv("MYSQL_USER", "root").strip()
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "").strip()
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "visionx").strip()

# Session & Cookie Configuration
SESSION_SECRET = os.getenv("SESSION_SECRET", "visionx-super-secret-key-change-in-production-32b").strip()
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "visionx_session").strip()
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", str(7 * 24 * 3600)).strip())
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").strip()

# Email & SMTP Configuration for OTP Delivery
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587").strip() or 587)
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", "VisionX <no-reply@visionx.local>").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

# Frontend Origin for CORS
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:5173").strip()
