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

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGES_PER_REPORT = 3


def detect_image_type(header):
    """Guess the type from the first bytes. Returns None if not allowed."""
    if header.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def validate_image_file(file):
    """Return (error, extension). error is None when the file is acceptable."""
    if file is None or file.filename == "":
        return "Please choose a photo.", None
    header = file.stream.read(12)
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size == 0:
        return "The file is empty.", None
    if size > MAX_IMAGE_BYTES:
        return "The photo is too large (maximum 5 MB).", None
    ext = detect_image_type(header)
    if ext is None:
        return "Only JPEG, PNG or WebP photos are allowed.", None
    return None, ext