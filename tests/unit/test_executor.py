"""Tests for WindowsExecutor — action dispatching and safety validation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from gotit.adapters.executor.windows import WindowsExecutor, _validate_path
from gotit.domain.models import ActionType, Intent, SearchResult


@pytest.fixture
def executor():
    return WindowsExecutor(search_config=None)


class TestSearchAction:
    async def test_empty_results(self, executor):
        intent = Intent(action=ActionType.SEARCH, raw_text="find stuff", query="stuff")
        result = await executor.execute(intent, [])
        assert result.success
        assert "No results" in result.message

    async def test_with_results(self, executor):
        intent = Intent(action=ActionType.SEARCH, raw_text="find py", query="*.py")
        targets = [SearchResult(path="C:\\a.py", filename="a.py")]
        result = await executor.execute(intent, targets)
        assert result.success
        assert "1 results" in result.message


class TestOpenFile:
    async def test_no_targets(self, executor):
        intent = Intent(action=ActionType.OPEN_FILE, raw_text="open file")
        result = await executor.execute(intent, [])
        assert not result.success

    async def test_blocked_extension(self, executor):
        intent = Intent(action=ActionType.OPEN_FILE, raw_text="open bat")
        targets = [SearchResult(path="C:\\evil.bat", filename="evil.bat")]
        result = await executor.execute(intent, targets)
        assert not result.success
        assert "Blocked" in result.message

    @patch("gotit.adapters.executor.windows.os.startfile")
    async def test_success(self, mock_startfile, executor):
        intent = Intent(action=ActionType.OPEN_FILE, raw_text="open doc")
        targets = [SearchResult(path="C:\\doc.pdf", filename="doc.pdf")]
        result = await executor.execute(intent, targets)
        assert result.success
        mock_startfile.assert_called_once_with("C:\\doc.pdf")


class TestRunProgram:
    async def test_no_target(self, executor):
        intent = Intent(action=ActionType.RUN_PROGRAM, raw_text="run something")
        result = await executor.execute(intent, [])
        assert not result.success
        assert "No program" in result.message

    @patch.object(WindowsExecutor, "_resolve_via_everything", new_callable=AsyncMock, return_value=None)
    @patch("gotit.adapters.executor.windows.shutil.which", return_value=None)
    async def test_program_not_found(self, mock_which, mock_ev, executor):
        intent = Intent(
            action=ActionType.RUN_PROGRAM, raw_text="run foo", target="nonexistent"
        )
        result = await executor.execute(intent, [])
        assert not result.success
        assert "not found" in result.message

    @patch("gotit.adapters.executor.windows.subprocess.Popen")
    @patch(
        "gotit.adapters.executor.windows.shutil.which",
        return_value="C:\\Windows\\notepad.exe",
    )
    async def test_success(self, mock_which, mock_popen, executor):
        intent = Intent(
            action=ActionType.RUN_PROGRAM, raw_text="open notepad", target="notepad"
        )
        result = await executor.execute(intent, [])
        assert result.success
        mock_popen.assert_called_once()

    @patch("gotit.adapters.executor.windows.subprocess.Popen")
    @patch.object(
        WindowsExecutor, "_resolve_via_everything",
        new_callable=AsyncMock,
        return_value="C:\\Program Files\\Notepad++\\notepad++.exe",
    )
    @patch("gotit.adapters.executor.windows.shutil.which", return_value=None)
    async def test_fallback_to_everything(self, mock_which, mock_ev, mock_popen, executor):
        intent = Intent(
            action=ActionType.RUN_PROGRAM, raw_text="open notepad++", target="notepad++"
        )
        result = await executor.execute(intent, [])
        assert result.success
        mock_popen.assert_called_once_with(
            ["C:\\Program Files\\Notepad++\\notepad++.exe"], shell=False
        )


class TestValidatePath:
    def test_normal_path(self):
        assert _validate_path("C:\\Users\\test\\doc.pdf")

    def test_blocked_bat(self):
        assert not _validate_path("C:\\evil.bat")

    def test_blocked_ps1(self):
        assert not _validate_path("C:\\script.ps1")

    def test_blocked_cmd(self):
        assert not _validate_path("C:\\run.cmd")
