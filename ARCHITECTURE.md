# Architecture Overview: Replate Multi-Channel Platform

## 1. System Components

### 1.1 Python CLI (Frontend)
*   **Role:** Terminal interface for volunteer drivers.
*   **API Client:** A custom wrapper in `client/api.py` that supports both Supabase and Mock backends via the `REPLATE_BACKEND` env var.

### 1.2 Supabase (Core Backend)
*   **Database:** PostgreSQL.
*   **Edge Functions:** TypeScript serverless functions to handle WhatsApp Webhooks and Gemini LLM integration.
*   **Persistence:** Primary store for Drivers, Tasks, Partners, and WhatsApp Sessions.

## 2. WhatsApp Multi-Turn Logic

### 2.1 State Machine (Simplified V1)
The system uses a 3-turn conversational flow. High-level states are listed below. For the full state-transition diagram and special command handling (RESET/STOP), refer to `TECH_DESIGN_WHATSAPP_V1.md`.

| State | Action | Next State |
|-------|--------|------------|
| `START` | Greet donor, ask for food description. | `AWAITING_DESC` |
| `AWAITING_DESC` | Extract Category & Qty using Gemini Pro, ask for pickup window. | `AWAITING_WINDOW` |
| `AWAITING_WINDOW` | Inject Task into Supabase, send confirmation. | `COMPLETED` |
| `COMPLETED` | Terminal state; wait for 'NEW' to restart. | `START` (on trigger) |

### 2.2 Session Expiry (TTL)
*   **Policy:** WhatsApp sessions expire **24 hours** after the last interaction.
*   **Implementation:** A PostgreSQL Cron job (or Supabase scheduled function) deletes rows in `whatsapp_sessions` where `updated_at < now() - interval '24 hours'`.

### 2.3 Webhook Verification (V1 Requirement)
Incoming requests from Meta **must** be verified using the `X-Hub-Signature-256` header and the app's `App Secret`. Requests failing verification will be rejected with a 401 Unauthorized before any processing occurs.

## 3. Intelligence & Fallbacks (Gemini)

### 3.1 Extraction Logic
The system uses Gemini Pro to transform unstructured text into:
*   `category`: One of [Prepared, Produce, Bakery, Dairy, Meat, Pantry].
*   `quantity_lb`: Numeric estimate.

### 3.2 Fallback Strategy
If Gemini returns low-confidence scores, fails to parse, or the API is unavailable:
1.  **Default Category:** Assign `Pantry` (lowest risk).
2.  **Generic Description:** Save the raw user text to `food_description` without modification.
3.  **Human Flag:** Set a `requires_review` flag on the `tasks` row for Replate Admins.

## 4. Data Privacy & Retention (PII)

### 4.1 donor_whatsapp_id
*   **Classification:** This field is considered **Personally Identifiable Information (PII)**.
*   **Retention Policy:** The `donor_whatsapp_id` is retained for **30 days** following task completion to allow for dispute resolution. After 30 days, a background worker masks this field (e.g., `whatsapp_user_masked`).

## 5. Database Schema Enhancements (V1)

### 5.1 Tasks Table
*   `category`: TEXT (Check constraint enforced).
*   `quantity_lb`: NUMERIC (Standardized unit).
*   `address_json`: Stores geo-coordinates and human-readable address.
*   `requires_review`: BOOLEAN (Flag for AI extraction issues).

### 5.2 Fixture Reconciliation
To maintain consistency between legacy and Supabase modes, `quantity_lb` is calculated as:
`quantity_lb = tray_count * multiplier` (where multiplier is based on `tray_type`).
*   `full`: 15 lbs
*   `half`: 7 lbs
*   `small`: 3 lbs

## 6. Security & Identity Status
*   **Simulated Auth:** V1 uses manual lookups in `drivers` by email for rapid prototyping.
*   **Production Path:** V2 will migrate to `supabase.auth` and signed JWTs.
