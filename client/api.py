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
    Claim a task atomically and record the timestamp.
    """
    res = supabase.table("tasks").update({
        "status": "claimed",
        "driver_id": driver_id,
        "claimed_at": "now()"
    }).eq("encrypted_id", encrypted_id).eq("status", "available").execute()
    
    if not res.data:
        raise ConflictError("Task is no longer available or already claimed.")
    
    return res.data[0]

def release_task(task_id: int, driver_id: str) -> dict:
    """
    Release a claimed task back to the available pool.
    """
    res = supabase.table("tasks").update({
        "status": "available",
        "driver_id": None,
        "released_at": "now()"
    }).eq("id", task_id).eq("driver_id", driver_id).eq("status", "claimed").execute()
    
    if not res.data:
        raise ApiError("Failed to release task. It may have been completed already.")
    
    return res.data[0]

def complete_task(task_id: int, driver_id: str, details: dict) -> dict:
    res = supabase.table("tasks").update({
        "status": details.get("outcome", "completed"),
        "completion_details": details,
        "completed_at": "now()"
    }).eq("id", task_id).eq("driver_id", driver_id).execute()
    
    if not res.data:
        raise ApiError("Failed to complete task")
    return res.data[0]

# ──────────────────────────────────────────────────────────────────────────────
# ⚠️ SIMULATED IDENTITY LAYER (DEMO ONLY)
# ──────────────────────────────────────────────────────────────────────────────
# THE FUNCTIONS BELOW ARE NOT PRODUCTION-READY.
# 
# 1. AUTH BYPASS: They perform manual table lookups instead of using 
#    supabase.auth.sign_in_with_password().
# 2. NO JWT VALIDATION: They return a hardcoded string instead of a 
#    cryptographically signed Supabase JWT.
# 3. NO ENCRYPTION: Passwords are not hashed or verified against Auth providers.
#
# TO UPGRADE TO PRODUCTION: 
# Replace these with real Supabase Auth calls and enable email confirmation.
# ──────────────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> dict:
    """SIMULATED LOGIN: Table lookup only. DO NOT USE IN PRODUCTION."""
    res = supabase.table("drivers").select("*").eq("email", email.lower()).execute()
    if not res.data:
        raise AuthError("Invalid email or password")
    
    driver = res.data[0]
    
    # Check against the standard demo password
    if password != "Password1":
        raise AuthError("Invalid email or password")
    
    return {
        "driver": driver, 
        "token": "SIMULATED_SESSION_JWT_DO_NOT_USE_IN_PROD"
    }

def signup(data: dict) -> dict:
    """SIMULATED SIGNUP: Manual table insert only. DO NOT USE IN PRODUCTION."""
    # Remove password since we aren't using real Supabase Auth providers
    clean_data = {k: v for k, v in data.items() if k != "password"}
    res = supabase.table("drivers").insert(clean_data).execute()
    if not res.data:
        raise ValidationError("Signup failed")
    
    return {
        "driver": res.data[0], 
        "token": "SIMULATED_SESSION_JWT_DO_NOT_USE_IN_PROD"
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
