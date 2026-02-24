from io import BytesIO

import httpx
import pytest
from babel_tower.config import Settings
from babel_tower.stt import STTError, transcribe


@pytest.fixture
def stt_settings(clean_env: pytest.MonkeyPatch) -> Settings:
    clean_env.setenv("BABEL_STT_URL", "http://test-stt:9000")
    return Settings()


def _wav_bytes() -> bytes:
    return b"RIFF" + b"\x00" * 100


class TestTranscribe:
    @pytest.mark.anyio
    async def test_returns_transcript_text(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(200, json={"text": " Hallo Welt "})

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        result = await transcribe(_wav_bytes(), stt_settings)
        assert result == "Hallo Welt"

    @pytest.mark.anyio
    async def test_accepts_bytesio(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(200, json={"text": "test"})

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        result = await transcribe(BytesIO(_wav_bytes()), stt_settings)
        assert result == "test"

    @pytest.mark.anyio
    async def test_raises_on_connection_error(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(STTError, match="unreachable"):
            await transcribe(_wav_bytes(), stt_settings)

    @pytest.mark.anyio
    async def test_raises_on_timeout(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            raise httpx.ReadTimeout("timeout")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(STTError, match="timed out"):
            await transcribe(_wav_bytes(), stt_settings)

    @pytest.mark.anyio
    async def test_raises_on_non_200(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        with pytest.raises(STTError, match="500"):
            await transcribe(_wav_bytes(), stt_settings)

    @pytest.mark.anyio
    async def test_handles_empty_text(
        self, stt_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(200, json={"text": ""})

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        result = await transcribe(_wav_bytes(), stt_settings)
        assert result == ""
