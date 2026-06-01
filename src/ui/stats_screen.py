from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog
)
from PyQt6.QtCore import Qt
import json
import csv
from pathlib import Path
from src.database import get_connection


class StatsScreen(QWidget):
    def __init__(self, on_back=None):
        super().__init__()
        self._on_back = on_back
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        header = QHBoxLayout()
        btn_back = QPushButton("← Назад")
        btn_back.setFixedWidth(100)
        btn_back.clicked.connect(lambda: self._on_back and self._on_back())
        title = QLabel("Статистика")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #a0a0ff;")
        header.addWidget(btn_back)
        header.addSpacing(16)
        header.addWidget(title)
        header.addStretch()

        btn_export = QPushButton("⬇  Экспорт CSV")
        btn_export.setFixedWidth(160)
        btn_export.clicked.connect(self._export_csv)
        header.addWidget(btn_export)
        layout.addLayout(header)

        # Summary row
        self._summary = QLabel("")
        self._summary.setStyleSheet("color: #8080b0; font-size: 13px;")
        layout.addWidget(self._summary)

        # Sessions table
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            "Дата", "Слов", "Тип", "Тест сразу", "Тест 24ч", "Тест 72ч", "Усталость"
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setStyleSheet("color: #a0a0ff;")
        self._table.setStyleSheet("""
            QTableWidget { background: #16213e; border: 1px solid #2a2a5a; border-radius: 8px; }
            QTableWidget::item { padding: 6px; }
        """)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

    def refresh(self):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY date DESC LIMIT 50"
        ).fetchall()
        conn.close()

        self._table.setRowCount(0)
        for i, row in enumerate(rows):
            self._table.insertRow(i)
            date = (row["date"] or "")[:16]
            self._table.setItem(i, 0, QTableWidgetItem(date))
            self._table.setItem(i, 1, QTableWidgetItem(str(row["word_count"] or "")))
            self._table.setItem(i, 2, QTableWidgetItem(row["concert_type"] or ""))
            self._table.setItem(i, 3, QTableWidgetItem(
                f"{row['test_immediate']:.1f}%" if row["test_immediate"] is not None else "—"
            ))
            self._table.setItem(i, 4, QTableWidgetItem(
                f"{row['test_24h']:.1f}%" if row["test_24h"] is not None else "—"
            ))
            self._table.setItem(i, 5, QTableWidgetItem(
                f"{row['test_72h']:.1f}%" if row["test_72h"] is not None else "—"
            ))
            self._table.setItem(i, 6, QTableWidgetItem(
                str(row["fatigue_score"]) if row["fatigue_score"] else "—"
            ))

        self._summary.setText(f"Всего сессий: {len(rows)}")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить статистику", "suggestolearn_stats.csv",
            "CSV files (*.csv)"
        )
        if not path:
            return

        conn = get_connection()
        rows = conn.execute("SELECT * FROM sessions ORDER BY date DESC").fetchall()
        conn.close()

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Дата", "Язык", "Слов", "Тип концерта",
                "Тест сразу %", "Тест 24ч %", "Тест 72ч %",
                "Усталость", "Настройки аудио"
            ])
            for row in rows:
                writer.writerow([
                    row["date"], row["language"], row["word_count"],
                    row["concert_type"], row["test_immediate"],
                    row["test_24h"], row["test_72h"],
                    row["fatigue_score"], row["audio_settings"]
                ])
