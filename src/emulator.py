import argparse
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

def command_exit(args):
    if args:
        print("Ошибка: команда exit не принимает аргументов")
        return False

    print("Выход из эмулятора.")
    return True

    
def execute_command(command_line):
    command, args = parse_command(command_line)

    if command is None:
        print("Ошибка: некорректные кавычки в команде.")
        return False

    if not command:
        return True

    if command == "ls":
        command_ls(args)
        return True

    if command == "cd":
        command_cd(args)
        return True

    if command == "exit":
        if command_exit(args):
            return "exit"

        return False

    print(f'Ошибка: неизвестная команда: {command}')
    return False


def parse_arguments():
    parser = argparse.ArgumentParser(
        description= "Эмулятор UNIX-подобной ОС"
    )

    parser.add_argument(
        "--vfs-path",
        help = "Путь к физическому расположению виртуальной "
        "файловой системы",
    )

    parser.add_argument(
        "--script-path",
        help = "Путь к стартовому скрипту",
    )

    return parser.parse_args()


def print_configuration(args):
    print("Конфигурация:")
    print(f"  Путь к VFS: {args.vfs_path or 'не указан'}")
    print(f"  Путь к скрипту: {args.script_path or 'не указан'}")


def run_startup_script(script_path):
    try:
        with open(script_path, "r", encoding="utf-8") as script_file:
            for line_number, line in enumerate(script_file, start = 1):
                command_line = line.strip()

                if not command_line:
                    continue

                print(get_prompt() + command_line)

                result = execute_command(command_line)

                if result is False:
                    print(
                        f'Ошибка выполнения скрипта '
                        f'на строке {line_number}.'
                    )
                    break

                if result == "exit":
                    break

    except FileNotFoundError:
        print(f'Ошибка: файл скрипта не найден: {script_path}')

    except OSError as error:
        print(f"Ошибка при чтении скрипта: {error}")


def run_interactive_mode():
    while True:
        try:
            command_line = input(get_prompt())
        except (EOFError, KeyboardInterrupt):
            print()
            break

        result = execute_command(command_line)

        if result == "exit":
            break


def main():
    args = parse_arguments()

    print("Эмулятор UNIX-подобной ОС")
    print("Доступны команды: ls, cd, exit")

    print_configuration(args)

    if args.script_path:
        run_startup_script(args.script_path)

    run_interactive_mode()


if __name__ == "__main__":
    main()