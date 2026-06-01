from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from src.test_module import build_test, TestSession
from src.database import update_test_result


class TestScreen(QWidget):
    def __init__(self, on_back=None, on_done=None):
        super().__init__()
        self._on_back  = on_back
        self._on_done  = on_done
        self._session: TestSession | None = None
        self._session_id: int | None = None
        self._delay_hours: int = 0
        self._build_ui()

    def start(self, words: list[dict], session_id: int, delay_hours: int = 0):
        self._session_id  = session_id
        self._delay_hours = delay_hours
        self._session     = build_test(words)
        self._show_question()

    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 50, 80, 50)
        layout.setSpacing(20)

        self._header = QLabel("Тест")
        self._header.setStyleSheet("font-size: 20px; color: #8080b0;")
        self._header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._header)

        self._word_label = QLabel("")
        self._word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._word_label.setStyleSheet(
            "font-size: 44px; font-weight: bold; color: #ffffff; padding: 20px;"
        )
        layout.addWidget(self._word_label)

        self._context_label = QLabel("")
        self._context_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._context_label.setStyleSheet("font-size: 14px; color: #6060a0; font-style: italic;")
        self._context_label.setWordWrap(True)
        layout.addWidget(self._context_label)

        layout.addSpacing(10)

        # 4 answer buttons
        self._btn_options: list[QPushButton] = []
        for i in range(4):
            btn = QPushButton("")
            btn.setFixedHeight(52)
            btn.setStyleSheet("""
                QPushButton {
                    background: #16213e;
                    border: 1px solid #4a4a8a;
                    border-radius: 10px;
                    font-size: 17px;
                    color: #e0e0e0;
                    padding: 8px 20px;
                }
                QPushButton:hover { background: #2a2a5a; }
            """)
            btn.clicked.connect(lambda _, idx=i: self._answer(idx))
            layout.addWidget(btn)
            self._btn_options.append(btn)

        layout.addSpacing(16)

        self._result_label = QLabel("")
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self._result_label)

        layout.addStretch()

    # ------------------------------------------------------------------
    def _show_question(self):
        if self._session is None or self._session.done:
            self._show_result()
            return

        q = self._session.current_question()
        total = self._session.total
        current = self._session.current + 1

        self._header.setText(f"Вопрос {current} из {total}")
        self._word_label.setText(q.word)
        self._context_label.setText(q.options[0] if False else "")  # context hidden during test
        self._result_label.setText("")

        for i, btn in enumerate(self._btn_options):
            btn.setText(q.options[i])
            btn.setEnabled(True)
            btn.setStyleSheet("""
                QPushButton {
                    background: #16213e; border: 1px solid #4a4a8a;
                    border-radius: 10px; font-size: 17px;
                    color: #e0e0e0; padding: 8px 20px;
                }
                QPushButton:hover { background: #2a2a5a; }
            """)

    def _answer(self, idx: int):
        if self._session is None:
            return

        q = self._session.current_question()
        chosen = self._btn_options[idx].text()
        correct = self._session.answer(chosen)

        # Visual feedback
        for i, btn in enumerate(self._btn_options):
            btn.setEnabled(False)
            if btn.text() == q.correct:
                btn.setStyleSheet(
                    "QPushButton { background: #2a5a2a; border: 1px solid #4aaa4a; "
                    "border-radius: 10px; font-size: 17px; color: #aaffaa; padding: 8px 20px; }"
                )
            elif i == idx and not correct:
                btn.setStyleSheet(
                    "QPushButton { background: #5a2a2a; border: 1px solid #aa4a4a; "
                    "border-radius: 10px; font-size: 17px; color: #ffaaaa; padding: 8px 20px; }"
                )

        if correct:
            self._result_label.setText("✓")
            self._result_label.setStyleSheet("font-size: 22px; color: #4aaa4a;")
        else:
            self._result_label.setText(f"✗  Правильно: {q.correct}")
            self._result_label.setStyleSheet("font-size: 16px; color: #ff8080;")

        QTimer.singleShot(1200, self._show_question)

    def _show_result(self):
        if self._session is None:
            return

        score = self._session.score
        errors = self._session.errors

        # Save result to DB
        if self._session_id is not None:
            update_test_result(self._session_id, score, self._delay_hours)

        # Clear layout and show results
        for btn in self._btn_options:
            btn.hide()
        self._context_label.hide()
        self._word_label.setStyleSheet(
            "font-size: 64px; font-weight: bold; color: #a0a0ff; padding: 20px;"
        )
        self._word_label.setText(f"{score}%")
        self._header.setText("Результат теста")

        color = "#4aaa4a" if score >= 70 else "#ffaa44" if score >= 40 else "#ff6060"
        self._result_label.setStyleSheet(f"font-size: 15px; color: {color};")

        if errors:
            error_words = ", ".join(q.word for q in errors[:8])
            suffix = f" и ещё {len(errors)-8}" if len(errors) > 8 else ""
            self._result_label.setText(f"Ошибки: {error_words}{suffix}")
        else:
            self._result_label.setText("Отлично! Все слова усвоены.")

        btn_done = QPushButton("← На главную")
        btn_done.setObjectName("primary")
        btn_done.setFixedWidth(200)
        btn_done.clicked.connect(lambda: self._on_done and self._on_done())
        self.layout().addWidget(btn_done, alignment=Qt.AlignmentFlag.AlignCenter)
