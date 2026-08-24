import base64
import io
import os
import time
import requests

# Cached availability flag — probed once per process lifetime.
# None = not yet checked, True = available, False = unavailable
_OLLAMA_AVAILABLE: "bool | None" = None


def _check_ollama(api_base: str, timeout: float = 3.0) -> bool:
    """
    Probe Ollama's /api/tags endpoint to confirm it is reachable AND
    that at least one llava model is loaded. Returns False on any failure.
    """
    try:
        r = requests.get(f"{api_base}/api/tags", timeout=timeout)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
        return any("llava" in m for m in models)
    except Exception:
        return False


class VisionDescriber:
    """
    High-Precision Vision Description using local Ollama + LLaVA.

    Safe-procedure behaviour
    ────────────────────────
    • One-time health-check on first use (cached for process lifetime).
    • Hard connect + read timeout — stalled Ollama never blocks a worker.
    • Exponential-backoff retry (up to MAX_RETRIES) on transient errors.
    • ConnectionError invalidates the cache so next file re-probes.
    • Always returns "" on failure — OCR-only fallback kicks in upstream.
    • Never raises — guaranteed silent degradation.
    """

    API_BASE        = "http://localhost:11434"
    MODEL           = "llava:7b"
    CONNECT_TIMEOUT = 5      # seconds to open the TCP connection
    READ_TIMEOUT    = 120    # seconds to wait for the full LLaVA response
    MAX_RETRIES     = 2      # attempts after the first failure (3 total)
    RETRY_BACKOFF   = [2, 5] # seconds before each retry

    def __init__(self):
        self.api_url = f"{self.API_BASE}/api/generate"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_available(self) -> bool:
        """Returns cached Ollama availability, probing exactly once."""
        global _OLLAMA_AVAILABLE
        if _OLLAMA_AVAILABLE is None:
            _OLLAMA_AVAILABLE = _check_ollama(self.API_BASE, timeout=self.CONNECT_TIMEOUT)
            if not _OLLAMA_AVAILABLE:
                print(
                    f"[INFO] VisionDescriber: Ollama not reachable or '{self.MODEL}' "
                    "not loaded. Vision disabled — falling back to OCR only."
                )
        return _OLLAMA_AVAILABLE

    def _encode_image(self, image_source) -> str:
        """Convert any source (path string or file-like) into a Base64 string."""
        if isinstance(image_source, str):
            with open(image_source, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        else:
            image_source.seek(0)
            return base64.b64encode(image_source.read()).decode("utf-8")

    def _call_ollama(self, base64_img: str) -> str:
        """Single HTTP attempt — raises on any error for the retry loop."""
        payload = {
            "model": self.MODEL,
            "prompt": (
                "Describe what you see in this image for a search index. "
                "Name specific things if you can."
            ),
            "images": [base64_img],
            "stream": False,
        }
        response = requests.post(
            self.api_url,
            json=payload,
            timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT),
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def describe(self, image_source) -> str:
        """
        Returns a text description of the image, or "" on any failure.
        Never raises.
        """
        if not self._is_available():
            return ""

        try:
            base64_img = self._encode_image(image_source)
        except Exception as e:
            print(f"[WARNING] VisionDescriber: could not encode image — {e}")
            return ""

        last_error = None
        total_attempts = 1 + self.MAX_RETRIES

        for attempt in range(total_attempts):
            try:
                return self._call_ollama(base64_img)

            except requests.exceptions.ConnectionError as e:
                # Ollama went down mid-batch — invalidate cache so the next
                # file re-probes instead of hammering a dead server.
                global _OLLAMA_AVAILABLE
                _OLLAMA_AVAILABLE = None
                last_error = e
                print(f"[WARNING] VisionDescriber: Ollama connection lost (attempt {attempt + 1}). Disabling for this session.")
                break  # No point retrying a dead connection

            except requests.exceptions.Timeout as e:
                last_error = e
                print(f"[WARNING] VisionDescriber: Ollama timed out (attempt {attempt + 1}/{total_attempts})")

            except Exception as e:
                last_error = e
                print(f"[WARNING] VisionDescriber: unexpected error (attempt {attempt + 1}/{total_attempts}) — {e}")

            # Back off before next retry (skip sleep on last attempt)
            if attempt < total_attempts - 1:
                sleep_sec = self.RETRY_BACKOFF[min(attempt, len(self.RETRY_BACKOFF) - 1)]
                time.sleep(sleep_sec)

        print(f"[ERROR] VisionDescriber: all {total_attempts} attempts failed — {last_error}. Returning empty.")
        return ""
