"""
audio_classifier.py
────────────────────
Lightweight audio-content classifier that labels a file as one of:

    "speech"      — clear spoken words, minimal music/noise
    "vocals"      — singing / vocal performance over music
    "music"       — music-dominant, little or no speech
    "pure_sound"  — ambient / SFX / noise — no speech, no tonal music
    "mixed"       — substantial speech AND music/sound

Strategy (no heavy ML model required)
──────────────────────────────────────
1. Use Whisper's own transcription metadata:
   • segment-level no_speech_prob  → how much Whisper doubts it is speech
   • total spoken word count       → speech density proxy
2. Use librosa for spectral shape:
   • spectral_flatness             → music (low) vs noise (high)
   • zero_crossing_rate            → tonal (low) vs noisy (high)
   • RMS energy                    → silence detection
3. Combine signals with simple thresholds into a final label.

Dependencies: librosa, numpy  (both CPU-only, no GPU needed)
"""

from __future__ import annotations

import io
import os
import tempfile
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass  # librosa is lazy-imported so the module loads fast


# ── tuneable thresholds ────────────────────────────────────────────────────────
_SPEECH_WORD_DENSITY   = 0.8   # words-per-second above this → speech-heavy
_NO_SPEECH_PROB_THRESH = 0.60  # avg Whisper no_speech_prob above this → not speech
_FLATNESS_MUSIC_MAX    = 0.08  # spectral flatness below this → music-like
_FLATNESS_NOISE_MIN    = 0.30  # spectral flatness above this → noise-like
_ZCR_TONAL_MAX         = 0.12  # zero-crossing rate below this → tonal
_SILENCE_ENERGY_THRESH = 1e-4  # RMS below this → effectively silent frame
_SILENCE_RATIO_MAX     = 0.85  # if > 85 % of frames are silent → ambient/SFX


def _load_audio_array(source, extension: str, sr: int = 22_050):
    """
    Load audio into a numpy float32 array at sample-rate `sr`.
    Works with both file-path strings and BytesIO streams.
    Returns (y, sr) — same convention as librosa.load.
    """
    import librosa  # lazy import

    if isinstance(source, str):
        y, _ = librosa.load(source, sr=sr, mono=True)
        return y, sr

    # BytesIO / stream — write to a temp file because librosa needs a path
    source.seek(0)
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
        tmp.write(source.read())
        tmp_path = tmp.name
    try:
        y, _ = librosa.load(tmp_path, sr=sr, mono=True)
    finally:
        os.unlink(tmp_path)
    return y, sr


def _spectral_features(y: np.ndarray, sr: int) -> dict:
    """
    Compute the three spectral signals we use for classification.
    Returns a dict with keys: flatness, zcr, silence_ratio.
    """
    import librosa

    # Spectral flatness — low → music/tonal; high → noise/silence
    flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))

    # Zero-crossing rate — low → tonal; high → noisy
    zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))

    # Silence ratio — fraction of frames whose RMS is below the energy threshold
    rms = librosa.feature.rms(y=y)[0]
    silence_ratio = float(np.mean(rms < _SILENCE_ENERGY_THRESH))

    return {"flatness": flatness, "zcr": zcr, "silence_ratio": silence_ratio}


def _whisper_speech_signals(whisper_result: dict) -> dict:
    """
    Pull speech-quality signals from an already-computed Whisper result dict.
    Returns: words_per_second, avg_no_speech_prob, has_transcript.
    """
    segments = whisper_result.get("segments", [])
    text = whisper_result.get("text", "").strip()
    word_count = len(text.split()) if text else 0

    if segments:
        total_duration = max(s.get("end", 0) for s in segments) or 1.0
        avg_no_speech = float(
            np.mean([s.get("no_speech_prob", 0.0) for s in segments])
        )
    else:
        total_duration = 1.0
        avg_no_speech = 1.0  # no segments → Whisper found nothing

    return {
        "words_per_second": word_count / total_duration,
        "avg_no_speech_prob": avg_no_speech,
        "has_transcript": bool(text),
    }


def classify(
    source,
    extension: str,
    whisper_result: dict | None = None,
) -> dict:
    """
    Classify the audio content.

    Args:
        source:         File path (str) or BytesIO stream.
        extension:      File extension e.g. '.mp3'.
        whisper_result: Pre-computed Whisper result dict. If provided, reused
                        so Whisper is NOT run a second time.

    Returns a dict::

        {
            "label":       "speech" | "vocals" | "music" | "pure_sound" | "mixed",
            "confidence":  "high" | "medium" | "low",
            "signals": {
                "words_per_second": float,
                "avg_no_speech_prob": float,
                "spectral_flatness": float,
                "zero_crossing_rate": float,
                "silence_ratio": float,
            },
            "description": str   # human-readable one-liner
        }
    """
    # ── 1. spectral features (always computed) ─────────────────────────────────
    try:
        y, sr = _load_audio_array(source, extension)
        spec = _spectral_features(y, sr)
    except Exception as e:
        # librosa may fail on exotic codecs — degrade gracefully
        print(f"[WARNING] AudioClassifier: spectral analysis failed — {e}")
        spec = {"flatness": 0.0, "zcr": 0.0, "silence_ratio": 0.0}

    flat     = spec["flatness"]
    zcr      = spec["zcr"]
    sil_rat  = spec["silence_ratio"]

    # ── 2. Whisper speech signals ──────────────────────────────────────────────
    if whisper_result is not None:
        wsig = _whisper_speech_signals(whisper_result)
    else:
        # No Whisper result supplied — treat as no speech
        wsig = {"words_per_second": 0.0, "avg_no_speech_prob": 1.0, "has_transcript": False}

    wps       = wsig["words_per_second"]
    no_speech = wsig["avg_no_speech_prob"]

    # ── 3. Decision logic ──────────────────────────────────────────────────────
    is_speech_heavy  = wps >= _SPEECH_WORD_DENSITY and no_speech < _NO_SPEECH_PROB_THRESH
    is_speech_light  = wsig["has_transcript"] and not is_speech_heavy
    is_mostly_silent = sil_rat > _SILENCE_RATIO_MAX
    is_tonal         = flat < _FLATNESS_MUSIC_MAX and zcr < _ZCR_TONAL_MAX
    is_noisy         = flat > _FLATNESS_NOISE_MIN

    if is_mostly_silent and not wsig["has_transcript"]:
        label      = "pure_sound"
        confidence = "high"
        desc       = "Ambient / SFX / near-silent audio with no detectable speech or music"

    elif is_speech_heavy and not is_tonal:
        label      = "speech"
        confidence = "high"
        desc       = "Clear spoken-word content (podcast, lecture, interview, voice memo)"

    elif is_speech_heavy and is_tonal:
        label      = "vocals"
        confidence = "medium"
        desc       = "Vocal performance over music (song with lyrics, spoken-word poetry)"

    elif is_tonal and not wsig["has_transcript"]:
        label      = "music"
        confidence = "high"
        desc       = "Instrumental or tonal music — no significant speech detected"

    elif is_noisy and not wsig["has_transcript"]:
        label      = "pure_sound"
        confidence = "medium"
        desc       = "Noise / ambient sound with no speech or tonal music"

    elif is_speech_light and is_tonal:
        label      = "mixed"
        confidence = "medium"
        desc       = "Mixed audio — music with intermittent speech or narration"

    elif is_speech_light:
        label      = "mixed"
        confidence = "low"
        desc       = "Mixed or unclear — some speech detected alongside other sounds"

    else:
        label      = "pure_sound"
        confidence = "low"
        desc       = "Unclassified audio — no strong speech or music signal detected"

    return {
        "label": label,
        "confidence": confidence,
        "signals": {
            "words_per_second":      round(wps, 3),
            "avg_no_speech_prob":    round(no_speech, 3),
            "spectral_flatness":     round(flat, 4),
            "zero_crossing_rate":    round(zcr, 4),
            "silence_ratio":         round(sil_rat, 3),
        },
        "description": desc,
    }
