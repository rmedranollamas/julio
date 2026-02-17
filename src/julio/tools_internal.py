import asyncio
import os
from typing import Optional


async def run_shell_command(command: str, timeout: float = 30.0) -> str:
    """Executes a shell command and returns combined stdout/stderr."""
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )

        def _decode_output():
            out = stdout_bytes.decode(errors="replace")
            err = stderr_bytes.decode(errors="replace")
            return f"STDOUT:\n{out}\nSTDERR:\n{err}"

        return await asyncio.to_thread(_decode_output)
    except asyncio.TimeoutError:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        await process.wait()
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()
        return f"Error executing command: {str(e)}"


async def list_files(path: str = ".") -> str:
    """Lists files in the specified directory."""
    try:

        def _list_dir():
            with os.scandir(path) as it:
                return "\n".join(entry.name for entry in it)

        return await asyncio.to_thread(_list_dir)
    except Exception as e:
        return f"Error listing files: {str(e)}"


async def read_file(path: str, offset: int = 0, length: Optional[int] = None) -> str:
    """Reads the content of a file with optional offset and length.

    Args:
        path: File path.
        offset: Byte offset to start reading from.
        length: Number of characters to read.
    """
    try:

        def _read_file_sync():
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                if offset > 0:
                    f.seek(offset)
                return f.read(length) if length is not None else f.read()

        return await asyncio.to_thread(_read_file_sync)
    except Exception as e:
        return f"Error reading file: {str(e)}"


async def write_file(path: str, content: str) -> str:
    """Writes content to a file."""
    try:

        def _write_file_sync():
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

        await asyncio.to_thread(_write_file_sync)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def request_user_input(question: str) -> str:
    """Requests input from the user."""
    return f"User has been asked: {question}. Waiting for response..."
