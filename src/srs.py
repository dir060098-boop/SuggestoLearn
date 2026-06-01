from __future__ import annotations
from datetime import datetime, timedelta
from src.database import get_connection


def update_srs(word_id: int, quality: int, language: str = "en"):
    """
    Update SRS schedule for a word after test.
    quality: 0-2 = wrong, 3-5 = correct (5 = easy, 3 = hard but correct)
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM srs_schedule WHERE word_id = ?", (word_id,)
    ).fetchone()

    if row:
        interval = row["interval"]
        ease = row["ease_factor"]
        reps = row["repetitions"]
    else:
        interval, ease, reps = 1, 2.5, 0

    if quality < 3:
        interval = 1
        reps = 0
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 3
        else:
            interval = round(interval * ease)
        ease = max(1.3, ease + 0.1 - (5 - quality) * 0.08)
        reps += 1

    next_review = (datetime.now() + timedelta(days=interval)).isoformat()

    with conn:
        if row:
            conn.execute(
                """UPDATE srs_schedule
                   SET next_review = ?, interval = ?, ease_factor = ?, repetitions = ?
                   WHERE word_id = ?""",
                (next_review, interval, ease, reps, word_id)
            )
        else:
            conn.execute(
                """INSERT INTO srs_schedule (word_id, language, next_review, interval, ease_factor, repetitions)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (word_id, language, next_review, interval, ease, reps)
            )
    conn.close()


def get_due_count(language: str = "en") -> int:
    conn = get_connection()
    count = conn.execute(
        """SELECT COUNT(*) FROM srs_schedule
           WHERE language = ? AND next_review <= datetime('now')""",
        (language,)
    ).fetchone()[0]
    conn.close()
    return count
