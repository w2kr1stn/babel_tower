from pathlib import Path

import pytest
from babel_tower.state import load_result, save_audio, save_result, save_transcript


@pytest.fixture
def state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path / "babel_tower"


class TestSaveAudio:
    def test_round_trip(self, state_dir: Path) -> None:
        data = b"RIFF\x00\x00\x00\x00WAVEfmt "
        save_audio(data)
        assert (state_dir / "audio.wav").read_bytes() == data

    def test_overwrites_existing(self, state_dir: Path) -> None:
        save_audio(b"first")
        save_audio(b"second")
        assert (state_dir / "audio.wav").read_bytes() == b"second"


class TestSaveTranscript:
    def test_round_trip(self, state_dir: Path) -> None:
        save_transcript("Hallo Welt")
        assert (state_dir / "transcript.txt").read_text() == "Hallo Welt"

    def test_overwrites_existing(self, state_dir: Path) -> None:
        save_transcript("first")
        save_transcript("second")
        assert (state_dir / "transcript.txt").read_text() == "second"


class TestSaveResult:
    def test_round_trip(self, state_dir: Path) -> None:
        save_result("cleaned text")
        assert (state_dir / "result.txt").read_text() == "cleaned text"

    def test_overwrites_existing(self, state_dir: Path) -> None:
        save_result("first")
        save_result("second")
        assert (state_dir / "result.txt").read_text() == "second"


class TestLoadResult:
    def test_returns_none_when_no_state(self, state_dir: Path) -> None:
        assert load_result() is None

    def test_returns_saved_result(self, state_dir: Path) -> None:
        save_result("some result")
        assert load_result() == "some result"

    def test_returns_latest_after_overwrite(self, state_dir: Path) -> None:
        save_result("first")
        save_result("second")
        assert load_result() == "second"


class TestAtomicWrite:
    def test_creates_parent_directories(self, state_dir: Path) -> None:
        assert not state_dir.exists()
        save_result("test")
        assert state_dir.is_dir()

    def test_no_temp_files_left_on_success(self, state_dir: Path) -> None:
        save_result("test")
        files = list(state_dir.iterdir())
        assert len(files) == 1
        assert files[0].name == "result.txt"
