"""Lenient output schemas: models sometimes omit or misname fields, so everything has a default."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Lenient(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ExtractedItem(_Lenient):
    id: str = ""
    kind: Literal["task", "decision", "question"] = "task"
    text: str
    owner: Optional[str] = None
    due: Optional[str] = None
    evidence: Optional[str] = None

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, v):
        v = str(v or "task").lower().strip()
        if v.startswith("decision"):
            return "decision"
        if v.startswith("question") or v == "open_question":
            return "question"
        return "task"


class Extraction(_Lenient):
    participants: list[str] = Field(default_factory=list)
    items: list[ExtractedItem] = Field(default_factory=list)


class Task(_Lenient):
    id: str = ""
    title: str
    owner: Optional[str] = None
    due: Optional[str] = None
    priority: Literal["high", "medium", "low"] = "medium"
    depends_on: list[str] = Field(default_factory=list)
    rationale: Optional[str] = None

    @field_validator("priority", mode="before")
    @classmethod
    def _priority(cls, v):
        v = str(v or "medium").lower().strip()
        return v if v in {"high", "medium", "low"} else "medium"


class Conflict(_Lenient):
    description: str
    resolution: Optional[str] = None


class Resolution(_Lenient):
    summary: str = ""
    tasks: list[Task] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)


class Email(_Lenient):
    to: str
    subject: str
    body: str


class Emails(_Lenient):
    emails: list[Email] = Field(default_factory=list)
