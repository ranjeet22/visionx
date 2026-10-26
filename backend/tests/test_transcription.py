"""
Tests for Whistle Speech-to-Text Transcription Service (Cactus Compute needle).
Covers:
- Valid audio recording transcription
- Silent / empty audio handling
- Malformed / corrupted audio stream handling
- File size boundary enforcement (> 10MB)
"""

import io
import wave
import struct
import pytest
from unittest.mock import patch

from backend.services.transcription import (
    transcribe_audio_clip,
    convert_to_16k_mono_wav,
    MAX_AUDIO_SIZE_BYTES
)


def generate_test_wav_bytes(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generates synthetic 16kHz mono 16-bit PCM WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        num_samples = int(duration_sec * sample_rate)
        # Low-amplitude sine wave
        samples = [int(1000 * (i % 20)) for i in range(num_samples)]
        wf.writeframes(struct.pack(f"<{num_samples}h", *samples))
    return buf.getvalue()


def test_empty_audio_bytes():
    """Empty audio payload should return an informative error."""
    res = transcribe_audio_clip(b"", content_type="audio/webm")
    assert res.success is False
    assert "empty" in res.error.lower()


def test_oversized_audio_bytes():
    """Audio exceeding 10MB limit must be rejected safely."""
    fake_huge_audio = b"\x00" * (MAX_AUDIO_SIZE_BYTES + 1024)
    res = transcribe_audio_clip(fake_huge_audio, content_type="audio/wav")
    assert res.success is False
    assert "exceeds" in res.error.lower()


def test_malformed_corrupt_audio():
    """Corrupted garbage bytes must be rejected gracefully without crash."""
    garbage = b"RIFF\x00\x00\x00\x00NOT_AUDIO_GARBAGE_PAYLOAD"
    res = transcribe_audio_clip(garbage, content_type="audio/wav")
    assert res.success is False
    assert "failed" in res.error.lower() or "decode" in res.error.lower()


def test_silent_audio_transcription():
    """Synthetic silence should process cleanly and note that no speech was detected."""
    wav_bytes = generate_test_wav_bytes(duration_sec=0.5)

    with patch("needle.transcribe", return_value={"text": "", "language": "en"}):
        res = transcribe_audio_clip(wav_bytes, content_type="audio/wav")
        assert res.success is True
        assert res.text == ""
        assert "no speech" in res.error.lower()


def test_successful_transcription():
    """Mocked successful Whistle transcription returns text."""
    wav_bytes = generate_test_wav_bytes(duration_sec=1.5)

    mock_whistle_output = {
        "text": "How do I recycle this plastic bottle?",
        "language": "en",
        "ttft_ms": 12.5,
        "decode_tps": 45.0
    }

    with patch("needle.transcribe", return_value=mock_whistle_output):
        res = transcribe_audio_clip(wav_bytes, content_type="audio/wav")
        assert res.success is True
        assert res.text == "How do I recycle this plastic bottle?"
        assert res.language == "en"
        assert res.error is None
