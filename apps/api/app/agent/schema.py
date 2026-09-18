"""Wire contracts between the extension and the persona agent."""

from typing import Literal

from pydantic import BaseModel, Field

Action = Literal["click", "type", "scroll", "back", "done", "give_up"]


class Element(BaseModel):
    id: int
    tag: str  # a, button, input, select, textarea
    text: str = ""  # visible text or aria-label, already redacted client side
    type: str | None = None  # input type


class Observation(BaseModel):
    """One page snapshot from the content script. PII is masked before upload."""

    url: str
    title: str = ""
    elements: list[Element] = Field(default_factory=list)
    text: str = ""  # visible text, trimmed client side
    errors: list[str] = Field(default_factory=list)  # visible error messages
    note: str | None = None  # executor feedback: "element not found", "captcha", ...


class PersonaStep(BaseModel):
    """What the test user thinks and does next. Exactly one action per step."""

    thought: str = Field(description="Think aloud, in character, one or two sentences.")
    action: Action
    target_id: int | None = Field(default=None, description="Element id for click/type.")
    text: str | None = Field(default=None, description="Text to type, for type only.")
    confusion: int = Field(ge=0, le=3, description="0 clear, 1 hesitant, 2 confused, 3 stuck")
