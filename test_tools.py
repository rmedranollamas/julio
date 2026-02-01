from tools_internal import run_shell_command, list_files, write_file, read_file
import os

def test_tools():
    # Test shell
    res = run_shell_command("echo 'hello'")
    print(f"Shell output: {res}")
    assert "hello" in res

    # Test FS
    write_file("test_fs.txt", "fs content")
    content = read_file("test_fs.txt")
    print(f"FS content: {content}")
    assert content == "fs content"

    files = list_files(".")
    assert "test_fs.txt" in files

    os.remove("test_fs.txt")
    print("Internal tools test PASSED")

if __name__ == "__main__":
    test_tools()
