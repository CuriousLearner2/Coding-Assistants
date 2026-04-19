# Product Requirements Document (PRD): Replate Multi-Channel Platform

## 1. Executive Summary
Replate is a multi-channel logistics platform designed to eliminate food waste. It connects food donors (businesses) with volunteer drivers and non-profit organizations (NPOs). The system combines a **Python CLI** for driver operations with a **WhatsApp Business API** layer for donor intake and real-time coordination.

## 2. Target Users
*   **Volunteer Drivers:** Use the CLI/App to discover, claim, and log pickups.
*   **Food Donors (Restaurants/Cafeterias):** Use WhatsApp to report surplus food without needing to install a dedicated app.
*   **Replate Admins:** Oversee the automated flow and provide support.

## 3. Core Functionality

### 3.1 Driver Operations (CLI/App)
*   **Authentication:** Secure login/signup with local session persistence.
*   **Onboarding:** Selection of primary NPO partner affiliation.
*   **Task Discovery:** Browse available pickups ranked by proximity (Haversine distance).
*   **Task Execution:** Claiming tasks and logging completion (weight, photo, destination).

### 3.2 WhatsApp Business Integration (Donor & Dispatch)
#### A. Automated Donation Intake (Lead Gen)
*   **Multi-Turn Bot:** A conversational interface that guides donors through a 3-4 turn process:
    1. Initial Greeting/Lead Capture.
    2. Food Description intake.
    3. Quantity/Weight estimation.
    4. Pickup window confirmation.
*   **Smart Categorization:** Uses an LLM (Gemini) to convert natural language descriptions into structured categories (e.g., "leftover chicken" -> `Prepared Meals`).
*   **Auto-Task Creation:** Once the conversation is complete, a new task is automatically injected into the Supabase database.

#### B. Proactive Volunteer Dispatch
*   **Proximity Alerts:** When a new task is created, the system identifies the nearest active volunteers.
*   **WhatsApp Push:** Sends a template message to drivers: "Hi Alice, 30lbs of Prepared Meals available 1.2km away. Claim here: [Link]".

#### C. Donor Impact Loop
*   **Automated Gratitude:** Upon task completion by a driver, the donor receives an instant WhatsApp update.
*   **Impact Metrics:** "Your 30lb donation was delivered! You just helped provide ~25 meals."

#### D. Live "On-the-Ground" Support
*   **Escalation:** A "Help" trigger in the CLI/WhatsApp that connects the user to a live Replate dispatcher.

## 4. Technical Requirements

### 4.1 Backend Architecture
*   **Primary:** Remote Supabase (BaaS) for database, auth, and edge functions.
*   **Edge Functions:** TypeScript-based serverless functions to handle WhatsApp Webhooks and LLM calls.
*   **Intelligence:** Gemini API integration for unstructured -> structured data extraction.

### 4.2 Data Storage (Supabase)
*   **Drivers:** Profile info, coordinates, affiliate NPO.
*   **Tasks:** Pickup metadata, **food category**, **quantity (lbs)**, and status.
*   **WhatsApp Sessions:** State machine table to track multi-turn conversation progress (`phone_number`, `current_state`, `temp_json_data`).

### 4.3 Communication Layer
*   **Inbound:** Meta/WhatsApp Webhooks -> Supabase Edge Functions.
*   **Outbound:** Supabase Database Triggers -> WhatsApp Template API.

## 5. Environment Management
*   `REPLATE_BACKEND`: Toggle between `supabase` and legacy `mock`.
*   `WHATSAPP_API_KEY` & `GEMINI_API_KEY`: Required for multi-channel features.

## 6. Future Roadmap
*   **Route Optimization:** Dynamic multi-stop routing for drivers claiming >1 task.
*   **Supabase Storage:** Real photo uploads from CLI and WhatsApp.
*   **Admin Dashboard:** Web-based view of the real-time logistics map.
