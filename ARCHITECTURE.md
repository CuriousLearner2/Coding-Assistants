# Architecture Overview: Replate Python CLI

## 1. System Components

### 1.1 Python CLI (Frontend)
*   **Role:** The user-facing terminal interface for volunteer drivers.
*   **Logic:** Handles navigation, user input validation, and local session management.
*   **State:** Minimal local state (session token) stored in `~/.replate/session.json`.

### 1.2 Supabase (Backend-as-a-Service)
*   **Role:** The centralized source of truth for all driver, task, and partner data.
*   **Auth:** Manages user identity (simulated in this CLI version using the `drivers` table).
*   **Database:** PostgreSQL with Row-Level Security (RLS) to protect data at the query level.
*   **API:** Automatically generated RESTful interface used by the Python `supabase-py` client.

### 1.3 Legacy Mock Backend (Deprecated)
*   **Role:** A local Flask server that mimics the original Ruby on Rails API.
*   **Status:** Retained for offline development and legacy integration testing.

## 2. Data Flow

### 2.1 Authentication Flow
1. User enters email/password in the CLI.
2. CLI sends a query to the Supabase `drivers` table.
3. If valid, a session is created and saved locally.

### 2.2 Task Lifecycle
1. **Discovery:** CLI fetches available tasks from Supabase where `status = 'available'`.
2. **Claim:** CLI updates the task in Supabase, setting `status = 'claimed'` and `driver_id = current_user_id`. RLS ensures only one user can claim a task at a time.
3. **Completion:** CLI updates the task with final weight and partner destination.

## 3. Technology Alignment
This Python CLI is architecturally aligned with the **Replate React Native** mobile app. Both share:
*   The same **Supabase schema** (`drivers`, `tasks`, `partners`).
*   The same **Geo-logic** (Haversine distance ranking).
*   The same **Security model** (RLS and Token-based auth).

## 4. Portability
The `client/api.py` module acts as a **Backend Switcher**. By changing the `REPLATE_BACKEND` environment variable, the entire CLI can pivot between the high-fidelity remote Supabase and the low-fidelity local mock without changing any UI logic.
