import os
import sqlite3

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('static', 'dynamic')),
    weapon_type TEXT NOT NULL,
    distance INTEGER,
    shots_count INTEGER NOT NULL,
    target_id TEXT,
    target_type TEXT,
    flow_type TEXT DEFAULT 'standard',
    scoring_method_id TEXT,
    scoring_method TEXT NOT NULL,
    scoring_config_json TEXT,
    static_values_json TEXT,
    description TEXT,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    exercise_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    raw_time REAL,
    penalty_time REAL,
    final_time REAL,
    total_score REAL,
    max_score REAL,
    percentage REAL,
    hit_factor REAL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS weapons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT NOT NULL,
    weapon_type TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS shot_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    shot_number INTEGER NOT NULL,
    phase_index INTEGER,
    phase_name TEXT,
    phase_type TEXT,
    series_index INTEGER,
    shot_in_phase INTEGER,
    value REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dynamic_hits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    zone_key TEXT,
    zone_name TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def migrate_legacy_schema(db):
    row = db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sessions'"
    ).fetchone()
    if not row:
        return
    columns = [item["name"] for item in db.execute("PRAGMA table_info(sessions)").fetchall()]
    if "exercise_id" in columns:
        migrate_columns(db)
        return
    backup_name = "legacy_sessions_backup"
    db.execute(f"ALTER TABLE sessions RENAME TO {backup_name}")
    db.commit()


def add_column(db, table, column, definition):
    exists = db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    if not exists:
        return
    columns = [item["name"] for item in db.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_columns(db):
    add_column(db, "exercises", "user_id", "INTEGER")
    add_column(db, "exercises", "target_id", "TEXT")
    add_column(db, "exercises", "flow_type", "TEXT DEFAULT 'standard'")
    add_column(db, "exercises", "scoring_method_id", "TEXT")
    db.execute("UPDATE exercises SET scoring_method_id = scoring_method WHERE scoring_method_id IS NULL")
    add_column(db, "sessions", "user_id", "INTEGER")
    db.execute(
        """
        UPDATE sessions
        SET user_id = (SELECT user_id FROM exercises WHERE exercises.id = sessions.exercise_id)
        WHERE user_id IS NULL
        """
    )
    add_column(db, "weapons", "user_id", "INTEGER")
    add_column(db, "shot_entries", "phase_index", "INTEGER")
    add_column(db, "shot_entries", "phase_name", "TEXT")
    add_column(db, "shot_entries", "phase_type", "TEXT")
    add_column(db, "shot_entries", "series_index", "INTEGER")
    add_column(db, "shot_entries", "shot_in_phase", "INTEGER")
    add_column(db, "dynamic_hits", "zone_key", "TEXT")
    db.commit()


def init_db(app):
    os.makedirs(app.instance_path, exist_ok=True)
    with app.app_context():
        db = get_db()
        migrate_legacy_schema(db)
        db.executescript(SCHEMA)
        migrate_columns(db)
        db.commit()
    app.teardown_appcontext(close_db)
