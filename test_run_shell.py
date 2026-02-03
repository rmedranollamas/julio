import asyncio
from tools_internal import run_shell_command


async def main():
    print("Testing normal command:")
    print(await run_shell_command("echo hello"))

    print("\nTesting timeout command:")
    print(await run_shell_command("sleep 5", timeout=1))


if __name__ == "__main__":
    asyncio.run(main())
