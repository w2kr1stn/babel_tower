from typing import Any

import pytest
from babel_tower.config import Settings


class TestSettingsDefaults:
    def test_stt_defaults(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = Settings()
        assert settings.stt_url == "http://localhost:9000"
        assert settings.stt_model == "Systran/faster-whisper-large-v3"
        assert settings.stt_language == "de"
        assert settings.stt_timeout == 30.0

    def test_llm_defaults(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = Settings()
        assert settings.llm_url == "http://m5:4000"
        assert settings.llm_model == "rupt"
        assert settings.llm_timeout == 15.0

    def test_audio_defaults(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = Settings()
        assert settings.audio_sample_rate == 16000
        assert settings.audio_channels == 1
        assert settings.vad_threshold == 0.5
        assert settings.silence_duration == 10.0

    def test_tts_defaults(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = Settings()
        assert settings.tts_url == "http://m5:8000"
        assert settings.tts_voice == "thorsten_emotional"
        assert settings.tts_timeout == 10.0
        assert settings.tts_enabled is False

    def test_processing_defaults(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = Settings()
        assert settings.default_mode == "bereinigen"
        assert settings.durchreichen_max_words == 5

    def test_prompts_dir_default(self, clean_env: pytest.MonkeyPatch) -> None:
        settings = Settings()
        assert settings.prompts_dir == "prompts"


class TestSettingsEnvOverride:
    def test_env_prefix_is_babel(self) -> None:
        assert Settings.model_config.get("env_prefix") == "BABEL_"

    def test_env_vars_override_defaults(self, env_overrides: dict[str, Any]) -> None:
        settings = Settings()
        assert settings.stt_url == "http://custom-stt:8080"
        assert settings.stt_model == "tiny"
        assert settings.llm_timeout == 30.0
        assert settings.default_mode == "strukturieren"

    def test_single_env_override(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("BABEL_STT_LANGUAGE", "en")
        settings = Settings()
        assert settings.stt_language == "en"
        # Other defaults remain unchanged
        assert settings.stt_url == "http://localhost:9000"

    def test_numeric_env_override(self, clean_env: pytest.MonkeyPatch) -> None:
        clean_env.setenv("BABEL_AUDIO_SAMPLE_RATE", "44100")
        clean_env.setenv("BABEL_VAD_THRESHOLD", "0.8")
        settings = Settings()
        assert settings.audio_sample_rate == 44100
        assert settings.vad_threshold == 0.8
