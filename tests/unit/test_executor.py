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
        intent = Intent(action=ActionType.OPEN_FILE, raw_text="open vbs")
        targets = [SearchResult(path="C:\\evil.vbs", filename="evil.vbs")]
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


class TestOpenWithProgram:
    @patch("gotit.adapters.executor.windows.subprocess.Popen")
    @patch("gotit.adapters.executor.windows.shutil.which", return_value="C:\\Program Files\\Code\\code.exe")
    async def test_open_file_with_program(self, mock_which, mock_popen, executor):
        intent = Intent(
            action=ActionType.OPEN_FILE, raw_text="用vscode打开config.ini",
            with_program="code",
        )
        targets = [SearchResult(path="C:\\project\\config.ini", filename="config.ini")]
        result = await executor.execute(intent, targets)
        assert result.success
        assert "code" in result.message.lower()
        mock_popen.assert_called_once_with(
            ["C:\\Program Files\\Code\\code.exe", "C:\\project\\config.ini"], shell=False
        )

    @patch("gotit.adapters.executor.windows.subprocess.Popen")
    @patch("gotit.adapters.executor.windows.shutil.which", return_value="C:\\Program Files\\Code\\code.exe")
    async def test_open_folder_with_program(self, mock_which, mock_popen, executor, tmp_path):
        folder = str(tmp_path)
        intent = Intent(
            action=ActionType.OPEN_FOLDER, raw_text="用vscode打开项目",
            target=folder, with_program="code",
        )
        result = await executor.execute(intent, [])
        assert result.success
        mock_popen.assert_called_once_with(
            ["C:\\Program Files\\Code\\code.exe", folder], shell=False
        )

    @patch.object(WindowsExecutor, "_resolve_via_everything", new_callable=AsyncMock, return_value=None)
    @patch("gotit.adapters.executor.windows.shutil.which", return_value=None)
    async def test_with_program_not_found(self, mock_which, mock_ev, executor):
        intent = Intent(
            action=ActionType.OPEN_FILE, raw_text="用unknown打开文件",
            with_program="unknown_editor",
        )
        targets = [SearchResult(path="C:\\doc.txt", filename="doc.txt")]
        result = await executor.execute(intent, targets)
        assert not result.success
        assert "not found" in result.message


class TestValidatePath:
    def test_normal_path(self):
        assert _validate_path("C:\\Users\\test\\doc.pdf")

    def test_bat_allowed(self):
        assert _validate_path("C:\\tools\\launch.bat")

    def test_cmd_allowed(self):
        assert _validate_path("C:\\tools\\run.cmd")

    def test_blocked_ps1(self):
        assert not _validate_path("C:\\script.ps1")

    def test_blocked_vbs(self):
        assert not _validate_path("C:\\script.vbs")
