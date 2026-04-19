import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Add the project root to the path so we can import fixtures
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dummy_backend.fixtures import PARTNERS, TASKS

load_dotenv()

URL = os.environ.get("SUPABASE_URL")
# Use SERVICE_ROLE_KEY to bypass RLS for seeding
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not URL or not KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    sys.exit(1)

supabase: Client = create_client(URL, KEY)

def seed():
    print(f"Connecting to {URL}...")

    # 1. Clear existing data (optional, but good for a clean demo)
    print("Cleaning existing data...")
    supabase.table("tasks").delete().neq("id", 0).execute()
    supabase.table("drivers").delete().neq("email", "").execute()
    supabase.table("partners").delete().neq("id", 0).execute()

    # 2. Seed Partners
    print(f"Seeding {len(PARTNERS)} partners...")
    supabase.table("partners").insert(PARTNERS).execute()

    # 3. Seed Tasks
    # We need to transform the task data slightly (address -> address_json)
    formatted_tasks = []
    for t in TASKS:
        task = t.copy()
        # Move nested address to JSON field
        task["address_json"] = task.pop("address")
        # Ensure driver_id is None (Supabase NULL)
        task["driver_id"] = None
        formatted_tasks.append(task)

    print(f"Seeding {len(formatted_tasks)} tasks...")
    supabase.table("tasks").insert(formatted_tasks).execute()

    print("\n✅ Database seeded successfully!")

if __name__ == "__main__":
    seed()
