"""SD-2.2: request bodies and browser snapshots are bounded before they reach code or model prompts."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agent.schema import Observation
from app.main import MAX_BODY, app

REAL = {"url": "https://a.example/", "title": "Home", "text": "x" * 6000, "errors": ["e" * 200] * 10, "notices": ["n" * 200] * 5,
        "elements": [{"id": i, "tag": "button", "text": "b" * 80} for i in range(120)]}


def test_what_the_extension_sends_fits():
    Observation.model_validate(REAL)  # its own caps: 120 elements, 80-character labels, 6,000 characters of text


@pytest.mark.parametrize("field,value", [
    ("text", "x" * 8001),
    ("elements", [{"id": i, "tag": "a", "text": ""} for i in range(151)]),
    ("elements", [{"id": 1, "tag": "a", "text": "t" * 301}]),
    ("errors", ["e"] * 21),
    ("notices", ["n" * 301]),
    ("note", "n" * 301),
])
def test_oversized_snapshot_fields_are_refused(field, value):
    with pytest.raises(ValidationError):
        Observation.model_validate(REAL | {field: value})


def test_a_long_title_is_trimmed_not_refused():
    assert len(Observation.model_validate(REAL | {"title": "t" * 900}).title) == 500


def test_large_or_chunked_bodies_are_refused_before_parsing(signed_in):
    c = TestClient(app)
    big = c.post("/me/test-users", content=b"{" + b" " * (MAX_BODY + 1) + b"}", headers={"Content-Type": "application/json"})
    assert big.status_code == 413
    chunked = c.post("/me/test-users", content=iter([b'{"name": "x",', b' "description": "y"}']), headers={"Content-Type": "application/json"})
    assert chunked.status_code == 411
    assert c.get("/health").status_code == 200
