"""Task 4: Implement analyze_journal_entry using any OpenAI-compatible API.

This project mandates the OpenAI Python SDK, which works with:
  - GitHub Models (default, free, no credit card required)
  - OpenAI proper
  - Azure OpenAI
  - Groq, Together, OpenRouter, Fireworks, DeepInfra
  - Ollama, LM Studio, vLLM (local)
  - Anthropic via their OpenAI-compat endpoint

Set OPENAI_API_KEY, and optionally OPENAI_BASE_URL and OPENAI_MODEL
in your .env file. Settings are loaded by ``api.config.Settings``.
"""

import json

from openai import AsyncOpenAI

from api.config import get_settings


def _default_client() -> AsyncOpenAI:
    """Construct the real OpenAI client from application settings.

    Called lazily from ``analyze_journal_entry`` so tests can inject a
    ``MockAsyncOpenAI`` without ever triggering this code path.
    """
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


async def analyze_journal_entry(
    entry_id: str,
    entry_text: str,
    client: AsyncOpenAI | None = None,
) -> dict:
    """Analyze a journal entry using an OpenAI-compatible LLM.

    Args:
        entry_id: ID of the entry being analyzed (pass through to the result).
        entry_text: Combined work + struggle + intention text.
        client: OpenAI client. If None, a default one is constructed from
            application settings. Tests pass in a MockAsyncOpenAI here; production code
            in the router calls this with no ``client`` argument.

    Returns:
        A dict matching AnalysisResponse:
            {
                "entry_id":  str,
                "sentiment": str,   # "positive" | "negative" | "neutral"
                "summary":   str,
                "topics":    list[str],
            }
    """
    # ---------------------------------------------------------------
    # ORIGINAL STARTER TODO (kept for reference — Task 4, completed)
    #
    #   1. If client is None, call _default_client() to construct one.
    #   2. Build a messages list that includes entry_text somewhere
    #      (the unit tests check that the entry text reaches the LLM).
    #   3. Call client.chat.completions.create(...) with a model name
    #      (use get_settings().openai_model — defaults to "gpt-4o-mini").
    #   4. Parse the assistant's JSON response with json.loads().
    #   5. Return a dict with entry_id, sentiment, summary, topics.
    #
    #   Was: raise NotImplementedError(...)
    # ---------------------------------------------------------------

    # Step 1 — pick the client.
    #   Tests inject a MockAsyncOpenAI (client is not None), so this branch
    #   is skipped and no real network call is ever made in the test suite.
    #   In production the router calls us with no client, so we build the
    #   real one lazily here — only when actually needed.
    if client is None:
        client = _default_client()

    settings = get_settings()

    # Step 2 — build the messages list.
    #   system message: pins the model to a strict JSON contract so the
    #     response is machine-parseable (no markdown, no prose).
    #   user message: carries entry_text. The test asserts that "FastAPI"
    #     (part of the sample entry) reaches the LLM, so entry_text MUST
    #     appear in a message's content — this is where it goes.
    system_prompt = (
        "You are a journaling assistant. Analyze the entry and respond with "
        "ONLY a JSON object, no markdown, no prose, with exactly these keys: "
        '"sentiment" (one of "positive", "negative", "neutral"), '
        '"summary" (a 2-sentence string), '
        '"topics" (a list of 2-4 short strings).'
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": entry_text},
    ]

    # Step 3 — call the LLM.
    #   model comes from settings (defaults to "gpt-4o-mini").
    #   response_format nudges compatible providers (OpenAI, GitHub Models)
    #   to emit valid JSON. It's harmless where unsupported because the
    #   prompt already demands JSON. The mock ignores kwargs entirely.
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        response_format={"type": "json_object"},
    )

    # Step 4 — parse the assistant's reply.
    #   The model's text lives at choices[0].message.content. Fall back to
    #   "{}" if it's None so json.loads never crashes on a null response.
    raw = response.choices[0].message.content or "{}"
    parsed = json.loads(raw)

    # Step 5 — assemble the result dict.
    #   entry_id is injected HERE, not requested from the model — the LLM
    #   never sees it and never returns it. AnalysisResponse (checked in the
    #   test) requires entry_id, so we add it ourselves alongside the three
    #   fields the model produced.
    return {
        "entry_id": entry_id,
        "sentiment": parsed["sentiment"],
        "summary": parsed["summary"],
        "topics": parsed["topics"],
    }
