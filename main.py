import sys
import getpass
import os
import socket
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QFont


# Создаем класс (виджет) терминала на основе виджета QTextEdit
class TerminalWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Получение имени пользователя и хоста из ОС
        username = getpass.getuser()
        hostname = socket.gethostname() if not socket.gethostname().endswith(".local") else socket.gethostname().split('.')[0]
        self.prompt = f"{username}@{hostname} $ "

        # Список для хранения истории команд
        self.history = []
        self.history_index = -1

        self.setFont(QFont("Monaco", 13))

        # Установка начального приглашения
        self.setPlainText(self.prompt)
        self.moveCursor(QTextCursor.End)

        # Сохранение позиции начала ввода
        self.input_start_pos = self.textCursor().position()

    # Обработчик нажатий клавиш
    def keyPressEvent(self, event):
        # Получение текущей позиции курсора
        cursor = self.textCursor()
        cursor_pos = cursor.position()

        # Запрет редактирования текста до input_start_pos (истории терминала)
        if cursor_pos <= self.input_start_pos:
            if event.key() in (Qt.Key_Backspace, Qt.Key_Left, Qt.Key_Up):
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
            else:
                # Для других клавиш перемещаем курсор в конец
                self.moveCursor(QTextCursor.End)
                cursor = self.textCursor()
                cursor_pos = cursor.position()

        # Обработка специальных клавиш
        if event.key() == Qt.Key_Return:
            self.execute_command()
            return
        elif event.key() == Qt.Key_Backspace:
            if cursor_pos == self.input_start_pos:
                # Не позволяем удалить приглашение
                return
        elif event.key() == Qt.Key_Up:
            self.navigate_history(-1)
            return
        elif event.key() == Qt.Key_Down:
            self.navigate_history(1)
            return
        elif event.key() == Qt.Key_Home:
            # Перемещаем в начало зоны ввода
            cursor.setPosition(self.input_start_pos)
            self.setTextCursor(cursor)
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

        if direction < 0:  # Стрелка вверх
            if self.history_index > 0:
                self.history_index -= 1
        else:  # Стрелка вниз
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
            else:
                self.history_index = len(self.history)
                self.replace_command('')
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

        # Вставка новой  команды
        self.insertPlainText(command)
        self.moveCursor(QTextCursor.End)


# Главное окно приложения
class MainWindow(QMainWindow):
    def __init__(self):
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

        self.terminal = TerminalWidget()
        layout.addWidget(self.terminal)

        self.setCentralWidget(central_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
