"""Server-side validation for sign-up, log-in, road search and hazard reports."""
import re

from api_client import REGIONS, SURFACES, SMOOTHNESS

EMAIL = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")

SEVERITIES = ["low", "medium", "high"]


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
    if confirm == "":
        errors["confirm"] = "Please confirm your password."
    elif confirm != password:
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
    if surface != "" and surface not in SURFACES:
        errors["surface"] = "Invalid surface type."

    smoothness = args.get("smoothness", "").strip().lower()
    if smoothness != "" and smoothness not in SMOOTHNESS:
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


def validate_report_location(lat, lon, region, severity):
    errors = {}
    region = (region or "").strip().lower()
    severity = (severity or "").strip().lower()

    if region not in REGIONS:
        errors["region"] = "Please choose a valid region."
    if severity not in SEVERITIES:
        errors["severity"] = "Severity must be low, medium or high."

    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        errors["location"] = "Latitude and longitude must be numbers."
    else:
        if region in REGIONS:
            south, west, north, east = REGIONS[region]["bbox"]
            if not (south <= lat <= north and west <= lon <= east):
                errors["location"] = "Location is outside the selected region."

    params = {"latitude": lat, "longitude": lon,
              "region": region, "severity": severity}
    return errors, params