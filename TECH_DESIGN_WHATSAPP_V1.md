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
| `START` | "I have food" | None | "Thanks! What kind of food do you have?" |
| `AWAITING_DESC` | "3 trays of pasta" | Extract Category & Qty | "Got it. When is the latest we can pick this up?" |
| `AWAITING_WINDOW` | "Until 5pm today" | Parse Time | "Confirmed! A volunteer will be notified." |

## 5. Intelligence Strategy (Gemini Pro)

### 5.1 System Prompt
```text
You are a logistics coordinator for Replate. 
Extract the following from the user's food description:
1. Category: [Prepared, Produce, Bakery, Dairy, Meat, Pantry]
2. Quantity_LB: Estimated weight in pounds.
3. Description: A clean version of the user's text.

Input: "I have 2 large boxes of leftover donuts"
Output: {"category": "Bakery", "quantity_lb": 10, "description": "2 boxes of donuts"}
```

### 5.2 Fallbacks
* **Low Confidence:** If the LLM cannot determine a category, the system defaults to `Pantry` and sets `requires_review = TRUE`.
* **API Failure:** The raw text is saved to `food_description`, and the donor is allowed to proceed to ensure the lead is not lost.

## 6. Security & Privacy

### 6.1 Webhook Verification
* **Signature Check:** The Edge Function will validate the `X-Hub-Signature-256` using the `WHATSAPP_APP_SECRET`.
* **PII Retention:** A PostgreSQL Cron job will run every 24 hours:
  ```sql
  DELETE FROM whatsapp_sessions WHERE updated_at < now() - interval '24 hours';
  ```

## 7. Implementation Plan
1. **SQL Setup:** Create `whatsapp_sessions` table and add `requires_review` to `tasks`.
2. **Edge Function:** Develop the TypeScript function for Meta Webhook handling.
3. **Gemini Integration:** Implement the `extractDonationDetails` utility using the Google AI SDK.
4. **Mock Testing:** Create a local Python script to simulate WhatsApp Webhook payloads for rapid iteration.
