from __future__ import annotations
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox,
    QHeaderView, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from src.importer import parse_csv, validate_preview
from src.database import add_words


class ImportWorker(QThread):
    finished = pyqtSignal(int, list)  # inserted_count, warnings

    def __init__(self, words: list[dict]):
        super().__init__()
        self.words = words

    def run(self):
        count, warnings = add_words(self.words, language="en")
        self.finished.emit(count, warnings)


class ImportScreen(QWidget):
    def __init__(self, on_back=None):
        super().__init__()
        self._on_back   = on_back
        self._all_words: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        btn_back = QPushButton("← Назад")
        btn_back.setFixedWidth(100)
        btn_back.clicked.connect(lambda: self._on_back and self._on_back())
        title = QLabel("Библиотека слов")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #a0a0ff;")
        header.addWidget(btn_back)
        header.addSpacing(16)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Drop zone
        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(self._load_file)
        layout.addWidget(self._drop_zone)

        # OR button
        btn_open = QPushButton("📂  Выбрать CSV файл")
        btn_open.setFixedWidth(220)
        btn_open.clicked.connect(self._open_dialog)
        layout.addWidget(btn_open, alignment=Qt.AlignmentFlag.AlignLeft)

        # Format hint
        hint = QLabel(
            "Формат: слово [TAB] перевод [TAB] контекст  |  Кодировка: UTF-8\n"
            "Пример:  negotiate    вести переговоры    We need to negotiate the terms."
        )
        hint.setStyleSheet("color: #6060a0; font-size: 12px;")
        layout.addWidget(hint)

        # Preview table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Слово", "Перевод", "Контекст"])
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setStyleSheet("color: #a0a0ff;")
        self._table.setStyleSheet("""
            QTableWidget { background: #16213e; border: 1px solid #2a2a5a; border-radius: 8px; }
            QTableWidget::item { padding: 6px; }
        """)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        # Status + import button
        bottom = QHBoxLayout()
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #8080b0; font-size: 13px;")
        self._btn_import = QPushButton("✅  Импортировать в базу")
        self._btn_import.setObjectName("primary")
        self._btn_import.setFixedWidth(240)
        self._btn_import.setEnabled(False)
        self._btn_import.clicked.connect(self._do_import)
        bottom.addWidget(self._status_label)
        bottom.addStretch()
        bottom.addWidget(self._btn_import)
        layout.addLayout(bottom)

    # ------------------------------------------------------------------
    def _open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать файл слов", "",
            "CSV/TXT files (*.csv *.txt);;All files (*)"
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        words, errors = parse_csv(path)
        preview, _ = validate_preview(path, n=10)

        self._all_words = words
        self._populate_table(preview, errors)

        total = len(words)
        err   = len(errors)
        self._status_label.setText(
            f"Найдено: {total} слов    Ошибок: {err}"
            + (f"  ⚠ {errors[0]}" if errors else "")
        )
        self._btn_import.setEnabled(total > 0)

    def _populate_table(self, words: list[dict], errors: list[str]):
        self._table.setRowCount(0)
        for i, w in enumerate(words):
            self._table.insertRow(i)
            self._table.setItem(i, 0, QTableWidgetItem(w["word"]))
            self._table.setItem(i, 1, QTableWidgetItem(w["translation"]))
            self._table.setItem(i, 2, QTableWidgetItem(w["context"]))

        # Mark error rows red
        for err in errors:
            try:
                line = int(err.split("Строка")[1].split(":")[0].strip()) - 1
                for col in range(3):
                    item = self._table.item(line, col)
                    if item:
                        item.setBackground(QColor("#5a2a2a"))
            except (IndexError, ValueError):
                pass

    def _do_import(self):
        if not self._all_words:
            return
        self._btn_import.setEnabled(False)
        self._btn_import.setText("Импортирую...")
        self._worker = ImportWorker(self._all_words)
        self._worker.finished.connect(self._on_import_done)
        self._worker.start()

    def _on_import_done(self, count: int, warnings: list[str]):
        self._btn_import.setText("✅  Импортировать в базу")
        msg = f"Добавлено: {count} слов."
        if warnings:
            msg += f"\nПропущено дублей: {len(warnings)}"
        QMessageBox.information(self, "Импорт завершён", msg)
        self._all_words = []
        self._table.setRowCount(0)
        self._status_label.setText("")


# ------------------------------------------------------------------
class DropZone(QFrame):
    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFixedHeight(80)
        self.setObjectName("card")
        self.setStyleSheet("""
            QFrame#card {
                border: 2px dashed #4a4a8a;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(self)
        lbl = QLabel("Перетащите CSV/TXT сюда")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #6060a0; font-size: 14px;")
        layout.addWidget(lbl)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith((".csv", ".txt")):
                self.file_dropped.emit(path)
                break
