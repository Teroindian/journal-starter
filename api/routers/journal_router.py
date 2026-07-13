from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException

from api.config import Settings, get_settings
from api.models.entry import AnalysisResponse, Entry, EntryCreate, EntryUpdate
from api.repositories.postgres_repository import PostgresDB
from api.services.entry_service import EntryService
from api.services.llm_service import analyze_journal_entry

router = APIRouter()


async def get_entry_service(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[EntryService]:
    async with PostgresDB(settings.database_url) as db:
        yield EntryService(db)


@router.post("/entries", status_code=201)
async def create_entry(
    entry_data: EntryCreate, entry_service: EntryService = Depends(get_entry_service)
):
    """Create a new journal entry."""
    # Create the full entry with auto-generated fields
    entry = Entry(
        work=entry_data.work, struggle=entry_data.struggle, intention=entry_data.intention
    )

    # Store the entry in the database
    created_entry = await entry_service.create_entry(entry.model_dump())

    # Return success response (FastAPI handles datetime serialization automatically)
    return {"detail": "Entry created successfully", "entry": created_entry}


# Implements GET /entries endpoint to list all journal entries
# Example response: [{"id": "123", "work": "...", "struggle": "...", "intention": "..."}]
@router.get("/entries")
async def get_all_entries(entry_service: EntryService = Depends(get_entry_service)):
    """Get all journal entries."""
    result = await entry_service.get_all_entries()
    return {"entries": result, "count": len(result)}


@router.get("/entries/{entry_id}")
async def get_entry(entry_id: str, entry_service: EntryService = Depends(get_entry_service)):
    """Get a single journal entry by ID.

    Returns the entry as a flat JSON object, or 404 if no entry has that id.
    """
    # ---------------------------------------------------------------
    # ORIGINAL STARTER TODO (kept for reference — Task 2a, completed)
    #
    #   TODO: Implement this endpoint to return a single journal entry by ID
    #
    #   Steps to implement:
    #   1. Use entry_service.get_entry(entry_id) to fetch the entry
    #   2. If entry is None, raise HTTPException with status_code=404
    #   3. Return the entry directly (not wrapped in a dict)
    #
    #   Example response (status 200):
    #   {
    #       "id": "uuid-string",
    #       "work": "...",
    #       "struggle": "...",
    #       "intention": "...",
    #       "created_at": "...",
    #       "updated_at": "..."
    #   }
    #
    #   Hint: Check the update_entry endpoint for similar patterns
    #
    #   Was: raise HTTPException(status_code=501, detail="Not implemented...")
    # ---------------------------------------------------------------

    # Step 1 — delegate to the service layer. Returns dict | None.
    entry = await entry_service.get_entry(entry_id)

    # Step 2 — the DB signals "no row" with None. HTTP signals it with 404.
    # This router is the only layer that knows how to speak HTTP.
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Step 3 — return bare, NOT wrapped. Tests assert entry["id"], not
    # result["entry"]["id"]. Wrapping is the most common way to fail here.
    return entry


@router.patch("/entries/{entry_id}")
async def update_entry(
    entry_id: str,
    entry_update: EntryUpdate,
    entry_service: EntryService = Depends(get_entry_service),
):
    """Update a journal entry. Body validated by EntryUpdate (Task 3)."""
    # ---------------------------------------------------------------
    # ORIGINAL STARTER TODO (kept for reference — Task 3, completed)
    #
    #   TODO (Task 3): Replace entry_update: dict with entry_update: EntryUpdate
    #   (import it from api.models.entry) so PATCH requests are validated the
    #   same way POST requests are. Without this, PATCH happily accepts
    #   empty strings and 300-character bodies — see TestUpdateEntry in
    #   tests/test_api.py.
    #
    #   Done: param is now EntryUpdate. FastAPI validates it before this
    #   function body runs, so bad input returns 422 automatically —
    #   no manual validation code needed here.
    # ---------------------------------------------------------------

    # Step 1 — convert the validated model back into a dict for the service.
    #   entry_update arrives as an EntryUpdate instance (FastAPI built it).
    #   model_dump() turns it back into a plain dict the service expects.
    #   exclude_unset=True: include ONLY the fields the caller actually sent,
    #   so omitted fields keep their existing values (true partial update).
    #   Without it, unsent fields become None and would wipe existing data.
    result = await entry_service.update_entry(
        entry_id, entry_update.model_dump(exclude_unset=True)
    )

    # Step 2 — existence check. The service returns a falsy value when no
    #   row matched that id → translate that into HTTP 404.
    if not result:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Step 3 — return the updated entry (the service hands back the new row).
    return result


# DELETE /entries/{entry_id} — remove a specific entry. Returns 404 if not found.
# Task 2b, completed.
@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, entry_service: EntryService = Depends(get_entry_service)):
    """Delete a single journal entry by ID."""
    # ---------------------------------------------------------------
    # ORIGINAL STARTER TODO (kept for reference — Task 2b, completed)
    #
    #   TODO: Implement this endpoint to delete a specific journal entry
    #
    #   Steps to implement:
    #   1. Use entry_service.get_entry(entry_id) to check if entry exists
    #   2. If entry is None, raise HTTPException with status_code=404
    #   3. Use entry_service.delete_entry(entry_id) to delete the entry
    #   4. Return a success response (status 200)
    #
    #   Example response (status 200):
    #   {"detail": "Entry deleted successfully"}
    #
    #   Hint: Look at how the update_entry endpoint checks for existence
    #
    #   Was: raise HTTPException(status_code=501, detail="Not implemented...")
    # ---------------------------------------------------------------

    # Step 1 — existence check. DELETE on a missing row succeeds silently
    # in SQL (0 rows affected, no error), so we must check first or a
    # bogus id would wrongly return 200.
    entry = await entry_service.get_entry(entry_id)

    # Step 2 — translate "no row" into HTTP 404.
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Step 3 — the actual delete. DELETE FROM entries WHERE id = $1.
    await entry_service.delete_entry(entry_id)

    # Step 4 — wrapped dict, NOT a bare return. Nothing to hand back after
    # deletion, and the test asserts this exact shape.
    return {"detail": "Entry deleted successfully"}


@router.delete("/entries")
async def delete_all_entries(entry_service: EntryService = Depends(get_entry_service)):
    """Delete all journal entries"""
    await entry_service.delete_all_entries()
    return {"detail": "All entries deleted"}


@router.post("/entries/{entry_id}/analyze", response_model=AnalysisResponse)
async def analyze_entry(entry_id: str, entry_service: EntryService = Depends(get_entry_service)):
    """
    Analyze a journal entry using AI.

    Returns sentiment, summary, key topics, entry_id, and created_at timestamp.
    The LLM call itself lives in api/services/llm_service.py - implementing
    analyze_journal_entry there is part of the capstone.
    """
    entry = await entry_service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry_text = f"{entry['work']} {entry['struggle']} {entry['intention']}"

    try:
        return await analyze_journal_entry(entry_id, entry_text)
    except NotImplementedError as e:
        raise HTTPException(
            status_code=501,
            detail="LLM analysis not yet implemented - see api/services/llm_service.py",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Analysis failed: {e!s}") from e
