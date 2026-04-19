import os
from typing import Any, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

URL: str = os.environ.get("SUPABASE_URL", "")
KEY: str = os.environ.get("SUPABASE_ANON_KEY", "")

if not URL or not KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")

supabase: Client = create_client(URL, KEY)

# ── Exceptions ─────────────────────────────────────────────────────────────────

class ApiError(Exception):
    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status

class AuthError(ApiError):
    pass

class NotFoundError(ApiError):
    pass

class ConflictError(ApiError):
    pass

class ValidationError(ApiError):
    def __init__(self, message: str, errors: Optional[list] = None):
        super().__init__(message)
        self.errors = errors or [message]

# ── Supabase Native Methods ────────────────────────────────────────────────────

def get_partners() -> List[dict]:
    res = supabase.table("partners").select("*").eq("active", True).execute()
    return res.data

def get_available_tasks(date_str: str) -> List[dict]:
    res = supabase.table("tasks").select("*").eq("date", date_str).eq("status", "available").execute()
    return res.data

def get_my_tasks(driver_id: str) -> List[dict]:
    res = supabase.table("tasks").select("*").eq("driver_id", driver_id).execute()
    return res.data

def claim_task(encrypted_id: str, driver_id: str) -> dict:
    """
    Claim a task atomically to prevent race conditions.
    This uses a conditional update: only update if the status is 'available'.
    """
    res = supabase.table("tasks").update({
        "status": "claimed",
        "driver_id": driver_id
    }).eq("encrypted_id", encrypted_id).eq("status", "available").execute()
    
    # If no rows were updated, it means the task was either not found 
    # or was already claimed by someone else.
    if not res.data:
        raise ConflictError("Task is no longer available or already claimed.")
    
    return res.data[0]

def complete_task(task_id: int, driver_id: str, details: dict) -> dict:
    res = supabase.table("tasks").update({
        "status": details.get("outcome", "completed"),
        "completion_details": details
    }).eq("id", task_id).eq("driver_id", driver_id).execute()
    
    if not res.data:
        raise ApiError("Failed to complete task")
    return res.data[0]

# ──────────────────────────────────────────────────────────────────────────────
# DEMO ONLY AUTHENTICATION
# ──────────────────────────────────────────────────────────────────────────────
# WARNING: The functions below are for PROTOTYPE DEMONSTRATION ONLY.
# 1. They DO NOT verify passwords (they lookup by email only).
# 2. They return a HARDCODED mock token instead of a real Supabase JWT.
# 3. In a production app, use supabase.auth.sign_in_with_password()
#    and supabase.auth.sign_up() to leverage real identity management.
# ──────────────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> dict:
    # DEMO ONLY: Basic password verification for seeded accounts
    # In a production app, use supabase.auth.sign_in_with_password()
    res = supabase.table("drivers").select("*").eq("email", email.lower()).execute()
    if not res.data:
        raise AuthError("Invalid email or password")
    
    driver = res.data[0]
    
    # Check against the standard demo password
    if password != "Password1":
        raise AuthError("Invalid email or password")
    
    return {
        "driver": driver, 
        "token": "supabase_session_active_DEMO_ONLY"
    }

def signup(data: dict) -> dict:
    # DEMO ONLY: Password is removed and NOT saved or verified
    clean_data = {k: v for k, v in data.items() if k != "password"}
    res = supabase.table("drivers").insert(clean_data).execute()
    if not res.data:
        raise ValidationError("Signup failed")
    
    return {
        "driver": res.data[0], 
        "token": "supabase_session_active_DEMO_ONLY"
    }

# ──────────────────────────────────────────────────────────────────────────────

def update_driver(driver_id: str, updates: dict) -> dict:
    res = supabase.table("drivers").update(updates).eq("id", driver_id).execute()
    if not res.data:
        raise ApiError("Failed to update driver")
    return res.data[0]

# ── Old REST compatibility ─────────────────────────────────────────────────────

def post(path: str, json: dict = None, token: Optional[str] = None) -> Any:
    if path == "/api/drivers/login": return login(json.get("email"), json.get("password"))
    if path == "/api/drivers": return signup(json)
    raise ApiError(f"POST {path} not implemented")

def get(path: str, **kwargs) -> Any:
    if path == "/api/partners": return get_partners()
    raise ApiError(f"GET {path} not implemented")
