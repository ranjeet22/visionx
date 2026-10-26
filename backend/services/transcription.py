"""
Whistle Speech-to-Text Transcription Service
Integrates Cactus Compute's Whistle ASR model via the needle SDK.
Processes browser-recorded speech audio (WebM, Ogg, WAV, MP4) and returns transcript text.
"""

import io
import os
import time
import wave
import tempfile
import logging
from typing import Tuple, Optional
import av
import numpy as np

import needle
from backend.schemas.detection import TranscribeResponse

logger = logging.getLogger("visionx.transcription")

# Maximum allowed audio upload size: 10 MB
MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024

# Allowed audio mime prefixes / extensions
SUPPORTED_MIME_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp4",
    "audio/m4a",
    "audio/aac",
    "audio/mpeg",
    "audio/flac"
}


def convert_to_16k_mono_wav(audio_bytes: bytes) -> bytes:
    """
    Decodes arbitrary audio container format (WebM/Opus, Ogg, MP4, WAV) using PyAV
    and converts to 16 kHz mono 16-bit PCM WAV.
    """
    in_buf = io.BytesIO(audio_bytes)
    container = av.open(in_buf)

    if not container.streams.audio:
        raise ValueError("Provided file does not contain any valid audio streams.")

    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    out_buf = io.BytesIO()

    with wave.open(out_buf, "wb") as out_wf:
        out_wf.setnchannels(1)
        out_wf.setsampwidth(2)
        out_wf.setframerate(16000)

        for frame in container.decode(audio=0):
            resampled_frames = resampler.resample(frame)
            if resampled_frames:
                for rf in resampled_frames:
                    out_wf.writeframes(rf.to_ndarray().tobytes())

        # Flush any buffered frames in the resampler
        flushed_frames = resampler.resample(None)
        if flushed_frames:
            for rf in flushed_frames:
                out_wf.writeframes(rf.to_ndarray().tobytes())

    return out_buf.getvalue()


def transcribe_audio_clip(audio_bytes: bytes, content_type: Optional[str] = None) -> TranscribeResponse:
    """
    Validates, preprocesses, and transcribes speech audio using Cactus Compute Whistle.
    Cleans up all temporary files immediately.
    """
    start_time = time.perf_counter()

    # 1. Size validation
    if len(audio_bytes) == 0:
        return TranscribeResponse(
            success=False,
            text="",
            error="Received empty audio data. Please record speech and try again."
        )

    if len(audio_bytes) > MAX_AUDIO_SIZE_BYTES:
        return TranscribeResponse(
            success=False,
            text="",
            error=f"Audio file exceeds maximum size limit of {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)}MB."
        )

    # 2. Convert to 16 kHz mono WAV
    try:
        wav_data = convert_to_16k_mono_wav(audio_bytes)
    except Exception as e:
        logger.warning(f"Audio decoding/resampling failed: {e}")
        return TranscribeResponse(
            success=False,
            text="",
            error=f"Failed to decode audio stream: {str(e)}"
        )

    # 3. Transcribe with Whistle via temporary file
    temp_wav_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            temp_wav_path = tmp_file.name
            tmp_file.write(wav_data)

        # Transcribe using needle
        result = needle.transcribe(
            temp_wav_path,
            keywords=["VisionX", "recycle", "compost", "plastic", "cardboard", "bottle"]
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        raw_text = result.get("text", "").strip() if isinstance(result, dict) else str(result).strip()
        detected_lang = result.get("language") if isinstance(result, dict) else None

        if not raw_text:
            return TranscribeResponse(
                success=True,
                text="",
                language=detected_lang,
                duration_ms=elapsed_ms,
                error="No speech detected in audio recording."
            )

        return TranscribeResponse(
            success=True,
            text=raw_text,
            language=detected_lang,
            duration_ms=elapsed_ms,
            error=None
        )

    except Exception as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(f"Whistle transcription error: {e}")
        return TranscribeResponse(
            success=False,
            text="",
            duration_ms=elapsed_ms,
            error=f"Transcription failed: {str(e)}"
        )
    finally:
        # Strictly ensure temporary audio files are removed
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except Exception:
                pass
