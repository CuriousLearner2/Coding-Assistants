# Replate Python CLI

A terminal-based application for food rescue volunteer drivers.

## Getting Started

### 1. Prerequisites
* Python 3.14+
* A Supabase account (free tier)

### 2. Installation
```bash
# Install dependencies
pip install -r requirements.txt
```

### 3. Backend Setup (Supabase)
The project now uses **Supabase** as its primary backend.

1. Create a project at [supabase.com](https://supabase.com).
2. Run the SQL schema provided in `seed_supabase.py` (see comments for the SQL block) in the Supabase SQL Editor.
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
```bash
python main.py
```

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
