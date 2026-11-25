"""
<YOUR PROJECT NAME> -- a Flask web app (team project starter).

Content comes from an external API (see api_client.py). The only data stored
is user accounts and their favorites (see models.py). Authentication is
email + password with Flask sessions.

Run locally:   flask run --debug    ->   http://127.0.0.1:5000
"""
import os
import uuid
from functools import wraps

import requests
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, abort, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash

import api_client
from models import db, User, Favorite, Road, Watchlist, HazardReport, Note, ReportImage
from validators import (validate_signup, validate_login,
                        validate_road_search, validate_report_location)
from validators_reports import (validate_report_description, validate_note_content,
                                validate_image_file, MAX_IMAGES_PER_REPORT)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")


def database_uri():
    """PostgreSQL on Render (DATABASE_URL), else a local SQLite file."""
    url = os.environ.get("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url
    return "sqlite:///" + os.path.abspath("app.db")


app.config["SQLALCHEMY_DATABASE_URI"] = database_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024  # whole request, in bytes
db.init_app(app)
with app.app_context():
    db.create_all()


@app.context_processor
def inject_globals():
    user = None
    favorite_ids = set()
    watchlist_by_osm = {}
    if "user_id" in session:
        user = db.session.get(User, session["user_id"])
        if user:
            favorite_ids = {f.item_id for f in user.favorites}
            watchlist_by_osm = {w.road.osm_id: w.id for w in user.watchlist
                                if w.road.element_type == "way"}
    return {"current_user": user, "favorite_ids": favorite_ids,
            "watchlist_by_osm": watchlist_by_osm}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ---------- content (from your API) --------------------------------
@app.route("/")
def home():
    regions = {key: r["label"] for key, r in api_client.REGIONS.items()}
    return render_template("home.html", regions=regions,
                           surfaces=api_client.SURFACES,
                           smoothness=api_client.SMOOTHNESS)


@app.route("/roads")
def roads():
    """JSON for the map and list. Example:
    /roads?region=naccache&surface=asphalt&include_service=1"""
    errors, params = validate_road_search(request.args)
    if errors:
        return jsonify({"errors": errors}), 400
    try:
        all_roads, saved_at, stale = api_client.get_roads(
            params["region"], params["include_service"])
    except api_client.OverpassError as e:
        return jsonify({"error": str(e)}), 502
    found = api_client.filter_roads(all_roads, params["surface"],
                                    params["smoothness"], params["name"])
    return jsonify({"count": len(found), "roads": found,
                    "stale": stale, "saved_at": saved_at})


@app.route("/road/<osm_type>/<int:osm_id>")
def road_detail(osm_type, osm_id):
    if osm_type != "way":
        abort(404)
    try:
        road = api_client.get_road(osm_id)
    except api_client.OverpassError as e:
        flash(str(e))
        return redirect(url_for("home"))
    return render_template("detail.html", road=road)


# ===================================================================
# AUTHENTICATION  --  YOU BUILD THIS (sign-up, log-in, log-out, sessions)
# ===================================================================
# This is YOUR work. The routes below are stubs. Implement them using what
# you learned in the "Sessions & Login" slides. Tools already imported for
# you at the top: generate_password_hash, check_password_hash, session,
# and the validators validate_signup / validate_login.
#
# What each route should do:
#   signup (POST): validate the form; reject an email that already exists;
#                  hash the password; create the User; store session["user_id"];
#                  redirect home.
#   login  (POST): validate; find the user by email; check_password_hash;
#                  on success store session["user_id"]; else show an error.
#   logout        : session.clear(); redirect home.
# A worked version of favorites below shows how session["user_id"] is used.

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        errors, email = validate_signup(request.form)
        password = request.form.get("password", "")
        data = {"email": email}

        if not errors and User.query.filter_by(email=email).first():
            errors["email"] = "An account with this email already exists."

        if errors:
            return render_template("signup.html", errors=errors, data=data), 400

        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()

        session.clear()
        session["user_id"] = user.id
        flash("Welcome! Your account was created.")
        return redirect(url_for("home"))
    return render_template("signup.html", errors={}, data={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        errors, email = validate_login(request.form)
        password = request.form.get("password", "")
        data = {"email": email}

        if errors:
            return render_template("login.html", errors=errors, data=data), 400

        user = User.query.filter_by(email=email).first()
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.")
            return render_template("login.html", errors={}, data=data), 401

        session.clear()
        session["user_id"] = user.id
        flash("Logged in successfully.")
        return redirect(url_for("home"))
    return render_template("login.html", errors={}, data={})


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home"))


# ---------- favorites (login required) -----------------------------
@app.route("/favorites")
@login_required
def favorites():
    items = Favorite.query.filter_by(user_id=session["user_id"]).all()
    return render_template("favorites.html", favorites=items)


@app.route("/favorites/add", methods=["POST"])
@login_required
def favorites_add():
    item_id = request.form.get("item_id", "").strip()
    if item_id:
        exists = Favorite.query.filter_by(
            user_id=session["user_id"], item_id=item_id).first()
        if exists:
            flash("Already in your favorites.")
        else:
            db.session.add(Favorite(
                user_id=session["user_id"], item_id=item_id,
                item_title=request.form.get("item_title", ""),
                item_image=request.form.get("item_image", "")))
            db.session.commit()
            flash("Saved to favorites.")
    return redirect(request.form.get("next") or url_for("favorites"))


@app.route("/favorites/remove", methods=["POST"])
@login_required
def favorites_remove():
    item_id = request.form.get("item_id", "").strip()
    fav = Favorite.query.filter_by(
        user_id=session["user_id"], item_id=item_id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        flash("Removed from favorites.")
    return redirect(request.form.get("next") or url_for("favorites"))

def safe_next(default_endpoint):
    """Redirect target from a form, only if it is a path on this site."""
    target = request.form.get("next", "")
    if target.startswith("/") and not target.startswith("//"):
        return target
    return url_for(default_endpoint)


@app.route("/watchlist")
@login_required
def watchlist():
    entries = (Watchlist.query.filter_by(user_id=session["user_id"])
               .order_by(Watchlist.created_at.desc()).all())
    return render_template("watchlist.html", entries=entries)


@app.route("/watchlist/add", methods=["POST"])
@login_required
def watchlist_add():
    try:
        osm_id = int(request.form.get("osm_id", "").strip())
    except ValueError:
        osm_id = 0
    if not 0 < osm_id < 10**13:
        flash("Invalid road.")
        return redirect(safe_next("watchlist"))

    road = Road.query.filter_by(osm_id=osm_id, element_type="way").first()
    if road is None:
        try:
            data = api_client.get_road(osm_id)
        except (api_client.OverpassError, KeyError, IndexError):
            flash("Could not load this road. Please try again later.")
            return redirect(safe_next("watchlist"))
        road = Road(osm_id=osm_id, element_type="way",
                    name=data.get("name") or data.get("name_ar"))
        db.session.add(road)
        db.session.flush()  # gives road.id without committing yet

    exists = Watchlist.query.filter_by(
        user_id=session["user_id"], road_id=road.id).first()
    if exists:
        flash("Already in your watchlist.")
    else:
        db.session.add(Watchlist(user_id=session["user_id"], road_id=road.id))
        db.session.commit()
        flash("Saved to your watchlist.")
    return redirect(safe_next("watchlist"))


@app.route("/watchlist/<int:entry_id>/delete", methods=["POST"])
@login_required
def watchlist_delete(entry_id):
    entry = db.session.get(Watchlist, entry_id)
    if entry is None:
        abort(404)
    if entry.user_id != session["user_id"]:
        abort(403)
    db.session.delete(entry)
    db.session.commit()
    flash("Removed from your watchlist.")
    return redirect(safe_next("watchlist"))   

def validate_report_form(form):
    """Run both report validators. Returns (errors, params, description, data)."""
    loc_errors, params = validate_report_location(
        form.get("latitude"), form.get("longitude"),
        form.get("region"), form.get("severity"))
    desc_errors, description = validate_report_description(form)
    errors = {**loc_errors, **desc_errors}
    data = {k: form.get(k, "") for k in
            ("latitude", "longitude", "region", "severity", "description")}
    return errors, params, description, data


def get_owned_report(report_id):
    """Load a report, or stop with 404 (missing) / 403 (not the owner)."""
    report = db.session.get(HazardReport, report_id)
    if report is None:
        abort(404)
    if report.user_id != session["user_id"]:
        abort(403)
    return report 

def get_owned_note(note_id):
    """Load a note, or stop with 404 (missing) / 403 (not the author)."""
    note = db.session.get(Note, note_id)
    if note is None:
        abort(404)
    if note.user_id != session["user_id"]:
        abort(403)
    return note    

IMAGEKIT_UPLOAD_URL = "https://upload.imagekit.io/api/v1/files/upload"
IMAGEKIT_FILES_URL = "https://api.imagekit.io/v1/files/"


def upload_to_imagekit(file, ext):
    """Upload one validated photo. Returns (url, file_id). Raises RuntimeError."""
    key = os.environ.get("IMAGEKIT_PRIVATE_KEY", "")
    name = f"{uuid.uuid4().hex}.{ext}"
    try:
        r = requests.post(
            IMAGEKIT_UPLOAD_URL, auth=(key, ""), timeout=20,
            files={"file": (name, file.stream)},
            data={"fileName": name, "folder": "/tari2na/reports",
                  "useUniqueFileName": "true"})
        r.raise_for_status()
        data = r.json()
        return data["url"], data["fileId"]
    except (requests.RequestException, ValueError, KeyError) as e:
        raise RuntimeError("ImageKit upload failed") from e


def delete_remote_image(file_id):
    """Best effort: the database stays the source of truth if this fails."""
    key = os.environ.get("IMAGEKIT_PRIVATE_KEY", "")
    try:
        requests.delete(IMAGEKIT_FILES_URL + file_id, auth=(key, ""), timeout=10)
    except requests.RequestException:
        app.logger.exception("Could not delete %s from ImageKit", file_id)

@app.route("/api/reports")
def api_reports():
    """JSON feed of a region's reports, for the map."""
    region = request.args.get("region", "").strip()
    if region not in api_client.REGIONS:
        return jsonify({"errors": {"region": "Please choose a valid region."}}), 400
    rows = (HazardReport.query.filter_by(region=region)
            .order_by(HazardReport.created_at.desc()).limit(500).all())
    return jsonify({"count": len(rows), "reports": [
        {"id": r.id, "latitude": r.latitude, "longitude": r.longitude,
         "severity": r.severity, "status": r.status, "type": r.type,
         "description": r.description,
         "created_at": r.created_at.isoformat()} for r in rows]})



@app.route("/reports/new", methods=["GET", "POST"])
@login_required
def report_new():
    regions = {key: r["label"] for key, r in api_client.REGIONS.items()}
    if request.method == "POST":
        errors, params, description, data = validate_report_form(request.form)
        if errors:
            return render_template("report_form.html", errors=errors,
                                   data=data, regions=regions), 400
        report = HazardReport(user_id=session["user_id"],
                              description=description, **params)
        db.session.add(report)
        db.session.commit()
        flash("Report posted. It is marked as unverified.")
        return redirect(url_for("report_detail", report_id=report.id))
    return render_template("report_form.html", errors={}, data={}, regions=regions)

@app.route("/reports")
def reports():
    regions = {key: r["label"] for key, r in api_client.REGIONS.items()}
    region = request.args.get("region", "").strip()
    if region and region not in regions:
        flash("Unknown region.")
        region = ""
    query = HazardReport.query
    if region:
        query = query.filter_by(region=region)
    rows = query.order_by(HazardReport.created_at.desc()).limit(100).all()
    return render_template("reports.html", reports=rows,
                           regions=regions, selected=region)


@app.route("/reports/<int:report_id>")
def report_detail(report_id):
    report = db.session.get(HazardReport, report_id)
    if report is None:
        abort(404)
    regions = {key: r["label"] for key, r in api_client.REGIONS.items()}
    is_owner = "user_id" in session and report.user_id == session["user_id"]
    notes = (Note.query.filter_by(report_id=report.id)
             .order_by(Note.created_at.asc()).all())
    return render_template("report_detail.html", report=report,
                           regions=regions, is_owner=is_owner, notes=notes)

@app.route("/reports/<int:report_id>/edit", methods=["GET", "POST"])
@login_required
def report_edit(report_id):
    report = get_owned_report(report_id)
    regions = {key: r["label"] for key, r in api_client.REGIONS.items()}
    action = url_for("report_edit", report_id=report.id)
    if request.method == "POST":
        errors, params, description, data = validate_report_form(request.form)
        if errors:
            return render_template("report_form.html", errors=errors, data=data,
                                   regions=regions, form_action=action,
                                   title="Edit report",
                                   submit_label="Save changes"), 400
        report.latitude = params["latitude"]
        report.longitude = params["longitude"]
        report.region = params["region"]
        report.severity = params["severity"]
        report.description = description
        db.session.commit()
        flash("Report updated.")
        return redirect(url_for("report_detail", report_id=report.id))
    data = {"latitude": str(report.latitude), "longitude": str(report.longitude),
            "region": report.region, "severity": report.severity,
            "description": report.description}
    return render_template("report_form.html", errors={}, data=data,
                           regions=regions, form_action=action,
                           title="Edit report", submit_label="Save changes")


@app.route("/reports/<int:report_id>/delete", methods=["POST"])
@login_required
def report_delete(report_id):
    report = get_owned_report(report_id)
    file_ids = [img.file_id for img in report.images]
    db.session.delete(report)
    db.session.commit()
    for file_id in file_ids:
        delete_remote_image(file_id)
    flash("Report deleted.")
    return redirect(url_for("reports"))

@app.route("/reports/<int:report_id>/notes", methods=["POST"])
@login_required
def note_add(report_id):
    report = db.session.get(HazardReport, report_id)
    if report is None:
        abort(404)
    errors, content = validate_note_content(request.form)
    if errors:
        flash(errors["content"])
    else:
        db.session.add(Note(report_id=report.id, user_id=session["user_id"],
                            content=content))
        db.session.commit()
        flash("Note added.")
    return redirect(url_for("report_detail", report_id=report.id))


@app.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def note_edit(note_id):
    note = get_owned_note(note_id)
    if request.method == "POST":
        errors, content = validate_note_content(request.form)
        if errors:
            data = {"content": request.form.get("content", "")}
            return render_template("note_form.html", note=note,
                                   errors=errors, data=data), 400
        note.content = content
        db.session.commit()
        flash("Note updated.")
        return redirect(url_for("report_detail", report_id=note.report_id))
    return render_template("note_form.html", note=note, errors={},
                           data={"content": note.content})


@app.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def note_delete(note_id):
    note = get_owned_note(note_id)
    report_id = note.report_id
    db.session.delete(note)
    db.session.commit()
    flash("Note deleted.")
    return redirect(url_for("report_detail", report_id=report_id))   

@app.errorhandler(413)
def too_large(e):
    flash("That upload is too large.")
    return redirect(url_for("reports"))  

@app.route("/reports/<int:report_id>/images", methods=["POST"])
@login_required
def report_image_add(report_id):
    report = get_owned_report(report_id)
    back = redirect(url_for("report_detail", report_id=report.id))
    if not os.environ.get("IMAGEKIT_PRIVATE_KEY"):
        flash("Photo uploads are not configured on this server.")
        return back
    if len(report.images) >= MAX_IMAGES_PER_REPORT:
        flash(f"A report can have at most {MAX_IMAGES_PER_REPORT} photos.")
        return back
    file = request.files.get("photo")
    error, ext = validate_image_file(file)
    if error:
        flash(error)
        return back
    try:
        url, file_id = upload_to_imagekit(file, ext)
    except RuntimeError:
        app.logger.exception("ImageKit upload failed")
        flash("The photo could not be uploaded. Please try again later.")
        return back
    db.session.add(ReportImage(report_id=report.id, image_url=url,
                               file_id=file_id))
    db.session.commit()
    flash("Photo added.")
    return back


@app.route("/reports/<int:report_id>/images/<int:image_id>/delete", methods=["POST"])
@login_required
def report_image_delete(report_id, image_id):
    report = get_owned_report(report_id)
    image = db.session.get(ReportImage, image_id)
    if image is None or image.report_id != report.id:
        abort(404)
    file_id = image.file_id
    db.session.delete(image)
    db.session.commit()
    delete_remote_image(file_id)
    flash("Photo removed.")
    return redirect(url_for("report_detail", report_id=report.id))       

if __name__ == "__main__":
    app.run(debug=True)