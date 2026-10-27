"""Phase 9 client for a locally running Ollama server."""

from __future__ import annotations

import json
import time
from urllib import error, request


class OllamaClient:
    """Communicate with the local Ollama HTTP API."""

    DEFAULT_BASE_URL = "http://127.0.0.1:11434"
    DEFAULT_MODEL = "qwen3:4b"
    DEFAULT_TIMEOUT = 300.0
    DEFAULT_RETRIES = 1
    DEFAULT_RETRY_DELAY = 1.0

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.retry_delay = float(retry_delay)

        if not self.base_url:
            raise ValueError("base_url cannot be empty.")
        if not self.model.strip():
            raise ValueError("model cannot be empty.")
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than zero.")
        if self.retries < 0:
            raise ValueError("retries cannot be negative.")
        if self.retry_delay < 0:
            raise ValueError("retry_delay cannot be negative.")

    def generate(self, prompt: str) -> str:
        """Generate a short structured response from local Qwen3:4B."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt cannot be empty.")

        response_schema = {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": [
                        "KEEP_FIRST",
                        "KEEP_SECOND",
                        "MANUAL_REVIEW",
                    ],
                },
                "reason": {"type": "string"},
            },
            "required": ["decision", "reason"],
            "additionalProperties": False,
        }

        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "format": response_schema,
                "keep_alive": "10m",
                "options": {
                    "temperature": 0,
                    "num_predict": 64,
                },
            },
            ensure_ascii=False,
        ).encode("utf-8")

        last_error: BaseException | None = None
        body: str | None = None

        for attempt in range(self.retries + 1):
            http_request = request.Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )

            try:
                with request.urlopen(http_request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8")
                last_error = None
                break
            except error.HTTPError as exc:
                details = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Local Ollama returned HTTP {exc.code}: {details or exc.reason}"
                ) from exc
            except error.URLError as exc:
                last_error = exc
            except TimeoutError as exc:
                last_error = exc

            if attempt < self.retries and self.retry_delay:
                time.sleep(self.retry_delay)

        if last_error is not None or body is None:
            if isinstance(last_error, TimeoutError):
                raise TimeoutError(
                    f"The Ollama request timed out after {self.timeout:.0f} seconds."
                ) from last_error
            raise RuntimeError(
                "Unable to connect to local Ollama at "
                f"{self.base_url}. Ensure Ollama is running and the "
                f"{self.model} model is installed."
            ) from last_error

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama returned invalid JSON.") from exc

        if not isinstance(data, dict):
            raise RuntimeError("Ollama returned an unexpected response structure.")

        response_text = data.get("response")
        if not isinstance(response_text, str) or not response_text.strip():
            raise RuntimeError("Ollama response did not contain usable text.")

        return response_text.strip()
