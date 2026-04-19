import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# ──────────────────────────────────────────────────────────────────────────────
# ADMIN SEEDING SCRIPT
# ──────────────────────────────────────────────────────────────────────────────
# WARNING: This script uses the SERVICE_ROLE_KEY, which bypasses all Row Level
# Security (RLS) policies. This is intended ONLY for initial database setup
# and seeding. DO NOT use this key or this script's patterns in application code.
# ──────────────────────────────────────────────────────────────────────────────

# Add the project root to the path so we can import fixtures
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dummy_backend.fixtures import PARTNERS, TASKS

load_dotenv()

URL = os.environ.get("SUPABASE_URL")
# Use SERVICE_ROLE_KEY to bypass RLS for administrative seeding
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not URL or not KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    sys.exit(1)

# Initialize the admin client
supabase: Client = create_client(URL, KEY)

def seed():
    print(f"Connecting to {URL}...")

    # 1. Clear existing data
    # Robust delete: Use filter that captures all records regardless of type (UUID or Int)
    print("Cleaning existing data...")
    # .neq('id', -1) is a safe way to target every row in a table for these fixtures
    supabase.table("tasks").delete().neq("id", -1).execute()
    supabase.table("drivers").delete().neq("email", "MOCK_DELETE_ALL").execute()
    supabase.table("partners").delete().neq("id", -1).execute()

    # 2. Seed Partners
    print(f"Seeding {len(PARTNERS)} partners...")
    supabase.table("partners").insert(PARTNERS).execute()

    # 3. Seed Tasks
    # Transform fixture data to match Supabase schema (address -> address_json)
    formatted_tasks = []
    for t in TASKS:
        task = t.copy()
        task["address_json"] = task.pop("address")
        task["driver_id"] = None
        formatted_tasks.append(task)

    print(f"Seeding {len(formatted_tasks)} tasks...")
    supabase.table("tasks").insert(formatted_tasks).execute()

    print("\n✅ Database seeded successfully!")

if __name__ == "__main__":
    try:
        seed()
    except Exception as e:
        print(f"\n❌ Seeding failed: {str(e)}")
        sys.exit(1)
