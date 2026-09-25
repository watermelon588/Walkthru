"""Plus features on persona runs and reports: custom test users, several test users per report (P4.2) and report
branding for the printed PDF (P4.3). Plain validation code; the routes live in app/main.py."""

import base64
import re

from fastapi import HTTPException

from app import plans
from app.agent.persona import PERSONAS

MAX_TEST_USERS = 10
MAX_GROUP = 6  # runs sharing one group id: the 4 built-in test users plus a couple of custom ones
CUSTOM_PREFIX = "custom:"
LOGO_BYTES = 200_000
# Raster formats only: an SVG logo can carry script, and the PDF never needs it.
LOGO_TYPES = {"image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff", "image/webp": b"RIFF"}
BUILT_IN_NAMES = set(PERSONAS) | {"first-time visitor", "phone user", "small-business buyer", "skeptical developer"}


def require(user_id: str, feature: str) -> None:
    """402 with a plain message unless the caller is on Plus (the server decides the plan, never the client)."""
    if plans.current(user_id)["plan"].name != "plus":
        raise HTTPException(402, f"{feature} are part of the Plus plan.")


def _text(value: str) -> str:
    return " ".join(value.split())


def clean_test_user(name: str, description: str) -> tuple[str, str]:
    """A custom test user's name and description, single-spaced. Raises 422 with a plain message."""
    name, description = _text(name), _text(description)
    if not 1 <= len(name) <= 40:
        raise HTTPException(422, "Give the test user a name of up to 40 characters.")
    if name.lower() in BUILT_IN_NAMES:
        raise HTTPException(422, "That name belongs to a built-in test user. Pick another.")
    if not 10 <= len(description) <= 300:
        raise HTTPException(422, "Describe the test user in 10 to 300 characters: who they are and what they care about.")
    return name, description


def persona_prompt(name: str, description: str) -> str:
    """How a custom test user reads in the persona prompt, where built-in ones read as a short description."""
    return f"{name}, {description}"


def _luminance(hex_color: str) -> float:
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_on_white(hex_color: str) -> float:
    return 1.05 / (_luminance(hex_color) + 0.05)


def clean_brand(name: str, color: str, footer: str, logo: str | None) -> dict:
    """Validated branding. The color must stay readable as small text on white paper (3:1, WCAG for large text)."""
    name, footer, color = _text(name), _text(footer), color.strip().lower()
    if not 1 <= len(name) <= 80:
        raise HTTPException(422, "Add your company or agency name (up to 80 characters).")
    if len(footer) > 120:
        raise HTTPException(422, "Keep the footer line to 120 characters.")
    if not re.fullmatch(r"#[0-9a-f]{6}", color):
        raise HTTPException(422, "Pick the brand color as a hex value like #1b1b1f.")
    if contrast_on_white(color) < 3:
        raise HTTPException(422, "That color is too light to read on white paper. Pick a darker shade.")
    return {"name": name, "color": color, "footer": footer, "logo": check_logo(logo) if logo else None}


def check_logo(data_url: str) -> str:
    """A PNG, JPEG or WebP data URL whose bytes really are that format, at most 200 kB."""
    match = re.fullmatch(r"data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=]+)", data_url.strip())
    if not match:
        raise HTTPException(422, "Upload the logo as a PNG, JPEG or WebP image.")
    try:
        raw = base64.b64decode(match.group(2), validate=True)
    except ValueError as e:
        raise HTTPException(422, "The logo file could not be read. Try exporting it again.") from e
    if len(raw) > LOGO_BYTES:
        raise HTTPException(422, "The logo is larger than 200 kB. Export a smaller version (about 600 pixels wide is plenty).")
    kind = match.group(1)
    if not raw.startswith(LOGO_TYPES[kind]) or (kind == "image/webp" and raw[8:12] != b"WEBP"):
        raise HTTPException(422, "The logo file is not the image type it claims to be.")
    return f"data:{kind};base64,{base64.b64encode(raw).decode()}"
