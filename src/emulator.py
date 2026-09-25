import getpass
import os
import re
import shlex
import socket

reg = re.compile(
    r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))"
)

def expand_vars(token):
    def replacer(match):
        name = match.group(1) or match.group(2)
        return os.environ.get(name, "")

    return reg.sub(replacer, token)

def get_prompt():
    username = getpass.getuser()
    hostname = socket.gethostname()

    current_dir = os.getcwd()
    home_dir = os.path.expanduser("~")

    if current_dir == home_dir:
        display_dir = "~"
    elif current_dir.startswith(home_dir + os.sep):
        display_dir = "~" + current_dir[len(home_dir):]
    else:
        display_dir = current_dir

    return f'{username}@{hostname}:{display_dir}$ '

def parse_command(command_line):
    try:
        parts = shlex.split(command_line)
    except ValueError:
        return None, None

    if not parts:
        return "", []

    parts = [expand_vars(part) for part in parts]

    return parts[0], parts[1:]

def command_ls(args):
    print(f'ls: args = {args}')

def command_cd(args):
    print(f'cd: args = {args}')


def main():
    print("Эмулятор UNIX-подобной ОС")
    print("Доступны команды: ls, cd, exit")

    while True:
        try:
            command_line = input(get_prompt())
        except (EOFError, KeyboardInterrupt):
            print()
            break

        command, args = parse_command(command_line)

        if command is None:
            print("Ошибка: некорректные кавычки в команде.")
            continue

        if command == "exit":
            if args:
                print("Ошибка: команда exit не принимает аргументов")
            else:
                print("Выход из эмулятора.")
                break

        elif command == "ls":
            command_ls(args)

        elif command == "cd":
            command_cd(args)

        else:
            print(f'Ошибка: неизвестная команда: {command}')


if __name__ == "__main__":
    main()