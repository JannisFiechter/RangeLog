import csv
import io
from datetime import date

from flask import Blueprint, Response, abort, jsonify, redirect, render_template, request, send_from_directory, url_for

from .models import (
    all_scoring_methods,
    all_targets,
    analysis_payload,
    all_exercises,
    app_counts,
    create_exercise,
    create_session_for_exercise,
    dashboard_stats,
    delete_exercise,
    delete_session,
    exercise_from_form,
    favorite_exercises,
    format_result,
    get_exercise,
    get_session,
    latest_sessions,
    recent_exercises,
    reset_all_data,
    scoring_payload,
    scoring_presets,
    seed_missing_default_exercises,
    sessions_for_exercise,
    static_session_blocks,
    update_exercise,
)
from .database import get_db

bp = Blueprint("main", __name__)


@bp.app_template_filter("result")
def result_filter(session, exercise):
    return format_result(exercise, session)


@bp.route("/")
def index():
    return render_template(
        "index.html",
        recent=recent_exercises(),
        favorites=favorite_exercises(),
        stats=dashboard_stats(),
        active="home",
    )


@bp.route("/start")
@bp.route("/exercises")
def exercises():
    return render_template("exercises.html", exercises=all_exercises(), active="exercises")


@bp.route("/history")
def history():
    return render_template("history.html", sessions=latest_sessions(50), active="history")


@bp.route("/exercises/new", methods=["GET", "POST"])
def new_exercise():
    if request.method == "POST":
        exercise_id = create_exercise(exercise_from_form(request.form))
        return redirect(url_for("main.exercise_detail", exercise_id=exercise_id))
    return render_template("exercise_form.html", exercise=None, presets=scoring_presets(), targets=all_targets(), scoring_methods=all_scoring_methods(), active="exercises")


@bp.route("/exercises/<int:exercise_id>")
def exercise_detail(exercise_id):
    exercise = get_exercise(exercise_id)
    if not exercise:
        abort(404)
    runs = sessions_for_exercise(exercise_id, limit=8)
    return render_template("exercise_detail.html", exercise=exercise, runs=runs, active="exercises")


@bp.route("/exercises/<int:exercise_id>/edit", methods=["GET", "POST"])
def edit_exercise(exercise_id):
    exercise = get_exercise(exercise_id)
    if not exercise:
        abort(404)
    if request.method == "POST":
        update_exercise(exercise_id, exercise_from_form(request.form))
        return redirect(url_for("main.exercise_detail", exercise_id=exercise_id))
    return render_template("exercise_form.html", exercise=exercise, presets=scoring_presets(), targets=all_targets(), scoring_methods=all_scoring_methods(), active="exercises")


@bp.route("/exercises/<int:exercise_id>/delete", methods=["POST"])
def delete_exercise_route(exercise_id):
    delete_exercise(exercise_id)
    return redirect(url_for("main.exercises"))


@bp.route("/exercises/<int:exercise_id>/run", methods=["GET", "POST"])
def run_form(exercise_id):
    exercise = get_exercise(exercise_id)
    if not exercise:
        abort(404)
    if request.method == "POST":
        session_id = create_session_for_exercise(exercise, request.form)
        return redirect(url_for("main.run_detail", session_id=session_id))
    return render_template("run_form.html", exercise=exercise, current_date=date.today().isoformat(), active="home")


@bp.route("/runs/<int:session_id>")
def run_detail(session_id):
    session = get_session(session_id)
    if not session:
        abort(404)
    exercise = get_exercise(session["exercise_id"])
    blocks = static_session_blocks(exercise, session) if exercise["type"] == "static" else []
    return render_template("run_detail.html", session=session, exercise=exercise, blocks=blocks, active="exercises")


@bp.route("/runs/<int:session_id>/delete", methods=["POST"])
def delete_session_route(session_id):
    session = get_session(session_id)
    if not session:
        abort(404)
    exercise_id = session["exercise_id"]
    delete_session(session_id)
    return redirect(url_for("main.exercise_detail", exercise_id=exercise_id))


@bp.route("/stats")
def stats():
    period = request.args.get("period", "90")
    days = None if period == "all" else int(period or 90)
    return render_template("stats.html", payload=analysis_payload(days), period=period, active="stats")


@bp.route("/settings")
def settings():
    return render_template("settings.html", counts=app_counts(), active="settings")


@bp.route("/manifest.json")
def manifest():
    return send_from_directory("../static", "manifest.json")


@bp.route("/service-worker.js")
def service_worker():
    return send_from_directory("../static", "service-worker.js")


@bp.route("/api/targets")
def api_targets():
    return jsonify({"targets": all_targets()})


@bp.route("/api/scoring")
def api_scoring():
    return jsonify(scoring_payload())


@bp.route("/api/export/json")
def api_export_json():
    db = get_db()
    payload = {
        "exercises": [dict(row) for row in db.execute("SELECT * FROM exercises ORDER BY id").fetchall()],
        "sessions": [dict(row) for row in db.execute("SELECT * FROM sessions ORDER BY id").fetchall()],
        "shot_entries": [dict(row) for row in db.execute("SELECT * FROM shot_entries ORDER BY session_id, shot_number").fetchall()],
        "dynamic_hits": [dict(row) for row in db.execute("SELECT * FROM dynamic_hits ORDER BY session_id, id").fetchall()],
    }
    return Response(
        jsonify(payload).get_data(as_text=True),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=rangelog-export.json"},
    )


@bp.route("/api/export/csv")
def api_export_csv():
    rows = get_db().execute(
        """
        SELECT
            s.id AS session_id, s.date, e.name AS exercise_name, e.type AS exercise_type,
            e.weapon_type, e.distance, e.target_id, COALESCE(e.scoring_method_id, e.scoring_method) AS scoring_method,
            s.total_score, s.max_score, s.percentage, s.raw_time, s.penalty_time,
            s.final_time, s.hit_factor, s.notes
        FROM sessions s JOIN exercises e ON e.id = s.exercise_id
        ORDER BY s.date, s.id
        """
    ).fetchall()
    output = io.StringIO()
    fieldnames = [
        "session_id", "date", "exercise_name", "exercise_type", "weapon_type", "distance",
        "target_id", "scoring_method", "total_score", "max_score", "percentage", "raw_time",
        "penalty_time", "final_time", "hit_factor", "notes",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=rangelog-sessions.csv"},
    )


@bp.route("/api/reset", methods=["POST"])
def api_reset():
    reset_all_data()
    return redirect(url_for("main.settings"))


@bp.route("/api/seed-defaults", methods=["POST"])
def api_seed_defaults():
    seed_missing_default_exercises()
    return redirect(url_for("main.settings"))


@bp.route("/api/exercises", methods=["GET", "POST"])
def api_exercises():
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        exercise_id = create_exercise(exercise_from_form(payload))
        return jsonify(get_exercise(exercise_id)), 201
    return jsonify(all_exercises())


@bp.route("/api/exercises/<int:exercise_id>", methods=["GET", "PUT", "DELETE"])
def api_exercise(exercise_id):
    exercise = get_exercise(exercise_id)
    if not exercise:
        abort(404)
    if request.method == "GET":
        exercise["sessions"] = sessions_for_exercise(exercise_id)
        return jsonify(exercise)
    if request.method == "DELETE":
        delete_exercise(exercise_id)
        return "", 204
    payload = request.get_json(silent=True) or request.form
    update_exercise(exercise_id, exercise_from_form(payload))
    return jsonify(get_exercise(exercise_id))


@bp.route("/api/exercises/<int:exercise_id>/sessions", methods=["POST"])
def api_create_session(exercise_id):
    exercise = get_exercise(exercise_id)
    if not exercise:
        abort(404)
    payload = request.get_json(silent=True) or request.form
    session_id = create_session_for_exercise(exercise, payload)
    return jsonify(get_session(session_id)), 201
