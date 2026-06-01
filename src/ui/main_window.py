from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from src.database import get_pending_delayed_tests
from src.srs import get_due_count
from src.ui.import_screen import ImportScreen
from src.ui.session_screen import SessionScreen
from src.ui.test_screen import TestScreen
from src.ui.stats_screen import StatsScreen


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SuggestoLearn")
        self.setMinimumSize(900, 620)
        self._apply_theme()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Screens
        self.home_screen    = self._build_home()
        self.import_screen  = ImportScreen(on_back=self._show_home)
        self.session_screen = SessionScreen(on_back=self._show_home,
                                            on_test=self._start_test)
        self.test_screen    = TestScreen(on_back=self._show_home,
                                         on_done=self._show_home)
        self.stats_screen   = StatsScreen(on_back=self._show_home)

        self.stack.addWidget(self.home_screen)
        self.stack.addWidget(self.import_screen)
        self.stack.addWidget(self.session_screen)
        self.stack.addWidget(self.test_screen)
        self.stack.addWidget(self.stats_screen)

        self._show_home()

        # Check for pending delayed tests every time app gains focus
        self._delayed_test_timer = QTimer(self)
        self._delayed_test_timer.timeout.connect(self._check_delayed_tests)
        self._delayed_test_timer.start(10_000)  # every 10 sec

    # ------------------------------------------------------------------
    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1a2e;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #16213e;
                color: #e0e0e0;
                border: 1px solid #4a4a8a;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #4a4a8a;
            }
            QPushButton:pressed {
                background-color: #6a6aaa;
            }
            QPushButton#primary {
                background-color: #4a4a8a;
                font-size: 17px;
                font-weight: bold;
            }
            QPushButton#primary:hover {
                background-color: #6a6aaa;
            }
            QPushButton#danger {
                border-color: #8a4a4a;
                color: #ffaaaa;
            }
            QPushButton#danger:hover {
                background-color: #8a4a4a;
            }
            QLabel#title {
                font-size: 32px;
                font-weight: bold;
                color: #a0a0ff;
            }
            QLabel#subtitle {
                font-size: 14px;
                color: #8080b0;
            }
            QLabel#badge {
                background-color: #4a4a8a;
                border-radius: 10px;
                padding: 4px 12px;
                font-size: 13px;
                color: #c0c0ff;
            }
            QFrame#card {
                background-color: #16213e;
                border: 1px solid #2a2a5a;
                border-radius: 12px;
            }
        """)

    # ------------------------------------------------------------------
    def _build_home(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(60, 50, 60, 50)
        layout.setSpacing(0)

        # Title
        title = QLabel("SuggestoLearn")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Суггестокибернетический метод изучения английского")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        # SRS badge
        self._srs_label = QLabel()
        self._srs_label.setObjectName("badge")
        self._srs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._srs_label.setFixedHeight(32)
        layout.addWidget(self._srs_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(36)

        # Buttons
        btn_session = QPushButton("▶  Новая сессия")
        btn_session.setObjectName("primary")
        btn_session.setFixedWidth(320)
        btn_session.clicked.connect(self._show_session)

        btn_review = QPushButton("🔁  Повторение")
        btn_review.setFixedWidth(320)
        btn_review.clicked.connect(self._show_review)

        btn_import = QPushButton("📂  Библиотека слов")
        btn_import.setFixedWidth(320)
        btn_import.clicked.connect(self._show_import)

        btn_stats = QPushButton("📊  Статистика")
        btn_stats.setFixedWidth(320)
        btn_stats.clicked.connect(self._show_stats)

        for btn in (btn_session, btn_review, btn_import, btn_stats):
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addSpacing(12)

        layout.addStretch()

        # Delayed test banner (hidden by default)
        self._delayed_banner = QLabel()
        self._delayed_banner.setObjectName("badge")
        self._delayed_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._delayed_banner.hide()
        layout.addWidget(self._delayed_banner, alignment=Qt.AlignmentFlag.AlignCenter)

        self._refresh_badges()
        return widget

    # ------------------------------------------------------------------
    def _refresh_badges(self):
        due = get_due_count("en")
        if due > 0:
            self._srs_label.setText(f"Сегодня к повторению: {due} слов")
            self._srs_label.show()
        else:
            self._srs_label.hide()

    def _check_delayed_tests(self):
        pending = get_pending_delayed_tests()
        if pending:
            t = pending[0]
            hours = t["hours_delay"]
            self._delayed_banner.setText(
                f"Отложенный тест готов ({hours}ч назад) — {t['word_count']} слов.  "
                f"[Нажмите для прохождения]"
            )
            self._delayed_banner.show()
            self._delayed_banner.mousePressEvent = lambda _: self._start_delayed_test(t)
        else:
            self._delayed_banner.hide()

    # ------------------------------------------------------------------
    def _show_home(self):
        self._refresh_badges()
        self.stack.setCurrentWidget(self.home_screen)

    def _show_import(self):
        self.stack.setCurrentWidget(self.import_screen)

    def _show_session(self):
        self.session_screen.load_words(review_mode=False)
        self.stack.setCurrentWidget(self.session_screen)

    def _show_review(self):
        self.session_screen.load_words(review_mode=True)
        self.stack.setCurrentWidget(self.session_screen)

    def _show_stats(self):
        self.stats_screen.refresh()
        self.stack.setCurrentWidget(self.stats_screen)

    def _start_test(self, words: list[dict], session_id: int):
        self.test_screen.start(words, session_id, delay_hours=0)
        self.stack.setCurrentWidget(self.test_screen)

    def _start_delayed_test(self, task: dict):
        from src.database import get_words
        words = get_words("en", limit=task["word_count"])
        self.test_screen.start(words, task["session_id"],
                                delay_hours=task["hours_delay"])
        self.stack.setCurrentWidget(self.test_screen)
