from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BABEL_")

    # STT
    stt_url: str = "http://localhost:9000"
    stt_model: str = "large-v3"
    stt_language: str = "de"

    # LLM Postprocessing (M5)
    llm_url: str = "http://m5:4000"
    llm_model: str = "rupt"
    llm_timeout: float = 15.0

    # Audio
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    vad_threshold: float = 0.5
    silence_duration: float = 1.5

    # Processing
    default_mode: str = "bereinigen"
    durchreichen_max_words: int = 5

    # Prompts
    prompts_dir: str = "prompts"
