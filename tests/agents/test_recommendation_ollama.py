import sys
import types

from tests.agents.collectors.import_helpers import load_module, recommendation_agent_path


class FakeResponse:
    status_code = 200

    def __init__(self, payload=None):
        self.payload = payload or {}

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_ollama_generate_posts_prompt(monkeypatch):
    calls = []
    httpx = types.ModuleType("httpx")
    httpx.HTTPError = Exception
    httpx.post = lambda *args, **kwargs: calls.append((args, kwargs)) or FakeResponse({"response": "ok"})
    monkeypatch.setitem(sys.modules, "httpx", httpx)
    module = load_module("ollama_client", recommendation_agent_path("ollama_client.py"))

    response = module.OllamaClient("http://ollama:11434/", "llama3.1:8b").generate("prompt")

    assert response == "ok"
    assert calls[0][0][0] == "http://ollama:11434/api/generate"
    assert calls[0][1]["json"] == {"model": "llama3.1:8b", "prompt": "prompt", "stream": False}


def test_ollama_wait_ready_uses_tags(monkeypatch):
    calls = []
    httpx = types.ModuleType("httpx")
    httpx.HTTPError = Exception
    httpx.get = lambda *args, **kwargs: calls.append((args, kwargs)) or FakeResponse()
    monkeypatch.setitem(sys.modules, "httpx", httpx)
    module = load_module("ollama_client", recommendation_agent_path("ollama_client.py"))

    module.OllamaClient("http://ollama:11434", "llama3.1:8b").wait_ready()

    assert calls[0][0][0] == "http://ollama:11434/api/tags"


class _FakeTime:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def test_wait_ready_times_out(monkeypatch):
    import pytest

    httpx = types.ModuleType("httpx")
    httpx.HTTPError = Exception

    def _raise(*args, **kwargs):
        raise httpx.HTTPError("down")

    httpx.get = _raise
    monkeypatch.setitem(sys.modules, "httpx", httpx)
    module = load_module("ollama_client", recommendation_agent_path("ollama_client.py"))
    monkeypatch.setattr(module, "time", _FakeTime())

    with pytest.raises(TimeoutError):
        module.OllamaClient("http://ollama:11434", "llama3.1:8b").wait_ready(timeout_seconds=30)


def test_pull_model_failure_is_non_fatal(monkeypatch):
    httpx = types.ModuleType("httpx")
    httpx.HTTPError = Exception

    def _raise(*args, **kwargs):
        raise httpx.HTTPError("no internet")

    httpx.post = _raise
    monkeypatch.setitem(sys.modules, "httpx", httpx)
    module = load_module("ollama_client", recommendation_agent_path("ollama_client.py"))

    module.OllamaClient("http://ollama:11434", "llama3.1:8b").pull_model()  # must not raise
