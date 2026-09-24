import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from emulator import get_prompt, parse_command


def test_parse_command():
    command, args = parse_command("ls -l test")

    assert command == "ls"
    assert args == ["-l", "test"]


def test_parse_empty_command():
    command, args = parse_command("")

    assert command == ""
    assert args == []


def test_parse_quoted_argument():
    command, args = parse_command('ls "my folder"')

    assert command == "ls"
    assert args == ["my folder"]


def test_parse_invalid_quotes():
    command, args = parse_command('ls "my folder')

    assert command is None
    assert args is None


def test_get_prompt():
    prompt = get_prompt()

    assert isinstance(prompt, str)
    assert prompt.endswith("$ ")