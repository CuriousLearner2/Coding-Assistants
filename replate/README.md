# Replate Python CLI

A terminal-based application for food rescue volunteer drivers.

## Getting Started

### 1. Prerequisites
* Python 3.11+
* A Supabase account (free tier)

### 2. Installation
```bash
# Install dependencies
pip install -r requirements.txt
```

### 3. Backend Setup (Supabase)
The project now uses **Supabase** as its primary backend.

1. Create a project at [supabase.com](https://supabase.com).
2. Run the SQL schema provided in `replate/setup_whatsapp_db.sql` in the Supabase SQL Editor.
3. Copy your project credentials into a `.env` file in the project root:
   ```text
   REPLATE_BACKEND=supabase
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key (only for seeding)
   ```
4. Seed your database with demo data:
   ```bash
   python seed_supabase.py
   ```

### 4. Running the App
The project includes a `bin` directory for easy invocation from any directory. 

**Setup (One-time):**
```bash
# Add to your PATH
echo 'export PATH="/Users/gautambiswas/Claude Code/replate/replate/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Commands:**
*   **`replate`**: Launches the main volunteer driver CLI.
*   **`replate-wa`**: Launches the WhatsApp Simulator to report new food donations.

---

## 🔄 End-to-End Workflow

1.  **Report Food**: Run `replate-wa`. Type `NEW` and follow the prompts to create a task.
2.  **Get Alerted**: If configured, the admin receives a WhatsApp notification when the task is claimed or rescued.
3.  **Claim Task**: Run `replate`. Log in as `alice@example.com` / `Password1`, browse "Available Pick-ups", and claim the task you just created.
4.  **Complete Task**: In `replate`, go to "My Tasks" and mark it as completed.

## ⚠️ Security Disclaimer
This application is a **functional prototype**. 
*   **Authentication is SIMULATED:** It performs manual lookups in the `drivers` table for demo purposes. 
*   **DO NOT USE THIS IN PRODUCTION:** It does not implement real JWT validation or secure password hashing.
*   See `ARCHITECTURE.md` for the production migration path.

## Deprecation Notice: Dummy Backend
The local Flask mock backend (`dummy_backend/`) is now **DEPRECATED**. It remains in the codebase for legacy testing purposes but is no longer the recommended way to run the application.

To force the app to use the deprecated backend, set the following in your `.env`:
```text
REPLATE_BACKEND=mock
```

## Testing
Run the test suite using `pytest`:
```bash
# Test against Supabase (requires valid .env)
pytest tests/integration/test_auth_flows.py -p tests.conftest_supabase

# Test against legacy mock (deprecated)
pytest
```
