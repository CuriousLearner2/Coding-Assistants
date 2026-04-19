# Product Requirements Document (PRD): Replate Python CLI

## 1. Executive Summary
Replate Python CLI is a terminal-based tool for volunteer drivers to facilitate food rescue operations. It bridges the gap between food donors (businesses) and recipients (NPOs).

## 2. Target Users
*   **Volunteer Drivers:** Individuals who pick up and deliver food donations.

## 3. Core Functionality
### 3.1 Authentication
*   Users must be able to log in and sign up.
*   Sessions must persist locally between runs.

### 3.2 Driver Onboarding
*   New users must select an NPO partner they are volunteering for.

### 3.3 Task Management
*   Browse available pick-ups for "Today" and "Tomorrow".
*   View detailed information (address, donor, food type, etc.).
*   Claim available pick-ups to be added to the user's task list.

### 3.4 Donation Logging
*   Log completion of a pick-up.
*   Record weight (lbs) and destination NPO.
*   Simulate/provide photo confirmation.

## 4. Technical Requirements
### 4.1 Backend Architecture
*   **Primary:** Remote Supabase (BaaS) for persistence and centralized data.
*   **Deprecated:** Local Flask Mock server for offline-only testing.

### 4.2 Data Storage
*   Drivers: UUID (primary key), email, profile details.
*   Tasks: Integer (id), encrypted_id, pickup window, status.
*   Partners: Integer (id), name.

### 4.3 Security
*   **Row-Level Security (RLS):** Policies must ensure users can only modify their own claimed tasks.
*   **API Protection:** All database communication must be via signed JWT/Anon keys.

### 4.4 Environment Management
*   Configuration via `.env` file.
*   Toggle between backends using `REPLATE_BACKEND`.

## 5. Future Roadmap
*   Real-time notifications for new nearby pick-ups.
*   Actual image upload to Supabase Storage.
*   Route optimization using Google Maps API.
