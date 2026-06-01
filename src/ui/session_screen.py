from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QProgressBar, QMessageBox, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

from src.database import get_words, get_words_due_for_review, save_session
from src.tts_engine import build_all_audio
from src.audio_mixer import build_session_audio, MUSIC_TRACKS
from src.session import SessionPlayer, Phase


class BuildWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(dict, list)   # audio_paths, words

    def __init__(self, words: list[dict], music_active: str, music_passive: str):
        super().__init__()
        self.words         = words
        self.music_active  = music_active
        self.music_passive = music_passive

    def run(self):
        words = build_all_audio(
            self.words,
            progress_callback=lambda c, t: self.progress.emit(c, t)
        )
        paths = build_session_audio(
            words,
            active_music=self.music_active,
            passive_music=self.music_passive,
        )
        self.finished.emit(paths, words)


class SessionScreen(QWidget):
    def __init__(self, on_back=None, on_test=None):
        super().__init__()
        self._on_back  = on_back
        self._on_test  = on_test
        self._words:   list[dict] = []
        self._player:  SessionPlayer | None = None
        self._session_id: int | None = None
        self._build_ui()

    def load_words(self, review_mode: bool = False):
        self._words = (get_words_due_for_review("en")
                       if review_mode else get_words("en", limit=300))
        count = len(self._words)
        self._word_count_label.setText(f"Слов в сессии: {count}")
        self._btn_start.setEnabled(count > 0)
        if count == 0:
            self._status.setText("Нет слов. Сначала импортируйте словарь.")
        else:
            self._status.setText("")
        self._show_config()

    # ------------------------------------------------------------------
    def _build_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(60, 40, 60, 40)
        self._layout.setSpacing(16)

        # --- CONFIG PANEL ---
        self._config_panel = QWidget()
        cfg = QVBoxLayout(self._config_panel)
        cfg.setSpacing(14)

        header = QHBoxLayout()
        btn_back = QPushButton("← Назад")
        btn_back.setFixedWidth(100)
        btn_back.clicked.connect(lambda: self._on_back and self._on_back())
        title = QLabel("Настройка сессии")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #a0a0ff;")
        header.addWidget(btn_back)
        header.addSpacing(16)
        header.addWidget(title)
        header.addStretch()
        cfg.addLayout(header)

        self._word_count_label = QLabel("Слов в сессии: —")
        self._word_count_label.setStyleSheet("font-size: 15px; color: #c0c0ff;")
        cfg.addWidget(self._word_count_label)

        # Music selectors
        music_row = QHBoxLayout()
        music_row.addWidget(QLabel("Музыка (активный концерт):"))
        self._active_music = QComboBox()
        for k in MUSIC_TRACKS:
            if k.startswith("active"):
                self._active_music.addItem(k.replace("_", " ").title(), k)
        music_row.addWidget(self._active_music)
        music_row.addSpacing(30)
        music_row.addWidget(QLabel("Музыка (пассивный концерт):"))
        self._passive_music = QComboBox()
        for k in MUSIC_TRACKS:
            if k.startswith("passive"):
                self._passive_music.addItem(k.replace("_", " ").title(), k)
        music_row.addWidget(self._passive_music)
        music_row.addStretch()
        cfg.addLayout(music_row)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #8a4a4a; font-size: 13px;")
        cfg.addWidget(self._status)

        self._btn_start = QPushButton("▶  Начать сессию")
        self._btn_start.setObjectName("primary")
        self._btn_start.setFixedWidth(240)
        self._btn_start.clicked.connect(self._start_build)
        cfg.addWidget(self._btn_start, alignment=Qt.AlignmentFlag.AlignLeft)

        self._layout.addWidget(self._config_panel)

        # --- BUILD PROGRESS ---
        self._build_panel = QWidget()
        self._build_panel.hide()
        bp = QVBoxLayout(self._build_panel)
        bp_label = QLabel("Генерация аудио...")
        bp_label.setStyleSheet("font-size: 16px; color: #a0a0ff;")
        bp.addWidget(bp_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self._build_bar = QProgressBar()
        self._build_bar.setFixedHeight(18)
        bp.addWidget(self._build_bar)
        self._build_status = QLabel("")
        self._build_status.setStyleSheet("color: #8080b0; font-size: 13px;")
        bp.addWidget(self._build_status, alignment=Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._build_panel)

        # --- PLAYBACK PANEL ---
        self._play_panel = QWidget()
        self._play_panel.hide()
        pp = QVBoxLayout(self._play_panel)
        pp.setSpacing(20)

        self._phase_label = QLabel("Фаза входа")
        self._phase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._phase_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #a0a0ff;")
        pp.addWidget(self._phase_label)

        self._word_label = QLabel("")
        self._word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._word_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #ffffff;")
        pp.addWidget(self._word_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(20)
        pp.addWidget(self._progress_bar)

        self._btn_stop = QPushButton("⏹  Прервать сессию")
        self._btn_stop.setObjectName("danger")
        self._btn_stop.setFixedWidth(220)
        self._btn_stop.clicked.connect(self._confirm_stop)
        pp.addWidget(self._btn_stop, alignment=Qt.AlignmentFlag.AlignCenter)

        self._layout.addWidget(self._play_panel)
        self._layout.addStretch()

    # ------------------------------------------------------------------
    def _show_config(self):
        self._config_panel.show()
        self._build_panel.hide()
        self._play_panel.hide()

    def _start_build(self):
        self._config_panel.hide()
        self._build_panel.show()
        self._build_bar.setMaximum(len(self._words))
        self._build_bar.setValue(0)

        active  = self._active_music.currentData()
        passive = self._passive_music.currentData()

        self._worker = BuildWorker(self._words, active, passive)
        self._worker.progress.connect(self._on_build_progress)
        self._worker.finished.connect(self._on_build_done)
        self._worker.start()

    def _on_build_progress(self, current: int, total: int):
        self._build_bar.setValue(current)
        self._build_status.setText(f"Обработано {current} из {total} слов...")

    def _on_build_done(self, paths: dict, words: list[dict]):
        self._build_panel.hide()
        self._play_panel.show()
        self._words = words

        self._session_id = save_session(
            language="en",
            word_count=len(words),
            concert_type="both",
            audio_settings={
                "active_music":  self._active_music.currentData(),
                "passive_music": self._passive_music.currentData(),
            }
        )

        self._progress_bar.setMaximum(len(words))
        self._progress_bar.setValue(0)

        self._player = SessionPlayer(
            active_audio=paths["active"],
            passive_audio=paths["passive"],
            word_count=len(words),
            on_phase_change=self._on_phase,
            on_progress=self._on_progress,
            on_done=self._on_session_done,
        )
        self._player.start()

    def _on_phase(self, phase: Phase):
        labels = {
            Phase.ENTRY:           "Расслабьтесь...",
            Phase.ACTIVE_CONCERT:  "Активный концерт",
            Phase.BETWEEN:         "Закройте глаза...",
            Phase.PASSIVE_CONCERT: "Пассивный концерт",
            Phase.EXIT:            "Сессия завершена",
            Phase.DONE:            "",
        }
        self._phase_label.setText(labels.get(phase, ""))

        # Dim screen for passive concert
        if phase == Phase.PASSIVE_CONCERT:
            self._word_label.hide()
            self.setStyleSheet("background-color: #0a0a1a;")
        elif phase == Phase.ACTIVE_CONCERT:
            self._word_label.show()
            self.setStyleSheet("")

    def _on_progress(self, current: int, total: int):
        self._progress_bar.setValue(current)
        if current < total and self._words:
            idx = min(current, len(self._words) - 1)
            self._word_label.setText(
                self._words[idx]["word"] + "\n" +
                self._words[idx]["translation"]
            )

    def _on_session_done(self):
        if self._on_test and self._session_id is not None:
            self._on_test(self._words, self._session_id)

    def _confirm_stop(self):
        reply = QMessageBox.question(
            self, "Прервать сессию?",
            "Прерывание разрушает состояние потока.\nВы уверены?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and self._player:
            self._player.stop()
            self._show_config()
