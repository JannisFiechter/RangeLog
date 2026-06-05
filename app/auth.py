from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import UserMixin, current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from .database import get_db
from .models import seed_missing_default_exercises


auth_bp = Blueprint("auth", __name__)


class User(UserMixin):
    def __init__(self, row):
        self.id = str(row["id"])
        self.username = row["username"]
        self.email = row["email"]
        self.password_hash = row["password_hash"]
        self.created_at = row["created_at"]


def get_user(user_id):
    if not user_id:
        return None
    row = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return User(row) if row else None


def find_user(login):
    return get_db().execute(
        "SELECT * FROM users WHERE username = ? OR email = ?", (login, login)
    ).fetchone()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip() or None
        password = request.form.get("password") or ""
        if not username:
            error = "Bitte Username angeben."
        elif not password:
            error = "Bitte Passwort angeben."
        elif get_db().execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            error = "Dieser Username ist bereits vergeben."
        elif email and get_db().execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            error = "Diese E-Mail ist bereits vergeben."
        else:
            cursor = get_db().execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, generate_password_hash(password)),
            )
            get_db().commit()
            login_user(get_user(cursor.lastrowid))
            seed_missing_default_exercises()
            return redirect(url_for("main.index"))
    return render_template("register.html", error=error, active="auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    error = None
    if request.method == "POST":
        login_name = (request.form.get("login") or "").strip()
        password = request.form.get("password") or ""
        row = find_user(login_name)
        if not row or not check_password_hash(row["password_hash"], password):
            error = "Login oder Passwort ist falsch."
        else:
            login_user(User(row))
            seed_missing_default_exercises()
            next_url = request.args.get("next")
            return redirect(next_url or url_for("main.index"))
    return render_template("login.html", error=error, active="auth")


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/account/email", methods=["POST"])
def change_email():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    email = (request.form.get("email") or "").strip() or None
    if email:
        existing = get_db().execute(
            "SELECT id FROM users WHERE email = ? AND id != ?", (email, int(current_user.id))
        ).fetchone()
        if existing:
            flash("Diese E-Mail ist bereits vergeben.", "error")
            return redirect(url_for("main.settings"))
    get_db().execute("UPDATE users SET email = ? WHERE id = ?", (email, int(current_user.id)))
    get_db().commit()
    flash("E-Mail wurde gespeichert.", "success")
    return redirect(url_for("main.settings"))


@auth_bp.route("/account/password", methods=["POST"])
def change_password():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    new_password_confirm = request.form.get("new_password_confirm") or ""
    if not check_password_hash(current_user.password_hash, current_password):
        flash("Aktuelles Passwort ist falsch.", "error")
        return redirect(url_for("main.settings"))
    if not new_password:
        flash("Bitte neues Passwort angeben.", "error")
        return redirect(url_for("main.settings"))
    if new_password != new_password_confirm:
        flash("Die neuen Passwörter stimmen nicht überein.", "error")
        return redirect(url_for("main.settings"))
    get_db().execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), int(current_user.id)),
    )
    get_db().commit()
    flash("Passwort wurde geändert.", "success")
    return redirect(url_for("main.settings"))


@auth_bp.route("/account/delete", methods=["POST"])
def delete_account():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    user_id = int(current_user.id)
    db = get_db()
    db.execute(
        "DELETE FROM dynamic_hits WHERE session_id IN (SELECT id FROM sessions WHERE user_id = ?)",
        (user_id,),
    )
    db.execute(
        "DELETE FROM shot_entries WHERE session_id IN (SELECT id FROM sessions WHERE user_id = ?)",
        (user_id,),
    )
    db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM exercises WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM weapons WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    logout_user()
    return redirect(url_for("auth.login"))
