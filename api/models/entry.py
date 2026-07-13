from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, Field, StringConstraints

# ---------------------------------------------------------------
# Task 3 — shared constrained type for journal text fields.
#
# Step 1: strip_whitespace=True  -> trims leading/trailing spaces first
# Step 2: min_length=1           -> after stripping, "" and "   " fail
# Step 3: max_length=256         -> rejects oversize input
#
# Order matters: Pydantic strips BEFORE checking min_length, so a
# whitespace-only string collapses to "" and is rejected.
# ---------------------------------------------------------------
JournalText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=256),
]


class AnalysisResponse(BaseModel):
    """Response model for journal entry analysis."""

    entry_id: str = Field(description="ID of the analyzed entry")
    sentiment: str = Field(
        description="Sentiment: positive, negative, or neutral")
    summary: str = Field(description="2 sentence summary of the entry")
    topics: list[str] = Field(
        description="2-4 key topics mentioned in the entry")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the analysis was created",
    )


class EntryCreate(BaseModel):
    """Model for creating a new journal entry (user input)."""

    # ---------------------------------------------------------------
    # ORIGINAL STARTER TODO (kept for reference — Task 3, completed)
    #
    #   TODO (Task 3): Add validation so that work, struggle, intention:
    #     - reject empty strings and whitespace-only input
    #     - strip surrounding whitespace
    #     - have a max length of 256 characters
    #
    #   Hint: wrap the field type in Annotated[str, StringConstraints(...)].
    #
    # Done: each field now uses JournalText (defined above), which carries
    # all three rules. max_length was removed from Field() because the
    # constraint now lives in the type.
    # ---------------------------------------------------------------
    work: JournalText = Field(
        description="What did you work on today?",
        json_schema_extra={
            "example": "Studied FastAPI and built my first API endpoints"},
    )
    struggle: JournalText = Field(
        description="What's one thing you struggled with today?",
        json_schema_extra={
            "example": "Understanding async/await syntax and when to use it"},
    )
    intention: JournalText = Field(
        description="What will you study/work on tomorrow?",
        json_schema_extra={
            "example": "Practice PostgreSQL queries and database design"},
    )


# ---------------------------------------------------------------
# ORIGINAL STARTER TODO (kept for reference — Task 3, completed)
#
#   TODO (Task 3): Define an EntryUpdate model for PATCH /entries/{entry_id}.
#
#   Requirements:
#     - All three fields (work, struggle, intention) must be optional.
#     - Each field, when provided, must follow the same validation rules
#       as EntryCreate (non-empty, whitespace-stripped, max 256 chars).
#
#   Once defined, import EntryUpdate in api/routers/journal_router.py
#   and use it as the type of the PATCH endpoint's request body.
# ---------------------------------------------------------------
class EntryUpdate(BaseModel):
    """Model for PATCH /entries/{entry_id} — partial update.

    All fields optional (default None) so a caller can update just one.
    When a value IS given, JournalText applies the same rules as
    EntryCreate: stripped, non-empty, max 256 chars.
    """

    # Step 1: JournalText | None  -> optional; validation only runs on a value
    # Step 2: default=None        -> field can be omitted from the request body
    work: JournalText | None = Field(
        default=None, description="Updated work text.")
    struggle: JournalText | None = Field(
        default=None, description="Updated struggle text.")
    intention: JournalText | None = Field(
        default=None, description="Updated intention text.")


class Entry(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique identifier for the entry (UUID)."
    )
    work: str = Field(..., max_length=256,
                      description="What did you work on today?")
    struggle: str = Field(
        ..., max_length=256, description="What's one thing you struggled with today?"
    )
    intention: str = Field(..., max_length=256,
                           description="What will you study/work on tomorrow?")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the entry was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the entry was last updated.",
    )
