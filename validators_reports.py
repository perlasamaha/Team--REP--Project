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

MAX_NOTE = 500


def validate_note_content(form):
    errors = {}
    content = form.get("content", "").strip()
    if content == "":
        errors["content"] = "Note text is required."
    elif len(content) > MAX_NOTE:
        errors["content"] = f"Note must be at most {MAX_NOTE} characters."
    return errors, content