import argparse
import base64
import getpass
import io
import os
import re
import shlex
import socket
import zipfile
from pathlib import PurePosixPath


reg = re.compile(
    r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))"
)


def expand_vars(token):
    def replacer(match):
        name = match.group(1) or match.group(2)
        return os.environ.get(name, "")

    return reg.sub(replacer, token)


class VirtualFileSystem:
    def __init__(self):
        self.name = "default"
        self.entries = {}
        self.physical_path = None

    @staticmethod
    def normalize_path(path):
        path = path.replace("\\", "/").strip("/")

        if not path:
            return "/"

        parts = []

        for part in path.split("/"):
            if part in ("", "."):
                continue

            if part == "..":
                if parts:
                    parts.pop()

                continue

            parts.append(part)

        return "/" + "/".join(parts)

    def clear(self):
        self.name = "default"
        self.entries = {}

    def load_from_zip(self, zip_path):
        if not os.path.isfile(zip_path):
            raise FileNotFoundError(
                f"ZIP-архив VFS не найден: {zip_path}"
            )

        try:
            with open(zip_path, "rb") as file:
                archive_data = file.read()

            with zipfile.ZipFile(
                io.BytesIO(archive_data),
                "r",
            ) as archive:
                if archive.testzip() is not None:
                    raise ValueError(
                        "ZIP-архив повреждён."
                    )

                entries = {}

                for info in archive.infolist():
                    raw_name = info.filename.replace(
                        "\\",
                        "/",
                    )

                    is_directory = raw_name.endswith("/")

                    normalized_path = self.normalize_path(
                        raw_name
                    )

                    if is_directory:
                        entries[normalized_path] = {
                            "type": "dir",
                            "data": "",
                        }

                    else:
                        data = archive.read(info)

                        entries[normalized_path] = {
                            "type": "file",
                            "data": base64.b64encode(
                                data
                            ).decode("ascii"),
                        }

                        parent = str(
                            PurePosixPath(
                                normalized_path
                            ).parent
                        )

                        while parent not in ("", "."):
                            parent = self.normalize_path(
                                parent
                            )

                            entries.setdefault(
                                parent,
                                {
                                    "type": "dir",
                                    "data": "",
                                },
                            )

                            if parent == "/":
                                break

                            parent = str(
                                PurePosixPath(parent).parent
                            )

                entries.setdefault(
                    "/",
                    {
                        "type": "dir",
                        "data": "",
                    },
                )

        except zipfile.BadZipFile as error:
            raise ValueError(
                "Неверный формат VFS: "
                "файл не является ZIP-архивом."
            ) from error

        except OSError as error:
            raise OSError(
                f"Ошибка чтения VFS: {error}"
            ) from error

        self.entries = entries
        self.name = os.path.basename(zip_path)
        self.physical_path = zip_path

    def initialize_default(self):
        self.clear()

        if not self.physical_path:
            return

        try:
            with zipfile.ZipFile(
                self.physical_path,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ):
                pass

        except OSError as error:
            raise OSError(
                "Не удалось очистить физическое "
                f"представление VFS: {error}"
            ) from error


vfs = VirtualFileSystem()


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

    return f"{username}@{hostname}:{display_dir}$ "


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
    print(f"ls: args = {args}")


def command_cd(args):
    print(f"cd: args = {args}")


def command_vfs_init(args):
    if args:
        print(
            "Ошибка: команда vfs-init "
            "не принимает аргументов"
        )
        return False

    try:
        vfs.initialize_default()

    except OSError as error:
        print(f"Ошибка: {error}")
        return False

    print("VFS инициализирована значениями по умолчанию.")
    print("Физическое представление VFS очищено.")

    return True


def command_exit(args):
    if args:
        print(
            "Ошибка: команда exit "
            "не принимает аргументов"
        )
        return False

    print("Выход из эмулятора.")

    return True


def execute_command(command_line):
    command, args = parse_command(command_line)

    if command is None:
        print(
            "Ошибка: некорректные кавычки в команде."
        )
        return False

    if not command:
        return True

    if command == "ls":
        command_ls(args)
        return True

    if command == "cd":
        command_cd(args)
        return True

    if command == "vfs-init":
        return command_vfs_init(args)

    if command == "exit":
        if command_exit(args):
            return "exit"

        return False

    print(
        f"Ошибка: неизвестная команда: {command}"
    )

    return False


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Эмулятор UNIX-подобной ОС"
    )

    parser.add_argument(
        "--vfs-path",
        help=(
            "Путь к физическому расположению "
            "виртуальной файловой системы"
        ),
    )

    parser.add_argument(
        "--script-path",
        help="Путь к стартовому скрипту",
    )

    return parser.parse_args()


def print_configuration(args):
    print("Конфигурация:")
    print(
        f"  Путь к VFS: "
        f"{args.vfs_path or 'не указан'}"
    )
    print(
        f"  Путь к скрипту: "
        f"{args.script_path or 'не указан'}"
    )


def load_vfs(vfs_path):
    if not vfs_path:
        print(
            "VFS: путь не указан, "
            "используется пустая VFS."
        )

        vfs.clear()
        vfs.physical_path = None

        return True

    try:
        vfs.load_from_zip(vfs_path)

    except (
        FileNotFoundError,
        ValueError,
        OSError,
    ) as error:
        print(f"Ошибка загрузки VFS: {error}")

        return False

    print(f"VFS загружена: {vfs.name}")
    print(
        f"Записей в памяти: "
        f"{len(vfs.entries)}"
    )

    return True


def run_startup_script(script_path):
    try:
        with open(
            script_path,
            "r",
            encoding="utf-8",
        ) as script_file:

            for line_number, line in enumerate(
                script_file,
                start=1,
            ):
                command_line = line.strip()

                if not command_line:
                    continue

                print(
                    get_prompt() + command_line
                )

                result = execute_command(
                    command_line
                )

                if result is False:
                    print(
                        "Ошибка выполнения скрипта "
                        f"на строке {line_number}."
                    )
                    break

                if result == "exit":
                    break

    except FileNotFoundError:
        print(
            "Ошибка: файл скрипта не найден: "
            f"{script_path}"
        )

    except OSError as error:
        print(
            f"Ошибка при чтении скрипта: {error}"
        )


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
    print(
        "Доступны команды: "
        "ls, cd, vfs-init, exit"
    )

    print_configuration(args)

    if not load_vfs(args.vfs_path):
        return

    if args.script_path:
        run_startup_script(args.script_path)

    run_interactive_mode()


if __name__ == "__main__":
    main()