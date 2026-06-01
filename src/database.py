import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "suggestolearn.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS words (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                language    TEXT NOT NULL DEFAULT 'en',
                word        TEXT NOT NULL,
                translation TEXT NOT NULL,
                context     TEXT NOT NULL,
                audio_main  TEXT,
                audio_sub   TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                language        TEXT NOT NULL DEFAULT 'en',
                date            DATETIME DEFAULT CURRENT_TIMESTAMP,
                word_count      INTEGER,
                concert_type    TEXT,
                audio_settings  TEXT,
                test_immediate  REAL,
                test_24h        REAL,
                test_72h        REAL,
                fatigue_score   INTEGER
            );

            CREATE TABLE IF NOT EXISTS srs_schedule (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id     INTEGER NOT NULL REFERENCES words(id),
                language    TEXT NOT NULL DEFAULT 'en',
                next_review DATETIME,
                interval    INTEGER DEFAULT 1,
                ease_factor REAL DEFAULT 2.5,
                repetitions INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS delayed_tests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL REFERENCES sessions(id),
                due_at      DATETIME NOT NULL,
                hours_delay INTEGER NOT NULL,
                completed   INTEGER DEFAULT 0
            );
        """)
    conn.close()


def add_words(words: list[dict], language: str = "en") -> tuple[int, list[str]]:
    """
    Insert words into DB. Returns (inserted_count, list_of_warnings).
    Each word dict: {word, translation, context}
    """
    conn = get_connection()
    inserted = 0
    warnings = []

    with conn:
        for w in words:
            existing = conn.execute(
                "SELECT id FROM words WHERE language = ? AND word = ?",
                (language, w["word"].strip())
            ).fetchone()

            if existing:
                warnings.append(f"Дубль пропущен: «{w['word']}»")
                continue

            conn.execute(
                "INSERT INTO words (language, word, translation, context) VALUES (?, ?, ?, ?)",
                (language, w["word"].strip(), w["translation"].strip(), w["context"].strip())
            )
            inserted += 1

    conn.close()
    return inserted, warnings


def get_words(language: str = "en", limit: int = 300) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM words WHERE language = ? ORDER BY created_at DESC LIMIT ?",
        (language, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_words_due_for_review(language: str = "en") -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT w.* FROM words w
        JOIN srs_schedule s ON s.word_id = w.id
        WHERE w.language = ? AND s.next_review <= datetime('now')
        ORDER BY s.next_review ASC
    """, (language,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_session(language: str, word_count: int, concert_type: str,
                 audio_settings: dict) -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            """INSERT INTO sessions (language, word_count, concert_type, audio_settings)
               VALUES (?, ?, ?, ?)""",
            (language, word_count, concert_type, json.dumps(audio_settings))
        )
        session_id = cur.lastrowid

        # Schedule delayed tests: 24h and 72h
        for hours in (24, 72):
            conn.execute(
                """INSERT INTO delayed_tests (session_id, due_at, hours_delay)
                   VALUES (?, datetime('now', ?), ?)""",
                (session_id, f"+{hours} hours", hours)
            )
    conn.close()
    return session_id


def update_test_result(session_id: int, score: float, delay_hours: int = 0):
    conn = get_connection()
    with conn:
        if delay_hours == 0:
            conn.execute(
                "UPDATE sessions SET test_immediate = ? WHERE id = ?",
                (score, session_id)
            )
        elif delay_hours == 24:
            conn.execute(
                "UPDATE sessions SET test_24h = ? WHERE id = ?",
                (score, session_id)
            )
        elif delay_hours == 72:
            conn.execute(
                "UPDATE sessions SET test_72h = ? WHERE id = ?",
                (score, session_id)
            )
        conn.execute(
            """UPDATE delayed_tests SET completed = 1
               WHERE session_id = ? AND hours_delay = ?""",
            (session_id, delay_hours)
        )
    conn.close()


def get_pending_delayed_tests() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT dt.*, s.word_count, s.language
        FROM delayed_tests dt
        JOIN sessions s ON s.id = dt.session_id
        WHERE dt.completed = 0 AND dt.due_at <= datetime('now')
        ORDER BY dt.due_at ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
