# Product Requirements Document (PRD): Replate Multi-Channel Platform

## 1. Executive Summary
Replate is a logistics platform designed to eliminate food waste by connecting donors (businesses) with volunteer drivers and NPOs. This document outlines the phased rollout of the platform, moving from a core CLI tool to a multi-channel system integrated with the WhatsApp Business API.

---

## 2. Version 1: Core Operations & Lead Generation (CURRENT)

### 2.1 Scope
The primary goal of V1 is to digitize the driver workflow and automate the intake of food donations via WhatsApp.

### 2.2 Driver Operations (Python CLI)
*   **Authentication:** Simulated login/signup for prototype testing with local session persistence.
*   **Onboarding:** Guided NPO partner selection for new drivers.
*   **Task Discovery:** Browse available pickups for Today/Tomorrow, ranked by Haversine distance.
*   **Task Execution:** Atomically claim tasks and log completion (weight, photo simulation, and destination).

### 2.3 WhatsApp Lead Generation (#1)
*   **Automated Intake Bot:** A conversational interface for donors to report surplus food without an app.
*   **Multi-Turn Interaction:** 
    1. Capture donor identity/location.
    2. Collect food description.
    3. Capture estimated quantity and pickup window.
*   **State Management:** A dedicated `whatsapp_sessions` table in Supabase to track multi-turn progress.
*   **Smart Categorization (LLM):** Integration with Gemini API to parse natural language (e.g., "3 trays of veggie pasta") into structured data:
    *   **Category:** (Prepared Meals, Produce, Bakery, etc.)
    *   **Quantity:** Estimated weight in lbs.
*   **Auto-Injection:** Completed conversations automatically create a new `available` task in the Supabase database.

---

## 3. Version 2: Proactive Coordination & Impact

### 3.1 Proactive Volunteer Dispatch (#2)
*   **Proximity Alerts:** Automated WhatsApp templates sent to the nearest 3 drivers when a high-priority task is injected.
*   **Direct Links:** Messages include deep-links to the CLI/App to claim the task instantly.

### 3.2 Donor Impact Loop (#3)
*   **Automated Gratitude:** WhatsApp message sent to the donor the moment a volunteer logs completion.
*   **Metrics:** Real-time feedback on how many meals the specific donation provided.

### 3.3 Live Support & Escalation (#4)
*   **Live Chat:** A "Help" command in both CLI and WhatsApp that routes the user to a human Replate dispatcher.

---

## 4. Technical Requirements

### 4.1 Backend Architecture
*   **Infrastructure:** Supabase (PostgreSQL, Edge Functions, RLS).
*   **AI Layer:** Gemini Pro for unstructured data extraction (V1).
*   **Messaging:** Meta WhatsApp Business API Cloud (V1/V2).

### 4.2 Data Schema (V1 Enhancements)
*   **Tasks Table:** Add `category`, `quantity_lb`, and `donor_whatsapp_id`.
*   **WhatsApp Sessions Table:** Track `phone_number`, `state`, and `temp_payload`.

### 4.3 Security
*   **V1 Prototype:** Simulated Identity Layer (manual table lookups).
*   **V2 Production:** Full migration to Supabase Auth (JWT/signed tokens).

---

## 5. Reviewer Checklist
- [ ] Is the transition from unstructured WhatsApp text to structured database rows clearly defined?
- [ ] Does the V1 schema support the required LLM categorization outputs?
- [ ] Is the state machine for the multi-turn conversation robust enough for V1?
