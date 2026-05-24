"""
SQLite database module for consultation history persistence.
Replaces the flat JSON file with a proper relational database.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional


DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
DB_PATH = os.path.join(DB_DIR, "consultations.db")


def _ensure_db_dir() -> None:
    os.makedirs(DB_DIR, exist_ok=True)


@contextmanager
def get_connection():
    """Context manager for SQLite connections."""
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    _ensure_db_dir()
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS consultations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT UNIQUE NOT NULL,
                patient_name TEXT NOT NULL,
                patient_age INTEGER NOT NULL,
                initial_case TEXT NOT NULL,
                diagnostic_summary TEXT DEFAULT '',
                interim_care TEXT DEFAULT '',
                physician_treatment TEXT DEFAULT '',
                conclusion TEXT DEFAULT '',
                final_report TEXT DEFAULT '',
                final_report_json TEXT DEFAULT '{}',
                consultation_status TEXT DEFAULT 'started',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS questions_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER NOT NULL,
                question_number INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                FOREIGN KEY (consultation_id) REFERENCES consultations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_consultations_thread
                ON consultations(thread_id);
            CREATE INDEX IF NOT EXISTS idx_qa_consultation
                ON questions_answers(consultation_id);
        """)


def save_consultation(thread_id: str, report_json: dict) -> int:
    """Insert or update a consultation record. Returns the row id."""
    now = datetime.now().isoformat()
    patient_info = report_json.get("patient_info", {})

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM consultations WHERE thread_id = ?", (thread_id,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE consultations SET
                    diagnostic_summary = ?,
                    interim_care = ?,
                    physician_treatment = ?,
                    conclusion = ?,
                    final_report_json = ?,
                    consultation_status = ?,
                    updated_at = ?
                WHERE thread_id = ?""",
                (
                    report_json.get("diagnostic_summary", ""),
                    report_json.get("interim_care", ""),
                    report_json.get("physician_treatment", ""),
                    report_json.get("conclusion", ""),
                    json.dumps(report_json, ensure_ascii=False),
                    "completed",
                    now,
                    thread_id,
                ),
            )
            consultation_id = existing["id"]
        else:
            cursor = conn.execute(
                """INSERT INTO consultations
                    (thread_id, patient_name, patient_age, initial_case,
                     diagnostic_summary, interim_care, physician_treatment,
                     conclusion, final_report_json, consultation_status,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    thread_id,
                    patient_info.get("name", "Inconnu"),
                    patient_info.get("age", 0),
                    patient_info.get("initial_case", ""),
                    report_json.get("diagnostic_summary", ""),
                    report_json.get("interim_care", ""),
                    report_json.get("physician_treatment", ""),
                    report_json.get("conclusion", ""),
                    json.dumps(report_json, ensure_ascii=False),
                    "completed",
                    now,
                    now,
                ),
            )
            consultation_id = cursor.lastrowid

        conn.execute(
            "DELETE FROM questions_answers WHERE consultation_id = ?",
            (consultation_id,),
        )
        for i, qa in enumerate(report_json.get("questions_and_answers", [])):
            conn.execute(
                """INSERT INTO questions_answers
                    (consultation_id, question_number, question, answer)
                VALUES (?, ?, ?, ?)""",
                (consultation_id, i + 1, qa.get("question", ""), qa.get("answer", "")),
            )

    return consultation_id


def get_consultation(thread_id: str) -> Optional[dict]:
    """Retrieve a consultation by thread_id."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM consultations WHERE thread_id = ?", (thread_id,)
        ).fetchone()
        if not row:
            return None

        qa_rows = conn.execute(
            """SELECT question_number, question, answer
               FROM questions_answers
               WHERE consultation_id = ?
               ORDER BY question_number""",
            (row["id"],),
        ).fetchall()

        return {
            "thread_id": row["thread_id"],
            "patient_name": row["patient_name"],
            "patient_age": row["patient_age"],
            "initial_case": row["initial_case"],
            "diagnostic_summary": row["diagnostic_summary"],
            "interim_care": row["interim_care"],
            "physician_treatment": row["physician_treatment"],
            "conclusion": row["conclusion"],
            "final_report_json": json.loads(row["final_report_json"]),
            "consultation_status": row["consultation_status"],
            "questions_and_answers": [
                {"question": qa["question"], "answer": qa["answer"]}
                for qa in qa_rows
            ],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


def get_all_consultations() -> list:
    """Retrieve all consultations ordered by creation date (newest first)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT thread_id, patient_name, patient_age, consultation_status, created_at "
            "FROM consultations ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
