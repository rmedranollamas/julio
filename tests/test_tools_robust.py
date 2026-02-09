import pytest
import asyncio
import os
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
from julio.tools_internal import run_shell_command, list_files, read_file, write_file

@pytest.mark.asyncio
async def test_run_shell_command_timeout():
    # Test timeout
    result = await run_shell_command("sleep 2", timeout=0.1)
    assert "Error: Command timed out" in result

@pytest.mark.asyncio
async def test_run_shell_command_error():
    # Test command error
    result = await run_shell_command("nonexistentcommand")
    assert "Error executing command" in result or "not found" in result.lower()

@pytest.mark.asyncio
async def test_list_files_nonexistent(tmp_path):
    non_existent = tmp_path / "doesnotexist"
    result = await list_files(str(non_existent))
    assert "Error listing files" in result

@pytest.mark.asyncio
async def test_read_file_nonexistent(tmp_path):
    non_existent = tmp_path / "none.txt"
    result = await read_file(str(non_existent))
    assert "Error reading file" in result

@pytest.mark.asyncio
async def test_write_file_error():
    # Attempt to write to a path that is a directory
    path = "/tmp/test_dir_write"
    os.makedirs(path, exist_ok=True)
    try:
        result = await write_file(path, "content")
        assert "Error writing file" in result
    finally:
        shutil.rmtree(path)

@pytest.mark.asyncio
async def test_run_shell_command_large_output():
    # Test large output
    result = await run_shell_command("head -c 100000 /dev/zero | tr '\\0' 'a'")
    assert len(result) > 100000
    assert "STDOUT:" in result

@pytest.mark.asyncio
async def test_run_shell_command_exception():
    with patch("asyncio.create_subprocess_shell") as mock_create:
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(side_effect=RuntimeError("internal error"))
        mock_proc.wait = AsyncMock()
        mock_proc.returncode = None
        mock_create.return_value = mock_proc

        result = await run_shell_command("some command")
        assert "Error executing command: internal error" in result
        mock_proc.kill.assert_called()
