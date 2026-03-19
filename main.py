import functools
import os
import random
import sys
import datetime
import json
import requests

import markdown
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QEvent
from PyQt5.QtGui import QFontMetrics, QFont
from PyQt5.QtWidgets import QMainWindow, QApplication, QStackedWidget, QLabel, QTextBrowser
from PyQt5.uic import loadUi
import time

# OpenRouter API configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY",
                                    "sk-or-v1-") # apni khud ki api daal


class start_changing_color(QThread):
    pysignal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        while self.running:
            self.pysignal.emit(f"color: rgba(209, 209, 209, {random.random():.2f})")
            time.sleep(0.1 * random.random())

    def stop(self):
        self.running = False


class thread_task(QThread):
    pyqtsignal_ = pyqtSignal(bool, str)

    def __init__(self, question):
        super().__init__()
        self.question = question

        # OpenRouter API configuration
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",  # Optional, for rankings
            "X-Title": "PyQt5 Chat App"  # Optional, shows in OpenRouter dashboard
        }

    def run(self):
        try:
            response_text = self.ask(self.question)
            self.pyqtsignal_.emit(True, response_text)
        except Exception as e:
            print(f"Run error: {e}")
            self.pyqtsignal_.emit(False, f"Error: {str(e)}")

    def ask(self, question):
        try:
            data = {
                "model": "openai/gpt-3.5-turbo",  # Free model available on OpenRouter
                "messages": [
                    {"role": "user", "content": question}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }

            response = requests.post(self.url, headers=self.headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                print(error_msg)
                return error_msg

        except requests.exceptions.Timeout:
            return "Request timed out. Please try again."
        except requests.exceptions.ConnectionError:
            return "Connection error. Please check your internet."
        except Exception as e:
            return f"Unexpected error: {str(e)}"


class thread_display(QThread):
    pyqtsignal_ = pyqtSignal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text
        self.running = True

    def run(self):
        for i in self.text:
            if not self.running:
                break
            self.pyqtsignal_.emit(i)
            time.sleep(0.05)  # Slightly faster display

    def stop(self):
        self.running = False


class FirstPage(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("main.ui", self)
        self.pushButton.raise_()


        self.content = self.scrollAreaWidgetContents
        self.scrollArea.setWidget(self.content)
        self.scrollArea.setWidgetResizable(True)

        self.textEdit.textChanged.connect(self.text_changed)
        self.max_count_line = 10

        self.pushButton.clicked.connect(self.ask_question)

        self.txt_to_display = 'Searching...'

        self.y = 5
        self.gap = 10
        self.max_width = 720
        self.max_character = 80

        self.temp_label = None
        self.change_color = None
        self.thread_task = None

        self.textEdit.installEventFilter(self)

    from PyQt5.QtCore import QEvent

    def eventFilter(self, obj, event):
        if obj == self.textEdit:
            if event.type() == QEvent.KeyPress:  # correct type
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    if event.modifiers() & Qt.ShiftModifier:
                        return False  # allow new line
                    else:
                        self.pushButton.click()  # press send button
                        return True  # event handled
        return super().eventFilter(obj, event)
        return super().eventFilter(obj, event)
    def get_width(self, text):
        font = QFont('Segoe UI', 12)
        metrics = QFontMetrics(font)
        sent = text.split('\n')
        widths = [metrics.width(i) for i in sent]
        max_width = max(widths) if widths else 0
        return min(max_width + 20, self.max_width)

    def get_x(self, text):
        return 721 - self.get_width(text)

    def get_height(self, text):
        return 20 + int(len(text.split('\n')) * 20)

    def insert_question(self, text):
        x = self.get_x(text)
        y = self.y
        h = self.get_height(text)
        w = self.get_width(text)

        label = QLabel(self.content)
        label.setText(text)
        label.setGeometry(x, y, w, h)
        label.setStyleSheet("""
            font: 12pt "Segoe UI";
            padding-left:5px;
            background-color:#303131;
            margin:1px;
            color:rgba(254, 255, 254);
            border-radius:15px;
        """)
        label.setWordWrap(True)
        label.show()
        self.y += h + self.gap
        self.update_scroll_area()
        self.auto_scroll()

    def insert_answer(self, text):
        try:
            x = 10
            y = self.y
            w = 741

            # Convert markdown to HTML
            html = markdown.markdown(text)

            font = QFont("Segoe UI", 12)
            metrics = QFontMetrics(font)
            available_w = w - 20

            # Calculate height based on content
            paragraphs = text.split('\n\n')
            line_count = 0

            for para in paragraphs:
                if para.strip():
                    words = para.split()
                    current_line = ""

                    for word in words:
                        test_line = current_line + " " + word if current_line else word
                        if metrics.width(test_line) <= available_w:
                            current_line = test_line
                        else:
                            line_count += 1
                            current_line = word

                    if current_line:
                        line_count += 1
                    line_count += 1  # Space between paragraphs

            line_count = max(1, line_count)
            h = (line_count * 21) + 45

            tb = QTextBrowser(self.content)
            tb.setHtml(html)
            tb.setOpenExternalLinks(True)
            tb.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            tb.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            tb.setStyleSheet("""
                QTextBrowser {
                    font: 12pt 'Segoe UI';
                    color: white;
                    background: #151416;
                    border-radius: 10px;
                    padding: 10px;
                    margin: 0px;
                    line-height: 1.4;

                }
                QTextBrowser a {
                    color: #8ab4f8;
                }
            """)
            tb.setGeometry(x, y, w, h)
            tb.show()

            self.y += h + self.gap
            self.update_scroll_area()
            self.auto_scroll()

        except Exception as e:
            print(f'Insert answer error: {e}')
            import traceback
            traceback.print_exc()

    def display_temp_message(self, color_style):
        if not self.temp_label:
            self.temp_label = QLabel(self.content)
            self.temp_label.setGeometry(40, self.y, 600, 50)

        self.temp_label.setText(self.txt_to_display)
        self.temp_label.setStyleSheet(f"""
            font: 12pt "Segoe UI";
            {color_style}
        """)
        self.temp_label.show()

    def ask_question(self):
        try:
            question = self.textEdit.toPlainText().strip()
            if len(question) == 0:
                return

            self.insert_question(question)

            print(f'Task started at {datetime.datetime.now().strftime("%H:%M:%S")}')

            # Start color changing animation
            self.change_color = start_changing_color()
            self.change_color.pysignal.connect(self.display_temp_message)
            self.change_color.start()

            # Start API request thread
            self.thread_task = thread_task(question)
            self.thread_task.pyqtsignal_.connect(self.thread_task_done)
            self.thread_task.start()

            # Clear input
            self.textEdit.setText("")

        except Exception as e:
            print(f'Ask question error: {e}')

        self.update_scroll_area()
        self.auto_scroll()

    def thread_task_done(self, is_completed, result):
        try:
            # Stop color animation
            if self.change_color:
                self.change_color.stop()
                self.change_color.quit()
                self.change_color.wait()

            # Hide temp message
            self.quit_changing_color()

            if is_completed:
                print("Answer fetched successfully")
                self.insert_answer(result)
            else:
                print("Error getting response")
                self.insert_answer(f"**Error:** {result}")

            print(f'Task ended at {datetime.datetime.now().strftime("%H:%M:%S")}')

        except Exception as e:
            print(f"Thread task done error: {e}")

    def quit_changing_color(self):
        if self.temp_label:
            self.temp_label.hide()
            self.temp_label = None

    def text_changed(self):
        try:
            self.count_next_line = self.textEdit.toPlainText().count("\n")
            self.change_height()
        except Exception as e:
            print(f'Text changed error: {e}')

    def change_height(self):
        try:
            # Count number of lines in textEdit
            self.count_next_line = self.textEdit.toPlainText().count("\n") + 1

            # Limit to max lines
            lines = min(self.count_next_line, self.max_count_line)

            # Height per line (roughly 20px per line + base 31px for padding)
            new_h = 31 + lines * 20

            # Fixed Y position of textEdit so button stays aligned
            # Let's assume button height is 50px, textEdit grows upward
            base_y = 950  # bottom Y of input area (adjust to your UI)
            new_y = base_y - new_h

            # Set geometry
            self.textEdit.setGeometry(610, new_y, 781, new_h)

            # Raise send button so it stays on top
            self.pushButton.raise_()

            print(f"TextEdit resized: y={new_y}, h={new_h}, lines={lines}")

        except Exception as e:
            print(f"change_height error: {e}")

    def update_scroll_area(self):
        self.content.setMinimumHeight(self.y + 50)

    def auto_scroll(self):
        scroll_bar = self.scrollArea.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def closeEvent(self, event):
        """Clean up threads when closing"""
        if self.change_color and self.change_color.isRunning():
            self.change_color.stop()
            self.change_color.quit()
            self.change_color.wait()

        if self.thread_task and self.thread_task.isRunning():
            self.thread_task.quit()
            self.thread_task.wait()

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = QStackedWidget()
    main_wind = FirstPage()
    widget.addWidget(main_wind)
    widget.showMaximized()
    widget.show()
    sys.exit(app.exec())
