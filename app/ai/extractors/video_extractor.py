"""Fast, bounded video analysis for V1 ingestion."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pytesseract
from PIL import Image

from app.ai.extractors.audio_extractor import _get_whisper_model
from app.ai.extractors.vision_describer import VisionDescriber


class VideoExtractor:
    """Extract metadata, English speech, OCR, and bounded visual descriptions."""

    SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
    MAX_FRAMES = 6
    FRAME_WIDTH = 512
    SPEECH_RMS_THRESHOLD = 0.012
    MIN_SPEECH_RATIO = 0.01

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.vision = VisionDescriber()

    def extract(self, source, extension: str | None = None) -> dict:
        extension = extension or self._extension_for(source)
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported video format: {extension}")

        with tempfile.TemporaryDirectory(prefix="repoir_video_") as work_dir:
            video_path = self._materialize_source(source, extension, work_dir)
            metadata = self._probe(video_path)
            audio_stream = next(
                (stream for stream in metadata["streams"] if stream.get("codec_type") == "audio"),
                None,
            )
            video_stream = next(
                (stream for stream in metadata["streams"] if stream.get("codec_type") == "video"),
                {},
            )
            duration = float(metadata.get("format", {}).get("duration") or 0.0)
            metadata_text = self._metadata_text(metadata, video_stream, audio_stream, duration)

            frame_count = self._frame_count(duration)
            visual_text = self._analyze_visuals(video_path, duration, work_dir, frame_count)
            audio_text = ""
            audio_status = "no_audio"
            detected_language = None

            if audio_stream:
                audio_path = os.path.join(work_dir, "audio.wav")
                self._extract_audio(video_path, audio_path)
                if self._has_speech(audio_path):
                    audio_status = "speech_detected"
                    audio_text, detected_language = self._transcribe(audio_path)
                    if detected_language != "en":
                        audio_status = "unsupported_language"
                        audio_text = ""
                else:
                    audio_status = "no_speech"

            parts = [metadata_text]
            if audio_status == "unsupported_language":
                parts.append(
                    f"AUDIO_LANGUAGE: {detected_language or 'unknown'}\n"
                    "AUDIO_TRANSCRIPTION: skipped because only English is supported."
                )
            elif audio_text:
                parts.append(f"AUDIO_LANGUAGE: English\nTRANSCRIPT:\n{audio_text}")
            else:
                parts.append("AUDIO: No speech detected.")
            if visual_text:
                parts.append(f"VISUAL CONTENT:\n{visual_text}")

            return {
                "raw_text": "\n\n".join(parts),
                "metadata": {
                    "file_type": extension,
                    "video_metadata": metadata,
                    "audio_status": audio_status,
                    "language": detected_language,
                    "visual_frame_count": frame_count,
                },
            }

    @staticmethod
    def _extension_for(source) -> str:
        if isinstance(source, (str, os.PathLike)):
            return Path(source).suffix.lower()
        raise ValueError("Extension must be provided for stream video sources")

    @staticmethod
    def _materialize_source(source, extension: str, work_dir: str) -> str:
        if isinstance(source, (str, os.PathLike)):
            return os.fspath(source)
        source.seek(0)
        path = os.path.join(work_dir, f"source{extension}")
        with open(path, "wb") as output:
            shutil.copyfileobj(source, output)
        source.seek(0)
        return path

    @staticmethod
    def _run(command: list[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                command,
                input=input_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("FFmpeg/FFprobe is required for video ingestion") from exc
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.decode("utf-8", errors="replace")[-500:]
            raise RuntimeError(f"Video processing command failed: {detail}") from exc

    def _probe(self, video_path: str) -> dict:
        result = self._run([
            "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", video_path,
        ])
        return json.loads(result.stdout.decode("utf-8"))

    def _metadata_text(self, metadata: dict, video_stream: dict, audio_stream: dict | None, duration: float) -> str:
        width = video_stream.get("width", "unknown")
        height = video_stream.get("height", "unknown")
        fps = video_stream.get("r_frame_rate", "unknown")
        codec = video_stream.get("codec_name", "unknown")
        audio_codec = audio_stream.get("codec_name", "none") if audio_stream else "none"
        return (
            "VIDEO_METADATA:\n"
            f"Duration: {duration:.1f} seconds\n"
            f"Resolution: {width}x{height}\n"
            f"FPS: {fps}\n"
            f"Video codec: {codec}\n"
            f"Audio codec: {audio_codec}\n"
            f"Audio present: {'yes' if audio_stream else 'no'}"
        )

    def _extract_audio(self, video_path: str, audio_path: str) -> None:
        self._run([
            "ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000",
            "-c:a", "pcm_s16le", audio_path,
        ])

    def _has_speech(self, audio_path: str) -> bool:
        result = self._run([
            "ffmpeg", "-v", "error", "-i", audio_path, "-f", "s16le", "-ac", "1", "-ar", "16000", "-",
        ])
        samples = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32) / 32768.0
        if samples.size == 0:
            return False
        window = 480
        rms_values = [float(np.sqrt(np.mean(chunk * chunk))) for chunk in np.array_split(samples, max(1, samples.size // window)) if chunk.size]
        if not rms_values:
            return False
        threshold = max(self.SPEECH_RMS_THRESHOLD, float(np.percentile(rms_values, 35)) * 1.8)
        return sum(rms >= threshold for rms in rms_values) / len(rms_values) >= self.MIN_SPEECH_RATIO

    def _transcribe(self, audio_path: str) -> tuple[str, str | None]:
        model = _get_whisper_model(self.model_size)
        result = model.transcribe(
            audio_path,
            task="transcribe",
            fp16=False,
            condition_on_previous_text=False,
            temperature=0,
        )
        return result.get("text", "").strip(), result.get("language")

    @classmethod
    def _frame_count(cls, duration: float) -> int:
        if duration < 5:
            return 1
        if duration < 15:
            return 2
        if duration < 60:
            return 4
        return cls.MAX_FRAMES

    def _analyze_visuals(self, video_path: str, duration: float, work_dir: str, frame_count: int) -> str:
        if duration <= 0:
            return ""
        timestamps = np.linspace(0.0, max(0.0, duration - 0.1), frame_count)
        descriptions = []
        for index, timestamp in enumerate(timestamps, start=1):
            frame_path = os.path.join(work_dir, f"frame_{index}.jpg")
            try:
                self._run([
                    "ffmpeg", "-y", "-ss", f"{timestamp:.3f}", "-i", video_path,
                    "-frames:v", "1", "-vf", f"scale={self.FRAME_WIDTH}:-2", "-q:v", "5", frame_path,
                ])
                with Image.open(frame_path) as image:
                    ocr_text = pytesseract.image_to_string(image).strip()
                vision_text = self.vision.describe(frame_path).strip()
                evidence = []
                if vision_text:
                    evidence.append(f"Vision: {vision_text}")
                if ocr_text:
                    evidence.append(f"OCR: {ocr_text}")
                if evidence:
                    descriptions.append(f"Frame {index} at {timestamp:.1f}s: " + " | ".join(evidence))
            except Exception as exc:
                print(f"[WARNING] Video frame {index} skipped: {exc}")
        return "\n".join(descriptions)
