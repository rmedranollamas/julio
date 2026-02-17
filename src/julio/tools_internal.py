import asyncio
import os
from typing import Optional


async def run_shell_command(command: str, timeout: float = 30.0) -> str:
    """Executes a shell command and returns the output."""
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

        def _decode():
            return f"STDOUT:\n{stdout.decode(errors='replace')}\nSTDERR:\n{stderr.decode(errors='replace')}"

        return await asyncio.to_thread(_decode)
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

        def _list():
            with os.scandir(path) as it:
                return "\n".join(entry.name for entry in it)

        return await asyncio.to_thread(_list)
    except Exception as e:
        return f"Error listing files: {str(e)}"


async def read_file(path: str, offset: int = 0, length: Optional[int] = None) -> str:
    """Reads the content of a file.

    Args:
        path: Path to the file.
        offset: Byte offset to start reading from.
        length: Maximum number of characters to read. If None, reads the whole file.
    """
    try:

        def _read():
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                if offset > 0:
                    f.seek(offset)

                if length is not None:
                    return f.read(length)

                # Use chunked reading for large files even when no length is specified
                # to avoid potential issues with very large single read calls,
                # although the final string will still be in memory.
                chunks = []
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                return "".join(chunks)

        return await asyncio.to_thread(_read)
    except Exception as e:
        return f"Error reading file: {str(e)}"


async def write_file(path: str, content: str) -> str:
    """Writes content to a file."""
    try:

        def _write():
            with open(path, "w") as f:
                f.write(content)

        await asyncio.to_thread(_write)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def request_user_input(question: str) -> str:
    """Requests input from the user when more information is needed to proceed."""
    return f"User has been asked: {question}. Waiting for response..."
