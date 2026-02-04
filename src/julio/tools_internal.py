import asyncio
import os


async def run_shell_command(command: str, timeout: float = 30.0) -> str:
    """Executes a shell command and returns the output."""
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return f"STDOUT:\n{stdout.decode()}\nSTDERR:\n{stderr.decode()}"
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
        files = await asyncio.to_thread(os.listdir, path)
        return "\n".join(files)
    except Exception as e:
        return f"Error listing files: {str(e)}"


async def read_file(path: str) -> str:
    """Reads the content of a file."""
    try:

        def _read():
            with open(path, "r") as f:
                return f.read()

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
