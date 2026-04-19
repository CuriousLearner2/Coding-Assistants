import os
import sys
import json
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

# Load environment
load_dotenv()

# Config
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use admin key for simulator
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_KEY]):
    print("Error: Missing SUPABASE or GEMINI credentials in .env")
    sys.exit(1)

# Init Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

# ── Gemini Extraction Logic ───────────────────────────────────────────────────

def extract_donation_details(text: str):
    prompt = f"""
    You are a logistics coordinator for Replate, a food rescue nonprofit.
    Extract the following from the user's food description:
    1. Category: Exactly one of [Prepared Meals, Produce, Bakery, Dairy, Meat/Protein, Pantry]
    2. Quantity_LB: A numeric estimate of the weight in pounds.
    3. Food_Description: A clean, concise title for the donation.

    Input: "{text}"
    Output valid JSON only:
    """
    try:
        response = model.generate_content(prompt)
        # Handle potential markdown in response
        raw_json = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(raw_json)
    except Exception as e:
        print(f"  [GEMINI ERROR] {e}")
        return {
            "category": "Pantry", 
            "quantity_lb": 5.0, 
            "food_description": text[:50],
            "requires_review": True
        }

# ── State Machine Logic ────────────────────────────────────────────────────────

def handle_message(phone: str, message: str):
    # 1. Get or Create Session
    res = supabase.table("whatsapp_sessions").select("*").eq("phone_number", phone).execute()
    session = res.data[0] if res.data else None
    
    if not session or message.upper() in ["RESET", "NEW", "START"]:
        supabase.table("whatsapp_sessions").upsert({
            "phone_number": phone,
            "state": "AWAITING_DESC",
            "temp_data": {},
            "updated_at": "now()"
        }).execute()
        return "👋 Hi from Replate! We're ready to help you rescue that food. \n\nWhat kind of food do you have today? (e.g. '3 trays of pasta')"

    state = session["state"]
    temp_data = session["temp_data"]

    if state == "AWAITING_DESC":
        print(f"  [AI] Categorizing: '{message}'...")
        details = extract_donation_details(message)
        temp_data.update(details)
        
        supabase.table("whatsapp_sessions").update({
            "state": "AWAITING_WINDOW",
            "temp_data": temp_data,
            "updated_at": "now()"
        }).eq("phone_number", phone).execute()
        
        return f"Got it! {details.get('food_description')} ({details.get('category')}). \n\nWhen is the latest we can pick this up? (e.g. 'Until 5pm today')"

    if state == "AWAITING_WINDOW":
        # Final Turn
        temp_data["pickup_window"] = message
        
        # 2. Inject Task into Supabase
        task_data = {
            "encrypted_id": f"wa_{phone[-4:]}_{os.urandom(2).hex()}",
            "date": "2026-04-18", # In prod, parse date from window
            "start_time": "12:00",
            "end_time": "17:00",
            "donor_name": f"WhatsApp Donor ({phone[-4:]})",
            "address_json": {"street": "Unknown (WA Lead)", "city": "SF", "state": "CA", "zip": "94105"},
            "lat": 37.7749, "lon": -122.4194,
            "food_description": temp_data.get("food_description"),
            "category": temp_data.get("category"),
            "quantity_lb": temp_data.get("quantity_lb"),
            "donor_whatsapp_id": phone,
            "status": "available"
        }
        
        supabase.table("tasks").insert(task_data).execute()
        
        # 3. Complete Session
        supabase.table("whatsapp_sessions").update({
            "state": "COMPLETED",
            "updated_at": "now()"
        }).eq("phone_number", phone).execute()
        
        return "✅ Success! Your donation is now live in our system. A volunteer will be notified shortly. Thank you! 🥕"

    if state == "COMPLETED":
        return "Your previous donation was logged. Type 'NEW' to report more surplus food!"

# ── Main Simulator Loop ────────────────────────────────────────────────────────

def run_simulator():
    print("═" * 50)
    print("  REPLATE WHATSAPP SIMULATOR (V1)")
    print("  Type your messages below to test the bot.")
    print("  Commands: 'RESET' to start over, 'EXIT' to quit.")
    print("═" * 50)
    
    phone = "+14155550000" # Mock donor phone
    
    while True:
        try:
            msg = input("\n[Donor]: ").strip()
            if msg.upper() == "EXIT": break
            if not msg: continue
            
            response = handle_message(phone, msg)
            print(f"\n[Bot]: {response}")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    run_simulator()
