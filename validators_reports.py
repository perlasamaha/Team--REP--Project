"""Validation for hazard report text fields."""

MAX_DESCRIPTION = 1000


def validate_report_description(form):
    errors = {}
    description = form.get("description", "").strip()
    if description == "":
        errors["description"] = "Description is required."
    elif len(description) > MAX_DESCRIPTION:
        errors["description"] = f"Description must be at most {MAX_DESCRIPTION} characters."
    return errors, description