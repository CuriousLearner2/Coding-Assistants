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

### 2.1 Backend Targeting
The project supports two testing modes via fixtures:
1. **Mock Backend (Standard):** Most integration tests in `tests/integration/` target the local Flask mock server. This is the default when running `pytest`.
2. **Supabase Integration (Cloud):** Critical auth and logistics logic can be validated against the live Supabase instance using the specialized fixtures in `tests/conftest_supabase.py`.

### 2.2 Input Mocking
Since the CLI relies on terminal interaction, all E2E and integration tests must use the `MockInput` utility to simulate user keystrokes and prevent `getpass` from hanging the test runner.

### 2.3 Regressions (Mock Backend)
Existing tests for the `dummy_backend` should be maintained to ensure the application logic remains sound even if the remote backend is unavailable.

---

## 4. End-to-End Testing (Simulator Flow)

To manually verify the full logistics loop, use the integrated CLI tools:

| Step | Command | Input | Expected Outcome |
|------|---------|-------|------------------|
| **1. Create** | `replate-wa` | `NEW`, `5 lbs apples`, `Yes`, `5pm today`, `Yes` | Task inserted into `tasks` table. |
| **2. Notify** | (Automatic) | - | WhatsApp alert sent to `ADMIN_PHONE`. |
| **3. Claim** | `replate` | Login `alice@example.com`, select Task, `Claim` | `status` changes to `claimed` in DB. |
| **4. Alert** | (Automatic) | - | WhatsApp alert: "Task claimed" sent to Admin/Donor. |
| **5. Finish**| `replate` | My Tasks, select Task, `Complete` | `status` changes to `completed` in DB. |

---

## 5. Automated Tests
Run the test suite using `pytest`:
```bash
# 1. Standard Mock Tests
pytest

# 2. Supabase Integration (requires valid .env)
# The -p flag loads the Supabase conftest plugin
pytest tests/integration/test_auth_flows.py -p tests.conftest_supabase
```
