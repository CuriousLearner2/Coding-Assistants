# Technical Design Document: WhatsApp Lead Generation (V1)

## 1. Overview
This document details the technical implementation of the automated food donation intake system via the WhatsApp Business API. It uses a state-machine-based conversation flow and Gemini Pro for intelligent data extraction.

## 2. System Architecture

### 2.1 Component Flow
1. **Meta Webhook:** Incoming WhatsApp messages are sent to a Supabase Edge Function (`/whatsapp-webhook`).
2. **Session Manager:** The function identifies the donor by phone number and retrieves their current state from the `whatsapp_sessions` table.
3. **LLM Parser (Turn 2):** When a food description is received, the function calls the **Gemini Pro API** to categorize and estimate weight.
4. **Task Injection:** Upon the final turn (pickup window), a new record is created in the `tasks` table.
5. **WhatsApp API:** The function responds to the donor using the WhatsApp Cloud API.

## 3. Data Schema

### 3.1 `whatsapp_sessions` Table
| Column | Type | Constraints |
|--------|------|-------------|
| `phone_number` | TEXT | Primary Key |
| `state` | TEXT | DEFAULT 'START' |
| `temp_data` | JSONB | Stores partial extraction (category, weight, etc.) |
| `updated_at` | TIMESTAMPTZ| DEFAULT now() |

### 3.2 `tasks` Table Updates (V1 Alignment)
* `category`: (Prepared, Produce, Bakery, Dairy, Meat, Pantry)
* `quantity_lb`: Numeric
* `donor_whatsapp_id`: Text
* `requires_review`: Boolean (Set to TRUE if AI confidence is low)

## 4. Multi-Turn State Machine

| State | User Input | AI Action | Bot Response |
|-------|------------|-----------|--------------|
| `START` (Implicit) | "NEW" / "START" | None | "Thanks! What kind of food do you have?" |
| `AWAITING_DESC` | "3 trays of pasta" | Extract Details | Summary of items, categories, and weight. "Does this look correct?" |
| `AWAITING_REVIEW` | "Yes" or correction | Re-extract (if needed) | "Great! When is the latest we can pick this up?" |
| `AWAITING_WINDOW` | "Until 5pm today" | Parse Window | Summary of date and time. "Does this work?" |
| `AWAITING_WINDOW_REVIEW` | "Yes" or correction | Re-parse (if needed) | "Success! Your donation is live. Thank you!" |
| `COMPLETED` | Any text | None | "Your donation is logged. Type 'NEW' to start another." |

### 4.1 Special Commands & Unexpected Input
* **"RESET" / "NEW":** Immediately resets the session state to `AWAITING_DESC` and clears `temp_data`.
* **"STOP" / "CANCEL":** Deletes the row from `whatsapp_sessions` and stops the flow.
* **Media/Images:** If an image is sent during `AWAITING_DESC`, the bot replies: *"I can't see images yet! Please type a short description of the food."* (Native photo support deferred to V2).

## 5. Intelligence Strategy (Gemini Pro)

### 5.1 System Prompt
The system extracts 5 structured fields from unstructured text to minimize donor friction:
1. `categories`: Array of matching labels (Prepared, Produce, Bakery, Dairy, Meat/Protein, Beverage, Pantry).
2. `quantity_lb`: Estimated total weight in pounds.
3. `food_description`: 2-3 word high-level summary.
4. `item_list`: Bulleted list of all mentioned items.
5. `requires_review`: Boolean flag for high-ambiguity descriptions.

### 5.2 Fallbacks
* **Extraction Failure:** If Gemini cannot parse the description, the system uses a local regex-based fallback to assign `Pantry` (5 lbs) and sets `requires_review = TRUE`.
* **Correction Logic:** Users can correct the AI by typing a free-form message (e.g., "Actually it's 50 lbs"). The system uses Gemini to "update" the existing JSON state based on this new input.

## 6. Security & Privacy

### 6.1 Webhook Verification
* **Signature Check:** The Edge Function validates the `X-Hub-Signature-256` header if `WHATSAPP_APP_SECRET` is configured in the environment. If the secret is missing, verification is bypassed (for development ease).
* **PII Retention:** A planned PostgreSQL Cron job will handle session deletion:
  ```sql
  DELETE FROM whatsapp_sessions WHERE updated_at < now() - interval '24 hours';
  ```

## 7. Implementation Plan
1. **SQL Setup:** Create `whatsapp_sessions` table and add `requires_review` to `tasks`.
2. **Edge Function:** Develop the TypeScript function for Meta Webhook handling.
3. **Gemini Integration:** Implement the `extractDonationDetails` utility using the Google AI SDK.
4. **Mock Testing:** Create a local Python script to simulate WhatsApp Webhook payloads for rapid iteration.
