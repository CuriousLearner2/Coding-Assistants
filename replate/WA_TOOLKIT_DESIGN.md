# Technical Design: wa_toolkit

**Status**: Draft
**Version**: 1.0.0
**Author**: Replate Engineering

## 1. Objective
To provide a reusable, modular Python framework for building multi-turn WhatsApp chatbots. The toolkit abstracts the "plumbing" (session persistence, state routing, AI extraction, and local simulation) so developers can focus exclusively on conversation logic and domain-specific actions.

## 2. System Architecture

```mermaid
graph TD
    A[WhatsApp/Simulator] -->|Message| B(StateMachine)
    B -->|Check Session| C(SessionManager)
    C <-->|Read/Write| D[(Supabase)]
    B -->|Dispatch| E(Domain Handlers)
    E -->|Call AI| F(AIExtractor)
    F <-->|Generate| G[Gemini API]
    E -->|Return| B
    B -->|Reply| A
```

## 3. Core Components

### 3.0 Package Structure
The toolkit is organized as a modular Python package:

```text
wa_toolkit/
├── __init__.py        # Package entry point
├── session.py         # SessionManager (Supabase persistence)
├── state_machine.py   # StateMachine (Orchestration & Dispatch)
├── ai_extractor.py    # AIExtractor (Gemini with resilience)
├── simulator.py       # Simulator (Local REPL)
└── errors.py          # Exception hierarchy
```

### 3.1 SessionManager (`session.py`)
**Base Class**: `SessionManager`
Responsible for persistence. It assumes a specific PostgreSQL schema in Supabase but allows for a custom table name.

**Implementation Details:**
- **Storage**: Supabase `JSONB` for `temp_data` to allow arbitrary key-value storage per project.
- **Consistency**: To prevent inconsistent states during process failures, the toolkit MUST perform a single write operation when updating both state and data.
- **Methods**:
    - `get(phone)`: Returns a `dict` representing the session.
    - `create(phone, state)`: Initializes a session using `.upsert()`.
    - `update(phone, state, data)`: Persists both `state` and `temp_data` in a single `.update()` call to ensure transactional consistency.

### 3.2 StateMachine (`state_machine.py`)
The orchestrator. It manages the lifecycle of a message from arrival to reply.

**Key Features:**
- **Command Interception**: Intercepts "system" commands (`RESET`, `STOP`, `NEW`) before they reach domain handlers.
- **Robust Error Handling**: Wraps handler execution in `try/except` to prevent bot crashes.
- **V1 Media Readiness**: The `handle(phone, message)` signature accepts `Any` for the message to remain forward-compatible with V2 rich-media objects.

### 3.3 AIExtractor (`ai_extractor.py`)
A wrapper around the Google GenAI SDK (Gemini) with built-in resilience.

**Robustness Strategy:**
- **Exponential Backoff**: 5 retries starting at 4s.
- **Model Fallback**: Automatically switches from `gemini-flash-latest` to `gemini-flash-lite-latest` on failure.
- **Offline Mode**: If `MOCK_AI=true`, it skips the API and calls a project-provided `mock_fn`.

### 3.4 Simulator (`simulator.py`)
A REPL-based interface for rapid local testing.

**Features:**
- Provides a clean loop for donor-bot interaction.
- Allows overriding the phone number via `--phone` for testing multi-session logic.

## 4. Error Handling & Exceptions (`errors.py`)
The toolkit defines a hierarchy of exceptions:

- `WAToolkitError`: Base class.
- `AIExtractionError`: Failed after all retries and fallbacks.
- `SessionError`: Database connection or schema mismatch issues.
- `StateNotFoundError`: Attempted to transition to a state with no registered handler.

## 5. Engineering Standards (Requirements)

- **Pinned Dependencies**: The implementation MUST include a `requirements.txt` that pins `supabase` and `google-genai` to specific versions to prevent breaking changes in host projects.
- **Type Safety**: Use Python type hints (`typing`) for all method signatures.
- **Stateless Handlers**: Handlers MUST remain pure functions; they do not manage persistence.
- **Graceful Degradation**: Failed AI extractions must return a valid JSON object with `requires_review: true` instead of raising unhandled exceptions to the StateMachine.

## 6. Testing Strategy

The toolkit itself must be validated independently of the projects using it:

1.  **Unit Tests (`StateMachine`)**: Verify command interception and handler routing using mock handlers and a mock SessionManager.
2.  **Mock Integration (`SessionManager`)**: Test session CRUD operations against a mock Supabase client to ensure single-write consistency.
3.  **Resilience Tests (`AIExtractor`)**: Force API failures to verify that exponential backoff and model fallback trigger correctly.
4.  **REPL Verification**: Ensure the simulator correctly terminates on `EXIT` and handles `KeyboardInterrupt`.

## 7. Roadmap / V2

- **Rich Media**: Implementation of a `Message` object to parse image URLs and voice notes.
- **Storage Adapters**: Interface-based persistence to support Redis or In-Memory storage.
