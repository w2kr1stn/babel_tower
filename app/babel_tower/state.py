import os
import tempfile
from pathlib import Path


def _state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
    return Path(base) / "babel_tower"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    closed = False
    try:
        os.write(fd, data)
        os.close(fd)
        closed = True
        os.replace(tmp, path)
    except BaseException:
        if not closed:
            os.close(fd)
        Path(tmp).unlink(missing_ok=True)
        raise


def save_audio(data: bytes) -> None:
    _atomic_write(_state_dir() / "audio.wav", data)


def save_transcript(text: str) -> None:
    _atomic_write(_state_dir() / "transcript.txt", text.encode())


def save_result(text: str) -> None:
    _atomic_write(_state_dir() / "result.txt", text.encode())


def load_result() -> str | None:
    path = _state_dir() / "result.txt"
    try:
        return path.read_text()
    except FileNotFoundError:
        return None
