import json
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app

from .database import get_db


FALLBACK_SCORING = {"targets": [], "scoring_methods": []}


def scoring_path():
    return Path(current_app.static_folder) / "data" / "scoring.json"


def scoring_payload():
    try:
        return json.loads(scoring_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return FALLBACK_SCORING


def all_targets():
    return scoring_payload().get("targets", [])


def all_scoring_methods():
    return scoring_payload().get("scoring_methods", [])


def get_target(target_id):
    return next((target for target in all_targets() if target["id"] == target_id), None)


def get_scoring_method(method_id):
    aliases = {"points_only": "points_sum", "idpa": "idpa_time_plus"}
    method_id = aliases.get(method_id, method_id)
    return next((method for method in all_scoring_methods() if method["id"] == method_id), None)


def default_target_for_type(exercise_type):
    return "b4" if exercise_type == "static" else "ipsc"


def default_scoring_for_type(exercise_type):
    return "points_sum" if exercise_type == "static" else "ipsc_minor"


def default_scoring_for_target(target_id, exercise_type):
    if exercise_type != "dynamic":
        return default_scoring_for_type(exercise_type)
    return {
        "idpa": "idpa_time_plus",
        "ipsc": "ipsc_minor",
        "universal_silhouette": "time_plus",
    }.get(target_id, default_scoring_for_type(exercise_type))


def target_values(target):
    if not target:
        return []
    if target.get("input_mode") == "number_range":
        return list(range(int(target.get("min", 1)), int(target.get("max", 100)) + 1))
    return [zone.get("value", 0) for zone in target.get("zones", []) if "value" in zone]


def config_from_scoring(target, method_id):
    method = get_scoring_method(method_id) or get_scoring_method(default_scoring_for_type((target or {}).get("category", "static")))
    if not method:
        return {"label": "Punkte", "result": "points", "zones": {}}
    if method["category"] == "static":
        return {
            "label": method["name"],
            "result": "points",
            "higher_is_better": method.get("higher_is_better", True),
            "uses_time": method.get("uses_time", False),
            "input_mode": (target or {}).get("input_mode", "buttons"),
            "min": (target or {}).get("min"),
            "max": (target or {}).get("max"),
            "zones": {str(zone["label"]): zone.get("value", 0) for zone in (target or {}).get("zones", [])},
        }
    zones = {}
    zone_keys = {}
    for zone in method.get("zones", []):
        label = zone["label"]
        key = zone.get("key", slug(label))
        zones[label] = zone.get("value", zone.get("penalty_seconds", 0))
        zone_keys[label] = key
    return {
        "label": method["name"],
        "result": method.get("result_type", "points"),
        "higher_is_better": method.get("higher_is_better", True),
        "uses_time": method.get("uses_time", False),
        "zones": zones,
        "zone_keys": zone_keys,
    }


def scoring_presets():
    return {
        method["id"]: {"label": method["name"], "result": method["result_type"], "category": method["category"]}
        for method in all_scoring_methods()
    }


SCORING_PRESETS = {
    "points_sum": {"label": "Punkte", "result": "points"},
    "points_only": {"label": "Points Only", "result": "points"},
    "ipsc_minor": {"label": "IPSC Minor", "result": "hit_factor"},
    "ipsc_major": {"label": "IPSC Major", "result": "hit_factor"},
    "idpa_time_plus": {"label": "IDPA Time Plus", "result": "final_time"},
    "idpa": {"label": "IDPA", "result": "final_time"},
    "time_plus": {"label": "Time Plus", "result": "final_time"},
    "points_dynamic": {"label": "Dynamische Punkte", "result": "points"},
}


DEFAULT_EXERCISES = [
    ("Feldschiessen 300 m Langwaffe", "static", "Langwaffe", 300, 18, "b4", "points_sum", "feldschiessen", 1),
    ("Obligatorisches 300 m Langwaffe", "static", "Langwaffe", 300, 20, "b4", "points_sum", "obligatorisch", 1),
    ("Feldschiessen 25 m Kurzwaffe", "static", "Kurzwaffe", 25, 18, "p10_25m", "points_sum", "feldschiessen", 1),
    ("Obligatorisches 25 m Kurzwaffe", "static", "Kurzwaffe", 25, 20, "p10_25m", "points_sum", "obligatorisch", 0),
    ("Bill Drill 7 m IPSC Minor", "dynamic", "Kurzwaffe", 7, 6, "ipsc", "ipsc_minor", "standard", 1),
    ("Bill Drill 7 m IDPA", "dynamic", "Kurzwaffe", 7, 6, "idpa", "idpa_time_plus", "standard", 0),
]


def flow_plan(flow_type):
    if flow_type == "feldschiessen":
        return [
            {"phase_index": 1, "phase_name": "Einzelschuss 1", "phase_type": "single", "series_index": None, "shots": 1},
            {"phase_index": 2, "phase_name": "Einzelschuss 2", "phase_type": "single", "series_index": None, "shots": 1},
            {"phase_index": 3, "phase_name": "Einzelschuss 3", "phase_type": "single", "series_index": None, "shots": 1},
            {"phase_index": 4, "phase_name": "Serie 1", "phase_type": "series", "series_index": 1, "shots": 5},
            {"phase_index": 5, "phase_name": "Serie 2", "phase_type": "series", "series_index": 2, "shots": 5},
            {"phase_index": 6, "phase_name": "Serie 3", "phase_type": "series", "series_index": 3, "shots": 5},
        ]
    if flow_type == "obligatorisch":
        singles = [
            {"phase_index": index, "phase_name": f"Einzelschuss {index}", "phase_type": "single", "series_index": None, "shots": 1}
            for index in range(1, 6)
        ]
        series = [
            {"phase_index": index + 5, "phase_name": f"Serie {index}", "phase_type": "series", "series_index": index, "shots": 5}
            for index in range(1, 4)
        ]
        return singles + series
    return []


def exercise_from_form(form):
    exercise_type = form.get("type", "static")
    target_id = form.get("target_id") or default_target_for_type(exercise_type)
    target = get_target(target_id) or get_target(default_target_for_type(exercise_type))
    method = form.get("scoring_method_id") or form.get("scoring_method") or default_scoring_for_target(target_id, exercise_type)
    if not get_scoring_method(method):
        method = default_scoring_for_type(exercise_type)
    flow_type = form.get("flow_type") or "standard"
    values = target_values(target) if target and target["category"] == "static" else []
    return {
        "name": form["name"],
        "type": exercise_type,
        "weapon_type": form.get("weapon_type", "Kurzwaffe"),
        "distance": int(form.get("distance") or 0),
        "shots_count": int(form.get("shots_count") or 1),
        "target_id": target["id"] if target else target_id,
        "target_type": target["name"] if target else form.get("target_type", ""),
        "flow_type": flow_type if exercise_type == "static" else "standard",
        "scoring_method_id": method,
        "scoring_method": method,
        "scoring_config": config_from_scoring(target, method),
        "static_values": values,
        "description": form.get("description", ""),
        "is_favorite": as_bool(form.get("is_favorite")),
    }


def as_bool(value):
    if isinstance(value, bool):
        return 1 if value else 0
    if value is None:
        return 0
    return 0 if str(value).lower() in {"0", "false", "off", "no"} else 1


def parse_number_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return [float(item) for item in value]
    return [float(part.strip()) for part in str(value).split(",") if part.strip()]


def exercise_to_json(exercise):
    item = dict(exercise)
    item["scoring_config"] = json.loads(item.pop("scoring_config_json") or "{}")
    item["static_values"] = json.loads(item.pop("static_values_json") or "[]")
    item["scoring_method_id"] = item.get("scoring_method_id") or item.get("scoring_method")
    item["flow_plan"] = flow_plan(item.get("flow_type") or "standard")
    item["target"] = get_target(item.get("target_id")) or {}
    item["scoring_label"] = item["scoring_config"].get("label") or item["scoring_method_id"]
    item["is_favorite"] = bool(item["is_favorite"])
    return item


def session_to_json(row):
    item = dict(row)
    entries = get_db().execute(
        """
        SELECT shot_number, phase_index, phase_name, phase_type, series_index, shot_in_phase, value
        FROM shot_entries WHERE session_id = ? ORDER BY shot_number
        """,
        (item["id"],),
    ).fetchall()
    item["shot_entries"] = [dict(entry) for entry in entries]
    item["shots"] = [entry["value"] for entry in entries]
    hits = get_db().execute(
        "SELECT zone_key, zone_name, count FROM dynamic_hits WHERE session_id = ? ORDER BY id", (item["id"],)
    ).fetchall()
    item["hits"] = {entry["zone_name"]: entry["count"] for entry in hits}
    item["hit_entries"] = [dict(entry) for entry in hits]
    return item


def seed_default_exercises():
    db = get_db()
    count = db.execute("SELECT COUNT(*) AS count FROM exercises").fetchone()["count"]
    if count:
        return
    for name, kind, weapon, distance, shots, target_id, method, flow, favorite in DEFAULT_EXERCISES:
        create_default_exercise(name, kind, weapon, distance, shots, target_id, method, flow, favorite)


def seed_missing_default_exercises():
    created = 0
    for name, kind, weapon, distance, shots, target_id, method, flow, favorite in DEFAULT_EXERCISES:
        exists = get_db().execute("SELECT id FROM exercises WHERE name = ?", (name,)).fetchone()
        if not exists:
            create_default_exercise(name, kind, weapon, distance, shots, target_id, method, flow, favorite)
            created += 1
    return created


def create_default_exercise(name, kind, weapon, distance, shots, target_id, method, flow, favorite):
    target = get_target(target_id)
    create_exercise(
        {
            "name": name,
            "type": kind,
            "weapon_type": weapon,
            "distance": distance,
            "shots_count": shots,
            "target_id": target_id,
            "target_type": target["name"] if target else "",
            "flow_type": flow,
            "scoring_method_id": method,
            "scoring_method": method,
            "scoring_config": config_from_scoring(target, method),
            "static_values": target_values(target) if kind == "static" else [],
            "description": "",
            "is_favorite": favorite,
        }
    )


def create_exercise(data):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO exercises (
            name, type, weapon_type, distance, shots_count, target_id, target_type,
            flow_type, scoring_method_id, scoring_method, scoring_config_json, static_values_json,
            description, is_favorite
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["name"], data["type"], data["weapon_type"], data["distance"], data["shots_count"],
            data.get("target_id"), data.get("target_type", ""), data.get("flow_type", "standard"),
            data.get("scoring_method_id") or data["scoring_method"],
            data["scoring_method"], json.dumps(data.get("scoring_config", {})), json.dumps(data.get("static_values", [])),
            data.get("description", ""), int(data.get("is_favorite", 0)),
        ),
    )
    db.commit()
    return cursor.lastrowid


def update_exercise(exercise_id, data):
    get_db().execute(
        """
        UPDATE exercises
        SET name = ?, type = ?, weapon_type = ?, distance = ?, shots_count = ?,
            target_id = ?, target_type = ?, flow_type = ?, scoring_method_id = ?, scoring_method = ?,
            scoring_config_json = ?, static_values_json = ?, description = ?,
            is_favorite = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            data["name"], data["type"], data["weapon_type"], data["distance"], data["shots_count"],
            data.get("target_id"), data.get("target_type", ""), data.get("flow_type", "standard"),
            data.get("scoring_method_id") or data["scoring_method"],
            data["scoring_method"], json.dumps(data.get("scoring_config", {})), json.dumps(data.get("static_values", [])),
            data.get("description", ""), int(data.get("is_favorite", 0)), exercise_id,
        ),
    )
    get_db().commit()


def delete_exercise(exercise_id):
    get_db().execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
    get_db().commit()


def get_exercise(exercise_id):
    row = get_db().execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
    return with_exercise_stats(exercise_to_json(row)) if row else None


def all_exercises():
    rows = get_db().execute("SELECT * FROM exercises ORDER BY is_favorite DESC, name").fetchall()
    return [with_exercise_stats(exercise_to_json(row)) for row in rows]


def recent_exercises(limit=4):
    rows = get_db().execute(
        """
        SELECT e.*, MAX(COALESCE(s.date, e.updated_at)) AS sort_date
        FROM exercises e LEFT JOIN sessions s ON s.exercise_id = e.id
        GROUP BY e.id ORDER BY sort_date DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [with_exercise_stats(exercise_to_json(row)) for row in rows]


def favorite_exercises():
    return [item for item in all_exercises() if item["is_favorite"]]


def sessions_for_exercise(exercise_id, limit=None):
    sql = "SELECT * FROM sessions WHERE exercise_id = ? ORDER BY date DESC, id DESC"
    params = [exercise_id]
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return [session_to_json(row) for row in get_db().execute(sql, params).fetchall()]


def latest_sessions(limit=20):
    rows = get_db().execute(
        """
        SELECT s.*, e.name AS exercise_name, e.type AS exercise_type, e.weapon_type
        FROM sessions s JOIN exercises e ON e.id = s.exercise_id
        ORDER BY s.date DESC, s.id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def with_exercise_stats(exercise):
    sessions = sessions_for_exercise(exercise["id"])
    exercise["runs_count"] = len(sessions)
    exercise["last_run"] = sessions[0] if sessions else None
    exercise["best_run"] = best_session(exercise, sessions)
    exercise["average"] = average_result(exercise, sessions)
    exercise["trend"] = trend(exercise, sessions)
    exercise["trend_percent"] = trend_percent(exercise, list(reversed(sessions)))
    exercise["chart"] = chart_payload(exercise, list(reversed(sessions)))
    return exercise


def result_key(exercise):
    if exercise["type"] == "static":
        return "percentage"
    result = exercise.get("scoring_config", {}).get("result")
    if result == "hit_factor":
        return "hit_factor"
    if result == "final_time":
        return "final_time"
    return "total_score"


def lower_is_better(exercise):
    return result_key(exercise) == "final_time"


def best_session(exercise, sessions):
    if not sessions:
        return None
    key = result_key(exercise)
    values = [item for item in sessions if item.get(key) is not None]
    if not values:
        return None
    return min(values, key=lambda item: item[key]) if lower_is_better(exercise) else max(values, key=lambda item: item[key])


def average_result(exercise, sessions):
    key = result_key(exercise)
    values = [item.get(key) for item in sessions if item.get(key) is not None]
    return round(sum(values) / len(values), 2) if values else 0


def trend(exercise, sessions):
    pct = trend_percent(exercise, list(reversed(sessions)))
    if pct is None or abs(pct) < 0.1:
        return "neutral"
    return "up" if pct > 0 else "down"


def trend_percent(exercise, chronological):
    if len(chronological) < 2:
        return None
    key = result_key(exercise)
    old = chronological[0].get(key)
    new = chronological[-1].get(key)
    if not old or new is None:
        return None
    return round(((old - new) / old if lower_is_better(exercise) else (new - old) / old) * 100, 1)


def format_result(exercise, session):
    if not session:
        return "Noch kein Run"
    if exercise["type"] == "static":
        return f"{session['total_score']:.0f} P · {session['percentage']:.1f}%"
    result = exercise.get("scoring_config", {}).get("result")
    if result == "hit_factor":
        return f"HF {session['hit_factor']:.2f} · {session['total_score']:.0f} P"
    if result == "final_time":
        return f"{session['final_time']:.2f} s"
    return f"{session['total_score']:.0f} P"


def dashboard_stats():
    db = get_db()
    month = date.today().isoformat()[:7]
    return {
        "total_runs": db.execute("SELECT COUNT(*) AS count FROM sessions").fetchone()["count"],
        "total_exercises": db.execute("SELECT COUNT(*) AS count FROM exercises").fetchone()["count"],
        "favorites": db.execute("SELECT COUNT(*) AS count FROM exercises WHERE is_favorite = 1").fetchone()["count"],
        "month_runs": db.execute("SELECT COUNT(*) AS count FROM sessions WHERE substr(date, 1, 7) = ?", (month,)).fetchone()["count"],
    }


def app_counts():
    db = get_db()
    return {
        "exercises": db.execute("SELECT COUNT(*) AS count FROM exercises").fetchone()["count"],
        "runs": db.execute("SELECT COUNT(*) AS count FROM sessions").fetchone()["count"],
    }


def reset_all_data():
    db = get_db()
    db.execute("DELETE FROM dynamic_hits")
    db.execute("DELETE FROM shot_entries")
    db.execute("DELETE FROM sessions")
    db.execute("DELETE FROM exercises")
    db.commit()


def create_session_for_exercise(exercise, form):
    if exercise["type"] == "static":
        entries = parse_shot_entries(form.get("shot_entries_json"), form.get("shots"), exercise)
        shots = [entry["value"] for entry in entries]
        max_value = max(exercise["static_values"]) if exercise["static_values"] else 0
        total = sum(shots)
        max_score = exercise["shots_count"] * max_value
        data = {
            "raw_time": None, "penalty_time": None, "final_time": None,
            "total_score": total, "max_score": max_score,
            "percentage": (total / max_score * 100) if max_score else 0, "hit_factor": None,
        }
        return insert_session(exercise["id"], form, data, shots=entries)
    hits = {zone: int(form.get(f"zone_{slug(zone)}", 0) or 0) for zone in exercise["scoring_config"].get("zones", {})}
    return insert_session(exercise["id"], form, score_dynamic(exercise, float(form.get("raw_time") or 0), hits), hits=hits, exercise=exercise)


def parse_shot_entries(entries_json, shots_csv, exercise):
    if entries_json:
        try:
            entries = json.loads(entries_json)
            return [{**entry, "value": float(entry["value"])} for entry in entries]
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    plan = flow_plan(exercise.get("flow_type") or "standard")
    entries = []
    for index, value in enumerate(parse_number_list(shots_csv), start=1):
        phase = phase_for_shot(plan, index)
        entries.append({**phase, "shot_number": index, "value": value})
    return entries


def phase_for_shot(plan, shot_number):
    if not plan:
        return {"phase_index": None, "phase_name": "Standard", "phase_type": "single", "series_index": None, "shot_in_phase": shot_number}
    cursor = 0
    for phase in plan:
        if shot_number <= cursor + phase["shots"]:
            return {
                "phase_index": phase["phase_index"], "phase_name": phase["phase_name"], "phase_type": phase["phase_type"],
                "series_index": phase["series_index"], "shot_in_phase": shot_number - cursor,
            }
        cursor += phase["shots"]
    return {"phase_index": None, "phase_name": "Extra", "phase_type": "single", "series_index": None, "shot_in_phase": shot_number}


def static_session_blocks(exercise, session):
    entries = session.get("shot_entries", [])
    if not entries:
        entries = [
            {**phase_for_shot(exercise.get("flow_plan", []), index), "shot_number": index, "value": value}
            for index, value in enumerate(session.get("shots", []), start=1)
        ]
    normalized = []
    for entry in entries:
        if entry.get("phase_index") is None:
            fallback = phase_for_shot(exercise.get("flow_plan", []), entry["shot_number"])
            entry = {**entry, **fallback}
        normalized.append(entry)
    if exercise.get("flow_type") in {"feldschiessen", "obligatorisch"}:
        return static_flow_blocks(exercise, normalized)
    grouped = {}
    for entry in normalized:
        title = entry.get("phase_name") or "Schüsse"
        grouped.setdefault(title, []).append(entry)
    return [block_summary(title, shots) for title, shots in grouped.items()]


def static_flow_blocks(exercise, entries):
    flow_type = exercise.get("flow_type")
    single_count = 3 if flow_type == "feldschiessen" else 5
    blocks = [("Einzelfeuer", list(range(1, single_count + 1)))]
    cursor = single_count + 1
    for series in range(1, 4):
        blocks.append((f"Serie {series}", list(range(cursor, cursor + 5))))
        cursor += 5
    by_number = {entry["shot_number"]: entry for entry in entries}
    return [block_summary(title, [by_number[num] for num in numbers if num in by_number]) for title, numbers in blocks]


def block_summary(title, shots):
    values = [float(entry["value"]) for entry in shots]
    total = sum(values)
    return {
        "title": title,
        "shots": shots,
        "sum": total,
        "average": (total / len(values)) if values else 0,
    }


def score_dynamic(exercise, raw_time, hits):
    zones = exercise["scoring_config"].get("zones", {})
    mode = exercise["scoring_config"].get("result", "points")
    score = sum(hits.get(zone, 0) * float(value) for zone, value in zones.items())
    if mode == "final_time":
        return {"raw_time": raw_time, "penalty_time": score, "final_time": raw_time + score, "total_score": None, "max_score": None, "percentage": None, "hit_factor": None}
    return {
        "raw_time": raw_time if mode == "hit_factor" else None, "penalty_time": None, "final_time": None,
        "total_score": score, "max_score": None, "percentage": None,
        "hit_factor": (score / raw_time) if mode == "hit_factor" and raw_time > 0 else None,
    }


def insert_session(exercise_id, form, data, shots=None, hits=None, exercise=None):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO sessions (
            exercise_id, date, raw_time, penalty_time, final_time, total_score,
            max_score, percentage, hit_factor, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (exercise_id, form.get("date") or date.today().isoformat(), data.get("raw_time"), data.get("penalty_time"),
         data.get("final_time"), data.get("total_score"), data.get("max_score"), data.get("percentage"),
         data.get("hit_factor"), form.get("notes", "")),
    )
    session_id = cursor.lastrowid
    for index, entry in enumerate(shots or [], start=1):
        db.execute(
            """
            INSERT INTO shot_entries (
                session_id, shot_number, phase_index, phase_name, phase_type, series_index, shot_in_phase, value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id, entry.get("shot_number", index), entry.get("phase_index"), entry.get("phase_name"),
                entry.get("phase_type"), entry.get("series_index"), entry.get("shot_in_phase"), entry["value"],
            ),
        )
    zone_keys = (exercise or {}).get("scoring_config", {}).get("zone_keys", {})
    for zone, count in (hits or {}).items():
        db.execute(
            "INSERT INTO dynamic_hits (session_id, zone_key, zone_name, count) VALUES (?, ?, ?, ?)",
            (session_id, zone_keys.get(zone, slug(zone)), zone, count),
        )
    db.commit()
    return session_id


def get_session(session_id):
    row = get_db().execute(
        "SELECT s.*, e.name AS exercise_name, e.type AS exercise_type FROM sessions s JOIN exercises e ON e.id = s.exercise_id WHERE s.id = ?",
        (session_id,),
    ).fetchone()
    return session_to_json(row) if row else None


def delete_session(session_id):
    get_db().execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    get_db().commit()


def chart_payload(exercise, sessions):
    key = result_key(exercise)
    unit = "s" if key == "final_time" else ("%" if key == "percentage" else "")
    values = [session.get(key) for session in sessions if session.get(key) is not None]
    dates = [session["date"] for session in sessions if session.get(key) is not None]
    return {
        "title": exercise["name"], "key": key, "unit": unit, "lower_is_better": lower_is_better(exercise),
        "labels": dates, "values": values, "explanation": improvement_text(exercise, values),
    }


def improvement_text(exercise, values):
    if len(values) < 2 or not values[0]:
        return "Noch nicht genug Daten für Trendanalyse."
    old, new = values[0], values[-1]
    pct = ((old - new) / old if lower_is_better(exercise) else (new - old) / old) * 100
    if result_key(exercise) == "final_time":
        return f"Von {old:.2f} s auf {new:.2f} s = {abs(pct):.1f} % {'schneller' if pct >= 0 else 'langsamer'}."
    label = "Punkte" if exercise["type"] == "static" else "besser"
    return f"Von {old:.1f} auf {new:.1f} {label} = {pct:.1f} % Veränderung."


def stats_payload(days=None):
    cutoff = date.today() - timedelta(days=days) if days else None
    exercises = []
    for item in all_exercises():
        sessions = sorted(
            sessions_for_exercise(item["id"]),
            key=lambda session: (session["date"], session.get("created_at") or "", session["id"]),
        )
        if cutoff:
            sessions = [session for session in sessions if datetime.fromisoformat(session["date"]).date() >= cutoff]
        exercises.append({**item, "sessions": sessions, "chart": chart_payload(item, sessions)})
    return exercises


def analysis_payload(days=None):
    exercises = stats_payload(days)
    runs = [session for exercise in exercises for session in exercise["sessions"]]
    active = max(exercises, key=lambda item: len(item["sessions"]), default=None)
    trend_items = [primary_trend_summary(exercise) for exercise in exercises if len(exercise["sessions"]) >= 3]
    trend_items = [item for item in trend_items if item]
    best = max(trend_items, key=lambda item: item["percent"], default=None)
    positive = len([item for item in trend_items if item["percent"] > 0])
    static_values = [
        session.get("percentage")
        for exercise in exercises
        if exercise["type"] == "static"
        for session in exercise["sessions"]
        if session.get("percentage") is not None
    ]
    speed_values = [
        session.get("final_time")
        for exercise in exercises
        for session in exercise["sessions"]
        if session.get("final_time") is not None
    ]
    hf_values = [
        session.get("hit_factor")
        for exercise in exercises
        for session in exercise["sessions"]
        if session.get("hit_factor") is not None
    ]
    insights = trend_items[:4]
    if trend_items:
        insights.append({"text": f"Bei {positive} von {len(trend_items)} aktiven Übungen ist dein Trend positiv.", "status": "neutral"})
    else:
        insights.append({"text": "Noch nicht genug Daten für Trendanalyse.", "status": "neutral"})
    return {
        "runs_count": len(runs), "active_exercise": active["name"] if active and active["sessions"] else "Noch keine Runs",
        "best_improvement": best["name"] if best else "Keine Daten",
        "static_precision": average_value(static_values),
        "dynamic_speed": average_value(speed_values),
        "dynamic_hit_factor": average_value(hf_values),
        "insights": insights,
    }


def primary_trend_summary(exercise):
    sessions = exercise.get("sessions", [])
    half = len(sessions) // 2
    if half < 1:
        return None
    key = primary_analysis_key(exercise, sessions)
    if not key:
        return None
    first = [session[key] for session in sessions[:half] if session.get(key) is not None]
    second = [session[key] for session in sessions[half:] if session.get(key) is not None]
    if not first or not second:
        return None
    old, new = sum(first) / len(first), sum(second) / len(second)
    if not old:
        return None
    lower_better = key == "final_time"
    pct = ((old - new) / old if lower_better else (new - old) / old) * 100
    status = "positive" if pct > 0 else ("negative" if pct < 0 else "neutral")
    if key == "final_time":
        text = f"Bei {exercise['name']} bist du um {abs(pct):.1f} % {'schneller' if pct >= 0 else 'langsamer'} geworden."
    elif key == "hit_factor":
        text = f"Bei {exercise['name']} ist dein Hit Factor um {abs(pct):.1f} % {'gestiegen' if pct >= 0 else 'gesunken'}."
    elif exercise["type"] == "static":
        text = f"Bei {exercise['name']} bist du um {abs(pct):.1f} % {'präziser' if pct >= 0 else 'schlechter'} geworden."
    else:
        text = f"Bei {exercise['name']} hat sich dein Score um {abs(pct):.1f} % {'verbessert' if pct >= 0 else 'verschlechtert'}."
    return {"name": exercise["name"], "percent": round(pct, 1), "type": exercise["type"], "key": key, "text": text, "status": status}


def primary_analysis_key(exercise, sessions):
    if exercise["type"] == "static":
        return "percentage" if any(session.get("percentage") is not None for session in sessions) else "total_score"
    result = exercise.get("scoring_config", {}).get("result")
    if result == "hit_factor" and any(session.get("hit_factor") is not None for session in sessions):
        return "hit_factor"
    if result == "final_time" and any(session.get("final_time") is not None for session in sessions):
        return "final_time"
    if any(session.get("total_score") is not None for session in sessions):
        return "total_score"
    return None


def average_change(items):
    return round(sum(item["percent"] for item in items) / len(items), 1) if items else None


def average_value(values):
    return round(sum(values) / len(values), 2) if values else None


def slug(value):
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")
