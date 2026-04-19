# Replate Python CLI — Test Plan

**Project:** Replate Python CLI  
**Primary Backend:** Remote Supabase (BaaS)  
**Secondary Backend (Deprecated):** Dummy in-memory mock server  
**Revision:** 2026-04-18 — Migrated to Supabase architecture

---

## 1. Architecture Under Test

```
replate/
├── client/
│   ├── api.py             # Unified API client (Supabase + Mock Toggle)
│   ├── auth.py            # Auth flows
│   ├── available_tasks.py # Browse/Claim
│   ├── my_tasks.py        # Active tasks
│   ├── donation.py        # Completion logging
│   ├── account.py         # Profile
│   └── session.py         # Persistence
├── dummy_backend/         # [DEPRECATED] Local Flask mock
├── tests/
│   ├── conftest.py        # Legacy fixtures (Mock)
│   ├── conftest_supabase.py # Supabase fixtures & input mocking
│   ├── integration/       # Logic validation (Mock + Supabase modes)
│   └── unit/              # Utility validation
├── seed_supabase.py       # Admin DB setup
└── main.py                # Entry point
```

---

## 2. Test Strategy

### 2.1 Supabase Integration Testing
Tests targeting the remote Supabase instance must:
1.  Verify authentication using the `alice_session` fixture.
2.  Validate that CRUD operations on `tasks` and `drivers` correctly reflect in the remote tables.
3.  Ensure RLS policies prevent unauthorized data access.

### 2.2 Input Mocking
Since the CLI relies on terminal interaction, all E2E and integration tests must use the `MockInput` utility to simulate user keystrokes and prevent `getpass` from hanging the test runner.

### 2.3 Regressions (Mock Backend)
Existing tests for the `dummy_backend` should be maintained to ensure the application logic remains sound even if the remote backend is unavailable.

---

## 3. Critical Validation Scenarios

| Feature | Scenario | Success Criteria |
|---------|----------|------------------|
| **Auth** | Login with valid credentials | Session saved to `~/.replate/session.json` |
| **Claim** | Claim already-claimed task | API returns `ConflictError` |
| **Tasks** | View Available Pick-ups | List matches remote Supabase `tasks` table |
| **Donation**| Log weight and NPO | Task status changes to `completed` in Supabase |
| **Seeding** | Run `seed_supabase.py` | Remote DB is cleared and re-populated |
