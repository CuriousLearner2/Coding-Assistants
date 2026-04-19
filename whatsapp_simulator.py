import os
import sys
import json
import argparse
from datetime import date
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

# Load environment
load_dotenv()

# Config
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") 
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
    msg_upper = message.upper().strip()

    # 1. Handle Termination Commands
    if msg_upper in ["STOP", "CANCEL"]:
        supabase.table("whatsapp_sessions").delete().eq("phone_number", phone).execute()
        return "🛑 Session cancelled and deleted. Send 'NEW' to start again anytime."

    # 2. Get or Create Session
    res = supabase.table("whatsapp_sessions").select("*").eq("phone_number", phone).execute()
    session = res.data[0] if res.data else None
    
    # 3. Handle Reset / Initial Greet
    if not session or msg_upper in ["RESET", "NEW", "START"]:
        supabase.table("whatsapp_sessions").upsert({
            "phone_number": phone,
            "state": "AWAITING_DESC",
            "temp_data": {}
            # Omit updated_at to let DB handle it
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
            "temp_data": temp_data
        }).eq("phone_number", phone).execute()
        
        return f"Got it! {details.get('food_description')} ({details.get('category')}). \n\nWhen is the latest we can pick this up? (e.g. 'Until 5pm today')"

    if state == "AWAITING_WINDOW":
        # Final Turn
        temp_data["pickup_window"] = message
        
        # 4. Inject Task into Supabase
        task_data = {
            "encrypted_id": f"wa_{phone[-4:]}_{os.urandom(2).hex()}",
            "date": date.today().isoformat(), # Use current date
            "start_time": "12:00",
            "end_time": "17:00",
            "donor_name": f"WhatsApp Donor ({phone[-4:]})",
            "address_json": {"street": "Unknown (WA Lead)", "city": "SF", "state": "CA", "zip": "94105"},
            "lat": 37.7749, "lon": -122.4194,
            "food_description": temp_data.get("food_description"),
            "category": temp_data.get("category"),
            "quantity_lb": temp_data.get("quantity_lb"),
            "requires_review": temp_data.get("requires_review", False), # Propagate review flag
            "donor_whatsapp_id": phone,
            "status": "available"
        }
        
        supabase.table("tasks").insert(task_data).execute()
        
        # 5. Complete Session
        supabase.table("whatsapp_sessions").update({
            "state": "COMPLETED"
        }).eq("phone_number", phone).execute()
        
        return "✅ Success! Your donation is now live in our system. A volunteer will be notified shortly. Thank you! 🥕"

    if state == "COMPLETED":
        return "Your previous donation was logged. Type 'NEW' to report more surplus food!"

# ── Main Simulator Loop ────────────────────────────────────────────────────────

def run_simulator():
    parser = argparse.ArgumentParser(description="Replate WhatsApp Simulator")
    parser.add_argument("--phone", default="+14155550000", help="Donor phone number for testing concurrent sessions")
    args = parser.parse_args()

    print("═" * 50)
    print("  REPLATE WHATSAPP SIMULATOR (V1)")
    print(f"  Testing with Phone: {args.phone}")
    print("  Commands: 'RESET' to start over, 'STOP' to delete, 'EXIT' to quit.")
    print("═" * 50)
    
    while True:
        try:
            msg = input("\n[Donor]: ").strip()
            if msg.upper() == "EXIT": break
            if not msg: continue
            
            response = handle_message(args.phone, msg)
            print(f"\n[Bot]: {response}")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    run_simulator()
