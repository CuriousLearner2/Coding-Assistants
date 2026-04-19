# Architecture Overview: Replate Multi-Channel Platform

## 1. System Components

### 1.1 Python CLI (Frontend)
*   **Role:** Terminal interface for volunteer drivers.
*   **State:** Minimal local state (session token) in `~/.replate/session.json`.
*   **API Client:** A custom wrapper in `client/api.py` that supports both Supabase and Mock backends via the `REPLATE_BACKEND` env var.

### 1.2 Supabase (Core Backend)
*   **Database:** PostgreSQL.
*   **Edge Functions:** TypeScript serverless functions to handle WhatsApp Webhooks and Gemini LLM integration.
*   **Persistence:** Primary store for Drivers, Tasks, Partners, and WhatsApp Sessions.

### 1.3 WhatsApp/Meta Integration
*   **Webhooks:** Meta sends incoming messages to a Supabase Edge Function endpoint.
*   **State Machine:** Managed via the `whatsapp_sessions` table (see Section 2.1).

## 2. Technical Implementation Details

### 2.1 WhatsApp Multi-Turn State Machine
To handle conversational state, the `whatsapp_sessions` table tracks:
| Field | Type | Description |
|-------|------|-------------|
| `phone_number` | TEXT (PK) | Unique identifier for the donor. |
| `state` | TEXT | Current stage (e.g., `AWAITING_DESC`, `AWAITING_WEIGHT`). |
| `temp_data` | JSONB | Partial data captured during the conversation. |

### 2.2 Unstructured-to-Structured Data Flow
1. **Input:** User types "3 trays of veggie pasta" in WhatsApp.
2. **AI Processing:** Supabase Edge Function calls **Gemini Pro** with a system prompt to extract:
   * `category`: "Prepared Meals"
   * `quantity_lb`: 15.0 (estimated)
3. **Injection:** Edge Function inserts a new row into the `tasks` table with `status='available'`.

### 2.3 Database Schema Enhancements (V1)
*   **`tasks` Table Updates:**
    * `category`: (Check constraint: Prepared, Produce, Bakery, Dairy, Meat, Pantry)
    * `quantity_lb`: Numeric
    * `donor_whatsapp_id`: Text (linking back to the donor)
    * `address_json`: Stores street, city, state, zip for Haversine calculations.

## 3. Security & Identity Status

### 3.1 Simulated Identity Layer (⚠️ PROTOTYPE ONLY)
*   **Login/Signup:** Performed via manual table lookups in `drivers` by email.
*   **Passwords:** Not hashed or verified in V1.
*   **Tokens:** Hardcoded `SIMULATED_SESSION_JWT` used to maintain CLI session state.

### 3.2 Production Migration Path
1. Replace `api.py` auth calls with `supabase.auth.sign_in_with_password()`.
2. Enable RLS policies that verify `auth.uid() == driver_id`.
3. Implement WhatsApp signature verification to validate incoming Meta webhooks.

## 4. Haversine Geo-Logic
The distance calculation is performed in the `client/api.py` (when using Supabase) or the `dummy_backend` (when in mock mode) using the Haversine formula to rank tasks.
