# Эмулятор UNIX shell

## Описание

Проект представляет собой эмулятор командной оболочки UNIX,
реализованный на языке Python (Вариант 5 stage1).

Текущая версия проекта реализует первый этап задания — REPL
(Read-Eval-Print Loop).

Программа отображает приглашение командной строки с информацией
о пользователе, имени компьютера и текущем каталоге.

Поддерживаются следующие команды:

* `ls` — заглушка команды просмотра содержимого каталога;
* `cd` — заглушка команды перехода в каталог;
* `exit` — завершение работы эмулятора.

## Структура проекта

```text
shell-emulator/
├── src/
│   └── emulator.py
├── tests/
├── .gitignore
├── README.md
├── run.sh
└── run.bat
```

## Требования

* Python 3.8 или выше.

Дополнительные библиотеки не требуются.

## Запуск

### Windows

Из корневой папки проекта:

```bash
run.bat
```

Или напрямую:

```bash
python src\emulator.py
```

### Linux/macOS

Используйте:

```bash
./run.sh
```

Или напрямую:

```bash
python3 src/emulator.py
```

## Использование

После запуска программа выводит приглашение:

```text
username@hostname:~$
```

После приглашения можно ввести команду.

### Команда ls

```text
username@hostname:~$ ls
ls: args=[]
```

С аргументами:

```text
username@hostname:~$ ls -l test
ls: args=['-l', 'test']
```

### Команда cd

```text
username@hostname:~$ cd test
cd: args=['test']
```

### Неизвестная команда

```text
username@hostname:~$ hello
Ошибка: неизвестная команда: hello
```

### Некорректные кавычки

```text
username@hostname:~$ ls "test
Ошибка: некорректные кавычки в команде.
```

### Выход

```text
username@hostname:~$ exit
Выход из эмулятора.
```

## Тестирование

Тесты проекта находятся в каталоге `tests`.

Для запуска тестов используется:

```bash
python -m pytest
```

## Основные функции

В файле `src/emulator.py` реализованы следующие функции:

* `get_prompt()` — формирует приглашение командной строки;
* `parse_command()` — разбирает введённую команду и её аргументы;
* `command_ls()` — обрабатывает команду `ls`;
* `command_cd()` — обрабатывает команду `cd`;
* `main()` — запускает основной цикл REPL.

## Стиль кода

Код проекта написан с соблюдением соглашений PEP 8.

Для проверки стиля можно использовать:

```bash
python -m pycodestyle src tests
```

## Git

Для коммитов используется формат Conventional Commits.

Примеры:

```text
feat: add shell emulator
test: add parser tests
docs: update README
fix: handle invalid command quotes
refactor: improve command parsing
```
