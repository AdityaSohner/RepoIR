import os
import io
import tempfile

from app.ai.extractors import audio_classifier


class NoSpeechError(Exception):
    """
    Raised by AudioExtractor when an audio file contains no usable speech
    AND is not a vocal/singing performance.

    The ingestion pipeline catches this and skips embedding, returning a
    human-readable message to the caller instead of storing empty vectors.
    """
    pass


# ── Whisper singleton ──────────────────────────────────────────────────────────
_whisper_model = None


def _get_whisper_model(model_size: str = "base"):
    """Load the Whisper model once and cache it for the process lifetime."""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print(f"[*] Loading Whisper model '{model_size}' (first-time download may take a moment)...")
        _whisper_model = whisper.load_model(model_size)
        print("[+] Whisper model ready.")
    return _whisper_model


class AudioExtractor:
    """
    Transcribes audio files to text using OpenAI Whisper (local, no API key),
    then classifies the audio content type via AudioClassifier.

    Supported formats: .mp3, .mp4, .wav, .m4a, .ogg, .flac, .webm

    Output raw_text format injected into the ingestion pipeline::

        AUDIO_TYPE: speech
        AUDIO_CONFIDENCE: high
        AUDIO_DESCRIPTION: Clear spoken-word content (podcast, lecture ...)
        SIGNALS: wps=2.341 | no_speech=0.032 | flatness=0.0421 | zcr=0.089 | silence=0.041

        TRANSCRIPT:
        <whisper transcript here>

    This means the classification label, confidence, and signals are all
    embedded into the vector index and are retrievable by semantic search —
    e.g. "find music files" or "show me pure ambient recordings".
    """

    SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac", ".webm"}

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def extract(self, source, extension: str = None) -> dict:
        """
        Transcribe + classify the audio source.

        Args:
            source:    File path (str) or a BytesIO stream.
            extension: File extension e.g. '.mp3'. Required for stream sources.

        Returns:
            {
                "raw_text":  <enriched semantic text>,
                "metadata":  {
                    "file_type":         <ext>,
                    "audio_label":       "speech" | "vocals" | "music" | "pure_sound" | "mixed",
                    "audio_confidence":  "high" | "medium" | "low",
                    "audio_signals":     { ... },
                }
            }
        """
        if extension is None:
            if isinstance(source, str):
                extension = os.path.splitext(source)[1].lower()
            else:
                raise ValueError("Extension must be provided for stream audio sources")

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported audio format: {extension}")

        model = _get_whisper_model(self.model_size)

        # ── 1. Transcribe ──────────────────────────────────────────────────────
        whisper_result, tmp_path_used = self._transcribe(model, source, extension)
        transcript_text = whisper_result.get("text", "").strip()

        # ── 2. Classify ────────────────────────────────────────────────────────
        # Re-seek / re-use the same source for spectral analysis.
        # If a temp file was written we already deleted it, so re-create for librosa.
        classify_source = self._prepare_classify_source(source, extension)
        try:
            classification = audio_classifier.classify(
                source=classify_source,
                extension=extension,
                whisper_result=whisper_result,
            )
        except Exception as e:
            print(f"[WARNING] AudioExtractor: classification failed — {e}")
            classification = {
                "label": "unknown",
                "confidence": "low",
                "signals": {},
                "description": "Classification unavailable",
            }
        finally:
            # Clean up temp classify source if we made one
            if isinstance(classify_source, str) and classify_source != source:
                try:
                    os.unlink(classify_source)
                except Exception:
                    pass

        label      = classification["label"]
        confidence = classification["confidence"]
        signals    = classification["signals"]
        desc       = classification["description"]

        # Override for non-English audio: treat as vocal performance without transcript
        detected_lang = whisper_result.get("language")
        if detected_lang and detected_lang != "en":
            label = "vocals"
            transcript_text = ""
            desc = "Vocal performance — no text transcript"


        # ── 3. Build enriched semantic text ────────────────────────────────────
        sig_str = " | ".join(
            f"{k}={v}" for k, v in signals.items()
        ) if signals else "unavailable"

        semantic_header = (
            f"AUDIO_TYPE: {label}\n"
            f"AUDIO_CONFIDENCE: {confidence}\n"
            f"AUDIO_DESCRIPTION: {desc}\n"
            f"SIGNALS: {sig_str}"
        )

        # ── 4. Gate: discard non-vocal audio with no transcript ───────────────
        # Vocals are always kept (singing is content worth indexing even if
        # Whisper can't produce a clean transcript).  Everything else with
        # no transcript is silently dropped — no empty vectors stored.
        if not transcript_text and label != "vocals":
            raise NoSpeechError(
                f"Audio '{original_name or extension}' classified as '{label}' "
                "with no speech transcript — not indexed."
            )

        if transcript_text:
            full_text = f"{semantic_header}\n\nTRANSCRIPT:\n{transcript_text}"
        else:
            # vocals path: no transcript but still worth embedding the classification
            full_text = f"{semantic_header}\n\n(Vocal performance — no text transcript)"

        return {
            "raw_text": full_text,
            "metadata": {
                "file_type":        extension,
                "audio_label":      label,
                "audio_confidence": confidence,
                "audio_signals":    signals,
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transcribe(self, model, source, extension: str):
        """
        Run Whisper transcription with language auto-detection.
        Returns (whisper_result_dict, tmp_path_or_None).
        Cleans up any temp file before returning.
        """
        if isinstance(source, str):
            result = model.transcribe(source)
            return result, None

        # Stream → temp file
        source.seek(0)
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
            tmp.write(source.read())
            tmp_path = tmp.name
        try:
            result = model.transcribe(tmp_path)
        finally:
            os.unlink(tmp_path)

        # Rewind stream so the classifier can also read it
        source.seek(0)
        return result, None

    def _prepare_classify_source(self, source, extension: str):
        """
        Return something librosa can load.
        - If source is a path string, return it as-is.
        - If it's a stream, write a fresh temp file and return its path.
          Caller is responsible for deleting it.
        """
        if isinstance(source, str):
            return source

        source.seek(0)
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
            tmp.write(source.read())
            return tmp.name
