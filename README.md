# AI Customer Support Chatbot

FastAPI, LangGraph, and a static admin/chat interface for business inquiries and appointment handling.

## Run locally

1. Create a Python 3.10+ virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `app/backend/.env` and add at least one provider key, or enter the key from the admin settings page.
4. From `app/backend`, run `uvicorn server:app --reload --port 8001`.
5. Open `http://localhost:8001` for chat or `http://localhost:8001/admin.html` for settings.

## Providers and guardrails

Every agent can independently use Groq or OpenRouter. For OpenRouter, select the provider and enter its full model identifier in the custom model field, such as `provider/model-name`.

The guardrail runs before the supervisor and before any booking tool. It detects prompt injection and queries outside the configured business context. Admin settings control:

- enabled state, local heuristic switch, provider, model, and optional agent-specific key;
- the classification system prompt;
- replies for injection, irrelevant input, and guardrail failure;
- fail closed (`block`) or fail open (`allow`) behavior.

Stored keys are write-only through the API: `GET /api/settings/config` reports configured flags and never returns key values.

## Important deployment note

The existing project does not include admin authentication. Put the admin page and `/api/settings`, chat-management, user, booking, and blockout routes behind authentication before exposing this application publicly.
