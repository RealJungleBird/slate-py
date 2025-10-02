import sys
import getpass
import os
import socket
import platform
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QFont


# Создаем класс (виджет) терминала на основе виджета QTextEdit
class TerminalWidget(QTextEdit):
    def __init__(self, vfs_path, startup_script, parent=None):
        super().__init__(parent)

        # Сохранение конфигурации
        self.vfs_path = vfs_path
        self.startup_script = startup_script

        # Получение имени пользователя и хоста из ОС
        username = getpass.getuser()
        hostname = socket.gethostname() if not socket.gethostname().endswith(".local") else socket.gethostname().split('.')[0]
        self.prompt = f"{username}@{hostname} $ "

        # История команд
        self.history = []
        self.history_index = len(self.history)
        self.history_temp = "" # буфер для набранной команды перед навигацией по истории

        if platform.system() == "Windows":
            self.setFont(QFont("Consolas", 13))
        elif platform.system() == "Darwin":
            self.setFont(QFont("Monaco", 13))

        # Установка начального приглашения
        self.setPlainText(self.prompt)
        self.moveCursor(QTextCursor.End)

        # Сохранение позиции начала ввода
        self.input_start_pos = self.textCursor().position()

        self.run_startup_script()

    """
    Читает скрипт, построчно имитирует ввод/вывод команд,
    останавливается при первой ошибке
    """
    def run_startup_script(self):
        try:
            with open(self.startup_script) as f:
                lines = f.readlines()
        except Exception as e:
            self.show_error(f"Ошибка стартового скрипта: {e}")
            return

        for line_number, raw in enumerate(lines, start=1):
            cmd = raw.strip()
            if not cmd:
                continue    # пропуск пустых строк
            # отображаем ввод команды
            self.moveCursor(QTextCursor.End)
            self.insertPlainText(cmd + "\n")

            # парсинг аргументов
            try:
                parts = self.parse_arguments(cmd)
                name = parts[0] if parts else ""
                args = parts[1:]
            except Exception as e:
                self.show_error(f"Строка {line_number}: {e}")
                break   # остановка при ошибке парсинга

            # выполнение команды
            output = self.process_command(name, args)

            # если команда не найдена, считаем это ошибкой скрипта
            if name and output.endswith("не найдена"):
                self.show_error(f"Строка {line_number}: команда \"{name}\" не найдена")
                break

            # вывод результата
            self.moveCursor(QTextCursor.End)
            self.insertPlainText(output + "\n")

            # вывод следующего промпта
            self.moveCursor(QTextCursor.End)
            self.insertPlainText(self.prompt)

        # восстанавливаем позицию для пользовательского ввода
        self.moveCursor(QTextCursor.End)
        self.input_start_pos = self.textCursor().position()

    """
    Обработчик нажатий клавиш
        - стрелки вверх/вниз - навигация по истории
        - Enter для выполнения введенной команды
        - Backspace/Home/Ctrl+A - работа с текстом (только внутри зоны ввода)
    """
    def keyPressEvent(self, event):
        # Получение текущей позиции курсора
        cursor = self.textCursor()
        cursor_pos = cursor.position()

        # Навигация по истории
        if event.key() == Qt.Key_Up:
            self.navigate_history(-1)
            return
        if event.key() == Qt.Key_Down:
            self.navigate_history(1)
            return

        # Запрет редактирования текста до input_start_pos (истории терминала)
        if cursor_pos <= self.input_start_pos:
            if event.key() in (Qt.Key_Backspace, Qt.Key_Left):
                # Блокировка навигации за пределы зоны ввода
                cursor.setPosition(self.input_start_pos)
                self.setTextCursor(cursor)
                return
            elif event.key() == Qt.Key_Home:
                # Перемещаем в начало зоны ввода
                cursor.setPosition(self.input_start_pos)
                self.setTextCursor(cursor)
                return
            elif event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_A:
                # Выделяем только текст в зоне ввода
                cursor.setPosition(self.input_start_pos)
                cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
                return

        # Обработка Enter
        if event.key() == Qt.Key_Return:
            self.execute_command()
            return

        # Разрешаем стандартную обработку для остальных клавиш
        super().keyPressEvent(event)

    def execute_command(self):
        # Получение введенной команды
        cursor = self.textCursor()
        cursor.setPosition(self.input_start_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        command_text = cursor.selectedText().replace('\u2029', '\n').strip()

        if command_text:
            self.history.append(command_text)
            self.history_index = len(self.history)

            # Разбор команды на имя и аргументы
            try:
                command_parts = self.parse_arguments(command_text)
                command = command_parts[0] if command_parts else ""
                args = command_parts[1:] if len(command_parts) > 1 else []
            except Exception as e:
                self.show_error(str(e))
                command = ""
                args = []

            # Обработка команды
            output = self.process_command(command, args)

            # Вывод результата
            self.moveCursor(QTextCursor.End)
            self.insertPlainText("\n" + output)

        # Добавление нового приглашения
        self.moveCursor(QTextCursor.End)
        self.insertPlainText("\n" + self.prompt)
        self.moveCursor(QTextCursor.End)

        # Обновление позиции начала ввода
        self.input_start_pos = self.textCursor().position()

    # Парсер аргументов
    def parse_arguments(self, command_text):
        tokens = []
        current_token = ""
        in_quotes = False
        quote_char = None

        for char in command_text:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
            elif char == ' ' and not in_quotes:
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
            else:
                current_token += char

        if current_token:
            tokens.append(current_token)

        if in_quotes:
            raise Exception("незакрытые кавычки")

        return tokens

    # Обработчик команд
    def process_command(self, command, args):
        # Вывод параметров эмулятора
        if command == "conf-dump":
            lines = [
                f"vfs_path = {self.vfs_path}",
                f"startup_script = {self.startup_script}",
            ]
            return "\n".join(lines)

        # Команды-заглушки
        if command == "ls":
            return f"ls: {' '.join(args)}"
        elif command == "cd":
            return f"cd: {' '.join(args)}"
        elif command == "exit":
            QApplication.quit()
            return ""
        elif command == "":
            return ""
        else:
            return f"{command}: команда не найдена"

    def show_error(self, error_message):
        self.moveCursor(QTextCursor.End)
        self.insertPlainText(f"\nОшибка: {error_message}")

    # Навигация по истории команд
    def navigate_history(self, direction):
        if not self.history:
            return

        cursor = self.textCursor()
        cursor.setPosition(self.input_start_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        current_line = cursor.selectedText().replace('\u2029', '\n')

        if direction < 0:
            if self.history_index == len(self.history):
                self.history_temp = current_line
            if self.history_index > 0:
                self.history_index -= 1
            else:
                return
        else:
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
            else:
                self.history_index = len(self.history)
                self.replace_command(self.history_temp)
                return

        # Замена команды на выбранную из истории
        self.replace_command(self.history[self.history_index])

    # Замена текущей команды
    def replace_command(self, command):
        # Удаление текущей команды
        cursor = self.textCursor()
        cursor.setPosition(self.input_start_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()

        # Вставка новой команды
        self.insertPlainText(command)
        self.moveCursor(QTextCursor.End)


# Главное окно приложения
class MainWindow(QMainWindow):
    def __init__(self, vfs_path, startup_script):
        super().__init__()

        # Получаем имя пользователя и хоста для заголовка окна
        username = getpass.getuser()
        hostname = socket.gethostname() if not socket.gethostname().endswith(".local") else socket.gethostname().split('.')[0]
        self.setWindowTitle(f"Slate - [{username}@{hostname}]")

        # Устанавливаем размер и положение окна
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.terminal = TerminalWidget(vfs_path, startup_script)
        layout.addWidget(self.terminal)

        self.setCentralWidget(central_widget)