from __future__ import annotations

import subprocess
from unittest.mock import patch

from babel_tower.output import copy_to_clipboard, notify


class TestCopyToClipboard:
    @patch("babel_tower.output.subprocess.run")
    def test_success(self, mock_run: subprocess.CompletedProcess[str]) -> None:  # type: ignore[type-arg]
        result = copy_to_clipboard("hello world")
        assert result is True
        mock_run.assert_called_once_with(
            ["wl-copy", "hello world"],
            check=True,
            timeout=5,
            capture_output=True,
        )

    @patch("babel_tower.output.subprocess.run", side_effect=FileNotFoundError)
    def test_file_not_found(self, _mock_run: object) -> None:
        assert copy_to_clipboard("text") is False

    @patch(
        "babel_tower.output.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="wl-copy", timeout=5),
    )
    def test_timeout(self, _mock_run: object) -> None:
        assert copy_to_clipboard("text") is False

    @patch(
        "babel_tower.output.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "wl-copy"),
    )
    def test_called_process_error(self, _mock_run: object) -> None:
        assert copy_to_clipboard("text") is False


class TestNotify:
    @patch("babel_tower.output.subprocess.run")
    def test_success(self, mock_run: subprocess.CompletedProcess[str]) -> None:  # type: ignore[type-arg]
        result = notify("Title", "Body text")
        assert result is True
        mock_run.assert_called_once_with(
            ["notify-send", "--urgency=normal", "Title", "Body text"],
            check=True,
            timeout=5,
            capture_output=True,
        )

    @patch("babel_tower.output.subprocess.run")
    def test_custom_urgency(self, mock_run: subprocess.CompletedProcess[str]) -> None:  # type: ignore[type-arg]
        notify("Title", "Body", "critical")
        mock_run.assert_called_once_with(
            ["notify-send", "--urgency=critical", "Title", "Body"],
            check=True,
            timeout=5,
            capture_output=True,
        )

    @patch("babel_tower.output.subprocess.run")
    def test_truncates_long_body(self, mock_run: subprocess.CompletedProcess[str]) -> None:  # type: ignore[type-arg]
        long_body = "x" * 300
        notify("Title", long_body)
        call_args = mock_run.call_args
        assert call_args is not None
        body_arg = call_args.args[0][3]
        assert len(body_arg) == 200

    @patch(
        "babel_tower.output.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "notify-send"),
    )
    def test_failure(self, _mock_run: object) -> None:
        assert notify("Title", "Body") is False

    @patch("babel_tower.output.subprocess.run", side_effect=FileNotFoundError)
    def test_file_not_found(self, _mock_run: object) -> None:
        assert notify("Title", "Body") is False
