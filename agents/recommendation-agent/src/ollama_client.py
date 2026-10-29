import logging
import time

import httpx

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def wait_ready(self, timeout_seconds: int = 600) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                response = httpx.get(f"{self.base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(5)
        raise TimeoutError(f"Ollama not ready after {timeout_seconds}s at {self.base_url}")

    def pull_model(self) -> None:
        # Non-fatal on failure: in an air-gapped OT network the pull cannot
        # succeed, but the model may already be preloaded in the ollama volume.
        try:
            response = httpx.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model, "stream": False},
                timeout=1800,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(
                "model pull failed (offline?): %s — assuming %s is preloaded in the ollama volume",
                exc, self.model,
            )

    def generate(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["response"]
