import argparse
import base64
import getpass
import io
import os
import re
import shlex
import socket
import time
import zipfile
from pathlib import PurePosixPath

single_unit = 1

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
        self.cwd = "/"

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
        self.physical_path = None
        self.cwd = "/"

    def _build_entry(self, info, archive):
        raw_name = info.filename.replace("\\", "/")
        is_directory = raw_name.endswith("/")
        normalized_path = self.normalize_path(raw_name)

        if is_directory:
            return normalized_path, {
                "type": "dir",
                "data": "",
            }

        data = archive.read(info)

        return normalized_path, {
            "type": "file",
            "data": base64.b64encode(data).decode("ascii"),
        }

    def _ensure_parents(self, entries, path):
        parent = str(PurePosixPath(path).parent)

        while parent not in ("", "."):
            parent = self.normalize_path(parent)
            entries.setdefault(
                parent,
                {"type": "dir", "data": ""},
            )
            if parent == "/":
                break
            parent = str(PurePosixPath(parent).parent)

    def _read_archive_entries(self, zip_path):
        if not os.path.isfile(zip_path):
            raise FileNotFoundError(
                f"ZIP-архив VFS не найден: {zip_path}"
            )
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
                path, entry = self._build_entry(
                    info,
                    archive,
                )
                entries[path] = entry
                if entry["type"] == "file":
                    self._ensure_parents(entries, path)

            entries.setdefault(
                "/",
                {"type": "dir", "data": ""},
            )

            return entries

    def load_from_zip(self, zip_path):
        try:
            entries = self._read_archive_entries(zip_path)
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
    if is_vfs_active():
        return f"VFS:{vfs.cwd}> "
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

def is_vfs_active():
    return vfs.physical_path is not None

def resolve_vfs_path(path):
    if path.startswith("/"):
        return vfs.normalize_path(path)

    combined = f"{vfs.cwd.rstrip("/")}/{path}"
    return vfs.normalize_path(combined)

def list_vfs(path):
    normalized = resolve_vfs_path(path)
    entry = vfs.entries.get(normalized)
    if entry is None:
        raise FileNotFoundError(
            f"такого файла или каталога нет: {path}"
        )
    if entry["type"] == "file":
        return [PurePosixPath(normalized).name]
    prefix = normalized.rstrip("/") + "/"
    result = []
    for item_path, item in vfs.entries.items():
        if not item_path.startswith(prefix):
            continue
        relative = item_path[len(prefix):]
        if not relative or "/" in relative:
            continue
        name = relative
        if item["type"] == "dir":
            name += "/"
        result.append(name)
    return sorted(result)

def command_ls(args):
    paths = args if args else ["."]
    for path in paths:
        try:
            if is_vfs_active():
                entries = list_vfs(path)
            else:
                target = os.path.expanduser(path)
                if not os.path.exists(target):
                    raise FileNotFoundError(path)
                if os.path.isfile(target):
                    entries = [os.path.basename(
                        os.path.abspath(target))]
                else:
                    entries = sorted(os.listdir(target))
            if len(paths) > 1:
                print(f"{path}:")
            for entry in entries:
                print(entry)
            if len(paths) > 1:
                print()

        except OSError as error:
            print(f"Ошибка ls: {error}")
            return False
    return True


def command_cd(args):
    if len(args) > 1:
        print("Ошибка: cd принимает не более одного аргумента.")
        return False

    path = args[0] if args else "~"
    try:
        if is_vfs_active():
            target = "/" if not args else path
            normalized = resolve_vfs_path(target)
            entry = vfs.entries.get(normalized)

            if entry is None or entry["type"] != "dir":
                raise FileNotFoundError(path)

            vfs.cwd = normalized
        else:
            target = os.path.expanduser(path)
            if not os.path.isdir(target):
                raise FileNotFoundError(path)
            os.chdir(target)

    except OSError as error:
        print(f"Ошибка cd: {error}")
        return False

    return True

def get_system_uptime():
    try:
        if os.name == "nt":
            import ctypes
            return ctypes.windll.kernel32.GetTickCount64() / 1000
        with open("/proc/uptime", "r", encoding="utf-8") as file:
            return float(file.read().split()[0])
    except (OSError, AttributeError, ValueError):
        return time.monotonic()
        
def format_uptime_pretty(uptime_seconds):
    total_seconds = int(uptime_seconds) 
    days, remainder = divmod(total_seconds, 86400) 
    hours, remainder = divmod(remainder, 3600) 
    minutes = remainder // 60 
    parts = []

    if days:
        parts.append(f"{days} day" if days == single_unit else f"{days} days")
    if hours:
        parts.append(
            f"{hours} hour" 
            if hours==single_unit 
            else f"{hours} hours")
    if minutes:
        parts.append(
            f"{minutes} minute"
            if minutes == single_unit
            else f"{minutes} minutes"
        )
    if not parts:
        parts.append("0 minutes")

    return "up " + ", ".join(parts)   

def print_uptime_help():
    print("Использование: uptime [опция]")
    print("Опции:")
    print("  -p, --pretty   человекочитаемый формат")
    print("  -s, --since    время запуска системы")
    print("  -v, --version  версия команды")
    print("  -h, --help     справка")


def print_uptime_version():
    print("uptime 1.0")

def print_uptime_since():
    uptime_seconds = get_system_uptime()
    boot_time = time.time() - uptime_seconds
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_time)))

def print_uptime_pretty():
    uptime_seconds = get_system_uptime()
    print(format_uptime_pretty(uptime_seconds))

def print_uptime_default():
    uptime_seconds = get_system_uptime()
    print(f"up {format_uptime_pretty(uptime_seconds)}")

def command_uptime(args):
    if len(args) > 1:
        print("Ошибка: uptime принимает не более одной опции.")
        return False
    if not args:
        print_uptime_default()
        return True
    modes = {
        "-p": print_uptime_pretty,
        "--pretty": print_uptime_pretty,
        "-s": print_uptime_since,
        "--since": print_uptime_since,
        "-v": print_uptime_version,
        "--version": print_uptime_version,
        "-h": print_uptime_help,
        "--help": print_uptime_help,
    }
    handler = modes.get(args[0])
    if handler is None:
        print(f"Ошибка: неизвестная опция uptime: {args[0]}")
        return False
    handler()
    return True

def command_echo(args):
    print(" ".join(args))
    return True

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
        return command_ls(args)
    if command == "cd":
        return command_cd(args)
    if command == "uptime":
        return command_uptime(args)
    if command == "echo":
        return command_echo(args)
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
        with open(script_path,
            "r",encoding="utf-8",
        ) as script_file:
            for line_number, line in enumerate(
                script_file,
                start=1,
            ):
                command_line = line.strip()
                if not command_line:
                    continue
                print(get_prompt() + command_line)
                result = execute_command(command_line)
                if result is False:
                    print(
                        "Ошибка выполнения скрипта "
                        f"на строке {line_number}."
                    )
                    break
                if result == "exit":
                    return "exit"
        return True

    except FileNotFoundError:
        print(
            "Ошибка: файл скрипта не найден: "
            f"{script_path}"
        )
        return False

    except OSError as error:
        print(
            f"Ошибка при чтении скрипта: {error}"
        )
        return False


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
        "ls, cd, uptime, echo, vfs-init, exit"
    )

    print_configuration(args)

    if not load_vfs(args.vfs_path):
        return

    if args.script_path:
        script_completed = run_startup_script(
            args.script_path
        )
        if script_completed != True:
            return

    run_interactive_mode()


if __name__ == "__main__":
    main()