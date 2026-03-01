from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BABEL_",
        env_file=_ENV_FILE if _ENV_FILE.exists() else None,
    )

    # STT
    stt_url: str = "http://localhost:29000"
    stt_model: str = "Systran/faster-whisper-large-v3"
    stt_language: str = "de"
    stt_timeout: float = 30.0

    # LLM Postprocessing (M5)
    llm_url: str = "http://ai-station:4000"
    llm_model: str = "rupt"
    llm_api_key: str = ""
    llm_timeout: float = 60.0

    # Audio
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    vad_threshold: float = 0.5
    silence_duration: float = 20.0

    # TTS (M5)
    tts_url: str = "http://m5:8000"
    tts_voice: str = "thorsten_emotional"
    tts_timeout: float = 10.0
    tts_enabled: bool = False

    # Processing
    default_mode: str = "clean"
    durchreichen_max_words: int = 5
    review_enabled: bool = False

    # Prompts
    prompts_dir: str = "prompts"
