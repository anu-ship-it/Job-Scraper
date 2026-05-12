"""
core/database.py
SQLite-based storage for resume profiles, scraped jobs, and match results.
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path


DB_PATH = os.environ.get("JOB_SCRAPER_DB", "job_scraper.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS resume_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT (datetime('now')),
            file_path TEXT,
            raw_text TEXT,
            profile_json TEXT
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scraped_at TEXT DEFAULT (datetime('now')),
            source TEXT,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT UNIQUE,
            posted_date TEXT,
            description TEXT,
            description_fetched INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS job_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matched_at TEXT DEFAULT (datetime('now')),
            resume_profile_id INTEGER,
            job_id INTEGER,
            score INTEGER,
            matched_skills TEXT,
            missing_skills TEXT,
            verdict TEXT,
            reasoning TEXT,
            apply_priority TEXT,
            reported INTEGER DEFAULT 0,
            FOREIGN KEY (resume_profile_id) REFERENCES resume_profiles(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT (datetime('now')),
            report_html TEXT,
            match_count INTEGER,
            top_score INTEGER
        );
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


# ─── Resume ───────────────────────────────────────────────────────────────────

def save_resume(file_path: str, raw_text: str, profile: dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO resume_profiles (file_path, raw_text, profile_json) VALUES (?, ?, ?)",
        (file_path, raw_text, json.dumps(profile)),
    )
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def get_latest_resume() -> dict | None:
    conn = get_conn()
    c = conn.cursor()
    row = c.execute(
        "SELECT * FROM resume_profiles ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"],
            "file_path": row["file_path"],
            "raw_text": row["raw_text"],
            "profile": json.loads(row["profile_json"]),
        }
    return None


# ─── Jobs ─────────────────────────────────────────────────────────────────────

def save_jobs(jobs: list) -> int:
    conn = get_conn()
    c = conn.cursor()
    inserted = 0
    for j in jobs:
        try:
            c.execute(
                """INSERT OR IGNORE INTO jobs
                   (source, title, company, location, url, posted_date, description)
                   VALUES (?,?,?,?,?,?,?)""",
                (j["source"], j["title"], j["company"], j["location"],
                 j["url"], j["posted_date"], j.get("description", "")),
            )
            if c.rowcount:
                inserted += 1
        except Exception as e:
            print(f"[DB] save_jobs error: {e}")
    conn.commit()
    conn.close()
    return inserted


def get_unmatched_jobs(resume_profile_id: int, limit: int = 100) -> list:
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute(
        """SELECT j.* FROM jobs j
           WHERE j.id NOT IN (
               SELECT job_id FROM job_matches WHERE resume_profile_id = ?
           )
           ORDER BY j.scraped_at DESC LIMIT ?""",
        (resume_profile_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_job_description(job_id: int, description: str):
    conn = get_conn()
    conn.execute(
        "UPDATE jobs SET description=?, description_fetched=1 WHERE id=?",
        (description, job_id),
    )
    conn.commit()
    conn.close()


# ─── Matches ─────────────────────────────────────────────────────────────────

def save_match(resume_profile_id: int, job_id: int, match: dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO job_matches
           (resume_profile_id, job_id, score, matched_skills, missing_skills,
            verdict, reasoning, apply_priority)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            resume_profile_id,
            job_id,
            match.get("score", 0),
            json.dumps(match.get("matched_skills", [])),
            json.dumps(match.get("missing_skills", [])),
            match.get("verdict", ""),
            match.get("reasoning", ""),
            match.get("apply_priority", "low"),
        ),
    )
    conn.commit()
    mid = c.lastrowid
    conn.close()
    return mid


def get_top_matches(
    resume_profile_id: int,
    threshold: int = 80,
    limit: int = 50,
    unreported_only: bool = False,
) -> list:
    conn = get_conn()
    base = """
        SELECT m.*, j.title, j.company, j.location, j.url, j.source, j.posted_date
        FROM job_matches m
        JOIN jobs j ON m.job_id = j.id
        WHERE m.resume_profile_id = ? AND m.score >= ?
    """
    params = [resume_profile_id, threshold]
    if unreported_only:
        base += " AND m.reported = 0"
    base += " ORDER BY m.score DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(base, params).fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        d["matched_skills"] = json.loads(d.get("matched_skills") or "[]")
        d["missing_skills"] = json.loads(d.get("missing_skills") or "[]")
        results.append(d)
    return results


def mark_matches_reported(match_ids: list):
    conn = get_conn()
    placeholders = ",".join("?" * len(match_ids))
    conn.execute(
        f"UPDATE job_matches SET reported=1 WHERE id IN ({placeholders})",
        match_ids,
    )
    conn.commit()
    conn.close()


# ─── Reports ─────────────────────────────────────────────────────────────────

def save_report(html: str, match_count: int, top_score: int) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO weekly_reports (report_html, match_count, top_score) VALUES (?,?,?)",
        (html, match_count, top_score),
    )
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def get_all_reports() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, created_at, match_count, top_score FROM weekly_reports ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_report_html(report_id: int) -> str | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT report_html FROM weekly_reports WHERE id=?", (report_id,)
    ).fetchone()
    conn.close()
    return row["report_html"] if row else None


# ─── Stats ────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    conn = get_conn()
    stats = {
        "total_jobs": conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "total_matches": conn.execute("SELECT COUNT(*) FROM job_matches").fetchone()[0],
        "high_matches": conn.execute(
            "SELECT COUNT(*) FROM job_matches WHERE score >= 80"
        ).fetchone()[0],
        "total_reports": conn.execute("SELECT COUNT(*) FROM weekly_reports").fetchone()[0],
        "avg_score": conn.execute(
            "SELECT ROUND(AVG(score),1) FROM job_matches"
        ).fetchone()[0] or 0,
    }
    conn.close()
    return stats
