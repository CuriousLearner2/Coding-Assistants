# wa_toolkit — Reusable WhatsApp Bot Framework

Extracted from the Replate WhatsApp simulator, `wa_toolkit` is a thin Python library for building multi-turn WhatsApp chatbots backed by Supabase and an LLM. It handles the plumbing — sessions, state routing, AI extraction, retries, and local simulation — so each new project only writes the conversation logic specific to its domain.

---

## Motivation

The Replate simulator (`whatsapp_simulator.py`) contains several components that are entirely project-agnostic:

- Session persistence in Supabase
- State machine dispatch
- Global command handling (STOP, RESET, NEW)
- LLM extraction with retry and offline fallback
- A REPL harness for local testing

Any WhatsApp bot that uses a multi-turn conversation, persists state between messages, and uses an LLM to parse free text needs all of these. Rather than re-implementing them per project, `wa_toolkit` packages them as importable building blocks.

---

## Package Structure

```
wa_toolkit/
├── __init__.py
├── session.py        # Supabase-backed session manager
├── state_machine.py  # State router and handler registry
├── ai_extractor.py   # LLM call + retry + mock toggle
├── simulator.py      # Local REPL harness
└── errors.py         # Standardized error classes
```

Each project that uses `wa_toolkit` only writes:
- A set of state handler functions
- LLM prompts and expected JSON schemas
- A final action (e.g. insert a row, send an email, call an API)

---

## Module Design

### `session.py` — SessionManager

Manages a `whatsapp_sessions` table in Supabase. The schema is fixed:

```sql
CREATE TABLE whatsapp_sessions (
  phone_number TEXT PRIMARY KEY,
  state        TEXT NOT NULL,
  temp_data    JSONB DEFAULT '{}',
  updated_at   TIMESTAMPTZ DEFAULT now()
);
```

**API:**

```python
class SessionManager:
    def __init__(self, supabase_client, table: str = "whatsapp_sessions"):
        ...

    def get(self, phone: str) -> dict | None:
        """Return the session row for this phone, or None if it doesn't exist."""

    def create(self, phone: str, initial_state: str) -> dict:
        """Upsert a fresh session in initial_state with empty temp_data."""

    def update_state(self, phone: str, state: str) -> None:
        """Transition to a new state."""

    def update_data(self, phone: str, data: dict) -> None:
        """Merge new fields into temp_data."""

    def update(self, phone: str, state: str, data: dict) -> None:
        """Transition state and merge data in a single write."""

    def delete(self, phone: str) -> None:
        """Delete the session (on STOP/CANCEL)."""
```

Only the table name is project-specific. The schema stays constant across projects.

---

### `state_machine.py` — StateMachine

A simple registry that maps state names to handler functions and dispatches incoming messages.

**Design Insights (V1):**
*   **Media Readiness**: The `handle` method accepts `Any` for the message parameter. This allows future V2 handlers to process complex objects (containing image URLs or MIME types) while remaining compatible with simple text strings today.
*   **Robustness**: The `handle` method includes a global `try/except` wrapper. If a domain handler throws an unhandled exception, the StateMachine catches it, logs the trace, and returns a configurable "Technical Error" message to the user, preventing the entire bot process from crashing.

**API:**

```python
class StateMachine:
    def __init__(self, session_manager: SessionManager, initial_state: str, welcome_message: str):
        ...

    def register(self, state: str, handler: Callable[[str, Any, dict], tuple[str, str, dict]]):
        """
        Register a handler for a state.

        The handler signature is:
            handler(phone, message, temp_data) -> (reply, next_state, updated_data)
        """

    def handle(self, phone: str, message: Any) -> str:
        """
        Dispatch the message to the correct handler based on session state.
        Returns the reply string to send back to the user.
        """
```

**Global commands** (STOP, CANCEL, RESET, NEW, START) are intercepted before dispatch and handled uniformly. Projects can override the responses for these commands at construction time.

---

### `errors.py` — Standardized Errors

Provides a consistent exception hierarchy so projects can catch specific toolkit failures.

**Key Classes:**
*   `WAToolkitError`: Base exception for all toolkit-related issues.
*   `AIExtractionError`: Raised when the LLM fails after all retries and fallback models.
*   `SessionError`: Raised when database operations fail or the schema is invalid.
*   `StateNotFoundError`: Raised if the session is in a state with no registered handler.

---

### `ai_extractor.py` — AIExtractor

Wraps an LLM call with retry logic, model fallback, and an offline mock mode.

**API:**

```python
class AIExtractor:
    def __init__(
        self,
        api_key: str,
        primary_model: str = "gemini-flash-latest",
        fallback_model: str = "gemini-flash-lite-latest",
        mock_fn: Callable[[str], dict] | None = None,
        mock_env_var: str = "MOCK_AI",
    ):
        ...

    def extract(self, prompt: str, schema: dict) -> dict:
        """
        Call the LLM with the given prompt, expecting a JSON response
        matching schema. Retries with exponential backoff (5 attempts),
        falls back to fallback_model, then to mock_fn if all else fails.
        """
```

**Retry policy** (from Replate, carried forward unchanged):
- 5 attempts
- Exponential backoff: 4s min, 20s max
- Retries on any exception
- Falls back to `fallback_model` after primary fails
- Falls back to `mock_fn` after fallback fails
- If no `mock_fn` is provided, re-raises the last exception

---

### `simulator.py` — REPL Harness

A command-line loop for testing a bot locally without Meta infrastructure.

**API:**

```python
def run(
    handle_fn: Callable[[str, str], str],
    default_phone: str = "+14155550000",
    banner: str = "WhatsApp Bot Simulator",
):
    """
    Start an interactive REPL.
    - Reads phone number from --phone CLI arg (default: default_phone).
    - Loops on input(), calls handle_fn(phone, message), prints reply.
    - EXIT quits; KeyboardInterrupt exits cleanly.
    """
```

---

## Engineering Standards

1. **Dependency Stability**: `wa_toolkit` pins its dependencies (like `supabase-py` and `google-genai`) to specific versions to ensure that host projects (like Replate) don't face breaking changes during upstream updates.
2. **Stateless Handlers**: Handlers MUST remain pure functions of `(phone, message, data)`. They should not manage database connections or persistence directly; that is the role of the `StateMachine` and `SessionManager`.
3. **Graceful Degradation**: If the AI extraction fails all retries and fallback models, it must return a valid JSON object with the `requires_review` flag set to `true`, rather than crashing.

---

## Roadmap / V2

- **Media Support**: Expand the `message` object to handle WhatsApp images, documents, and voice notes.
- **Provider Agnostic**: Support for Twilio and Meta Cloud API through a unified `MessageAdapter`.
- **Advanced State Persistence**: Support for Redis as a faster alternative to Supabase for high-concurrency bots.

---

## How a New Project Uses It

### 1. Install

```bash
pip install wa-toolkit   # or: pip install -e path/to/wa_toolkit
```

### 2. Set up Supabase

Run the session table migration (one-time, same for all projects):

```sql
CREATE TABLE whatsapp_sessions (
  phone_number TEXT PRIMARY KEY,
  state        TEXT NOT NULL,
  temp_data    JSONB DEFAULT '{}',
  updated_at   TIMESTAMPTZ DEFAULT now()
);
```

### 3. Write your handlers

Each handler is a plain function:

```python
def handle_description(phone: str, message: str, data: dict) -> tuple[str, str, dict]:
    result = extractor.extract(prompt=f'Parse this: "{message}"', schema={...})
    data.update(result)
    reply = f"Got it: {result['item']}. Does that look right? (Yes / correct me)"
    return reply, "AWAITING_REVIEW", data
```

### 4. Wire it up

```python
from wa_toolkit.session import SessionManager
from wa_toolkit.state_machine import StateMachine
from wa_toolkit.ai_extractor import AIExtractor
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
sessions = SessionManager(supabase)
extractor = AIExtractor(api_key=GEMINI_KEY, mock_fn=my_mock)

sm = StateMachine(sessions, initial_state="AWAITING_DESC", welcome_message="👋 Hi!")
sm.register("AWAITING_DESC",   handle_description)
sm.register("AWAITING_REVIEW", handle_review)
sm.register("COMPLETED",       handle_done)

def handle_message(phone: str, message: str) -> str:
    return sm.handle(phone, message)
```
