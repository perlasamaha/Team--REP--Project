"""Server-side validation for sign-up, log-in and road search."""
import re

from api_client import REGIONS

EMAIL = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")

ALLOWED_SURFACES = {"asphalt", "concrete", "paved", "unpaved", "gravel", "dirt",
                    "paving_stones", "compacted", "sett", "ground", "unknown"}
ALLOWED_SMOOTHNESS = {"excellent", "good", "intermediate", "bad", "very_bad",
                      "horrible", "very_horrible", "impassable", "unknown"}


def validate_signup(form):
    errors = {}
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    confirm = form.get("confirm", "")
    if email == "":
        errors["email"] = "Email is required."
    elif not EMAIL.match(email):
        errors["email"] = "Enter a valid email address."
    if password == "":
        errors["password"] = "Password is required."
    elif len(password) < 6:
        errors["password"] = "Password must be at least 6 characters."
    if confirm != "" and confirm != password:
        errors["confirm"] = "Passwords do not match."
    return errors, email


def validate_login(form):
    errors = {}
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    if email == "":
        errors["email"] = "Email is required."
    if password == "":
        errors["password"] = "Password is required."
    return errors, email


def validate_road_search(args):
    errors = {}

    region = args.get("region", "").strip()
    if region not in REGIONS:
        errors["region"] = "Please choose a valid region."

    surface = args.get("surface", "").strip().lower()
    if surface != "" and surface not in ALLOWED_SURFACES:
        errors["surface"] = "Invalid surface type."

    smoothness = args.get("smoothness", "").strip().lower()
    if smoothness != "" and smoothness not in ALLOWED_SMOOTHNESS:
        errors["smoothness"] = "Invalid smoothness value."

    name = args.get("name", "").strip()
    if len(name) > 60:
        errors["name"] = "Search text is too long."

    include_service = args.get("include_service") == "1"

    params = {"region": region,
              "surface": surface or None,
              "smoothness": smoothness or None,
              "name": name or None,
              "include_service": include_service}
    return errors, params