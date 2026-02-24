from collections.abc import Generator
from typing import Any

import pytest


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Generator[pytest.MonkeyPatch, None, None]:
    """Remove all BABEL_ env vars so tests start from a clean state."""
    babel_vars = [
        "BABEL_STT_URL",
        "BABEL_STT_MODEL",
        "BABEL_STT_LANGUAGE",
        "BABEL_LLM_URL",
        "BABEL_LLM_MODEL",
        "BABEL_LLM_TIMEOUT",
        "BABEL_AUDIO_SAMPLE_RATE",
        "BABEL_AUDIO_CHANNELS",
        "BABEL_VAD_THRESHOLD",
        "BABEL_SILENCE_DURATION",
        "BABEL_DEFAULT_MODE",
        "BABEL_DURCHREICHEN_MAX_WORDS",
        "BABEL_PROMPTS_DIR",
        "BABEL_REVIEW_ENABLED",
    ]
    for var in babel_vars:
        monkeypatch.delenv(var, raising=False)
    yield monkeypatch


@pytest.fixture
def env_overrides(clean_env: pytest.MonkeyPatch) -> dict[str, Any]:
    overrides: dict[str, Any] = {
        "BABEL_STT_URL": "http://custom-stt:8080",
        "BABEL_STT_MODEL": "tiny",
        "BABEL_LLM_TIMEOUT": "30.0",
        "BABEL_DEFAULT_MODE": "strukturieren",
    }
    for key, value in overrides.items():
        clean_env.setenv(key, str(value))
    return overrides
