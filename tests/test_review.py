import subprocess
from unittest.mock import MagicMock, patch

from babel_tower.review import review_text


class TestReviewText:
    def test_review_returns_edited_text(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "edited text\n"

        with patch("babel_tower.review.subprocess.run", return_value=mock_result):
            assert review_text("original") == "edited text"

    def test_review_returns_none_on_dismiss(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("babel_tower.review.subprocess.run", return_value=mock_result):
            assert review_text("something") is None

    def test_review_returns_none_on_timeout(self) -> None:
        with patch(
            "babel_tower.review.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="rofi", timeout=60),
        ):
            assert review_text("something") is None

    def test_review_returns_none_on_missing_rofi(self) -> None:
        with patch(
            "babel_tower.review.subprocess.run",
            side_effect=FileNotFoundError("rofi not found"),
        ):
            assert review_text("something") is None

    def test_review_calls_rofi_with_correct_args(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "text\n"

        with patch("babel_tower.review.subprocess.run", return_value=mock_result) as mock_run:
            review_text("hello world")
            mock_run.assert_called_once()
            args = mock_run.call_args
            cmd = args.args[0] if args.args else args.kwargs.get("args", [])
            assert cmd[0] == "rofi"
            assert "-dmenu" in cmd
            assert "-filter" in cmd
            filter_idx = cmd.index("-filter")
            assert cmd[filter_idx + 1] == "hello world"
