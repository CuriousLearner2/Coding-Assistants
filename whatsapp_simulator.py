import os
import sys
import json
import argparse
import re
from datetime import date
from dotenv import load_dotenv
from supabase import create_client, Client
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Load environment
load_dotenv()

# Config
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") 
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
MOCK_AI = os.environ.get("MOCK_AI", "false").lower() == "true"

if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_KEY]):
    print("Error: Missing SUPABASE or GEMINI credentials in .env")
    sys.exit(1)

# Init Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GEMINI_KEY)

# ── Gemini Extraction Logic ───────────────────────────────────────────────────

def extract_donation_details_mock(text: str):
    """Local regex-based extraction to save API quota."""
    # Try to find a number
    nums = re.findall(r"\d+", text)
    qty = float(nums[0]) if nums else 5.0
    
    # Simple category mapping
    text_lower = text.lower()
    category = "Pantry"
    if any(w in text_lower for w in ["pasta", "chicken", "meal", "tray"]): category = "Prepared Meals"
    elif any(w in text_lower for w in ["apple", "veg", "fruit", "produce"]): category = "Produce"
    elif any(w in text_lower for w in ["bread", "donut", "pastry", "cake"]): category = "Bakery"
    
    return {
        "category": category,
        "quantity_lb": qty,
        "food_description": text[:30],
        "item_list": f"- {text}",
        "requires_review": True
    }

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def _call_gemini_api(text: str):
    prompt = f"""
    Return ONLY a JSON object:
    {{
      "category": "One of [Prepared Meals, Produce, Bakery, Dairy, Meat/Protein, Pantry]",
      "quantity_lb": estimated total weight in lbs (number),
      "food_description": "2-3 word summary",
      "item_list": "A bulleted list of everything mentioned"
    }}
    Input: "{text}"
    """
    
    response = client.models.generate_content(
        model='gemini-flash-latest',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
        ),
    )
    return json.loads(response.text)

def extract_donation_details(text: str):
    if MOCK_AI:
        print("  [MOCK AI] Using local extraction...")
        return extract_donation_details_mock(text)

    try:
        details = _call_gemini_api(text)
        # Ensure it's a dict, not a list
        if isinstance(details, list) and len(details) > 0:
            details = details[0]
        if not isinstance(details, dict):
            raise ValueError(f"AI returned {type(details)} instead of dict")
        return details
    except Exception as e:
        print(f"  [GEMINI ERROR] {e} - Falling back to local mock.")
        return extract_donation_details_mock(text)

def extract_window_details(text: str):
    """Use AI to parse natural language dates/times."""
    today = date.today().isoformat()
    prompt = f"""
    Today is {today}.
    Extract the pickup date and end time from this user input: "{text}"
    Return ONLY a JSON object:
    {{
      "date": "YYYY-MM-DD",
      "end_time": "HH:MM",
      "explanation": "short reason"
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json'),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"  [WINDOW AI ERROR] {e}")
        return {"date": today, "end_time": "17:00", "explanation": "Fallback to today 5pm"}

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
        }).execute()
        return "👋 Hi from Replate! We're ready to help you rescue that food. \n\nWhat kind of food do you have today? (e.g. '3 trays of pasta')"

    state = session["state"]
    temp_data = session["temp_data"]

    if state == "AWAITING_DESC":
        print(f"  [AI] Categorizing: '{message}'...")
        details = extract_donation_details(message)
        temp_data.update(details)
        
        supabase.table("whatsapp_sessions").update({
            "state": "AWAITING_REVIEW",
            "temp_data": temp_data
        }).eq("phone_number", phone).execute()
        
        return (
            f"Got it! Here is what I've captured:\n\n"
            f"📋 *Items:*\n{details.get('item_list')}\n"
            f"📦 *Category:* {details.get('category')}\n"
            f"⚖️ *Est. Weight:* {details.get('quantity_lb')} lbs\n\n"
            f"Does this look correct? (Reply 'Yes' or tell me what to change, e.g., 'It is 20 lbs')"
        )

    if state == "AWAITING_REVIEW":
        if msg_upper in ["YES", "Y", "OK", "LOOKS GOOD", "CORRECT"]:
            supabase.table("whatsapp_sessions").update({
                "state": "AWAITING_WINDOW"
            }).eq("phone_number", phone).execute()
            return "Great! When is the latest we can pick this up? (e.g. 'Until 5pm today')"
        
        # User is correcting the AI
        print(f"  [AI] Updating details based on correction: '{message}'...")
        prompt = f"The current data is {json.dumps(temp_data)}. Update it based on this user correction: \"{message}\". Return updated JSON."
        try:
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type='application/json'),
            )
            updated = json.loads(response.text)
            temp_data.update(updated)
            
            supabase.table("whatsapp_sessions").update({
                "temp_data": temp_data
            }).eq("phone_number", phone).execute()
            
            return (
                f"Updated! How about now?\n\n"
                f"📋 *Items:* {temp_data.get('item_list')}\n"
                f"📦 *Category:* {temp_data.get('category')}\n"
                f"⚖️ *Est. Weight:* {temp_data.get('quantity_lb')} lbs\n\n"
                f"Reply 'Yes' to confirm or tell me what else to change."
            )
        except Exception as e:
            print(f"  [CORRECTION ERROR] {e}")
            return "Sorry, I didn't quite catch that. Does the summary look okay now? (Reply 'Yes' or try describing the change again)"

    if state == "AWAITING_WINDOW":
        # Final Turn: Parse Date/Time
        print(f"  [AI] Parsing window: '{message}'...")
        window = extract_window_details(message)
        
        # 4. Inject Task into Supabase
        task_data = {
            "encrypted_id": f"wa_{phone[-4:]}_{os.urandom(2).hex()}",
            "date": window.get("date"),
            "start_time": "09:00",
            "end_time": window.get("end_time"),
            "donor_name": f"WhatsApp Donor ({phone[-4:]})",
            "address_json": {"street": "Unknown (WA Lead)", "city": "SF", "state": "CA", "zip": "94105"},
            "lat": 37.7749, "lon": -122.4194,
            "food_description": temp_data.get("food_description"),
            "category": temp_data.get("category"),
            "quantity_lb": float(temp_data.get("quantity_lb", 0)),
            "requires_review": temp_data.get("requires_review", False),
            "donor_whatsapp_id": phone,
            "status": "available"
        }
        
        supabase.table("tasks").insert(task_data).execute()
        
        # 5. Complete Session
        supabase.table("whatsapp_sessions").update({
            "state": "COMPLETED"
        }).eq("phone_number", phone).execute()
        
        return f"✅ Success! Your donation is live for {window.get('date')} until {window.get('end_time')}. A volunteer will be notified. Thank you! 🥕"

    if state == "COMPLETED":
        return "Your previous donation was logged. Type 'NEW' to report more surplus food!"

# ── Main Simulator Loop ────────────────────────────────────────────────────────

def run_simulator():
    parser = argparse.ArgumentParser(description="Replate WhatsApp Simulator")
    parser.add_argument("--phone", default="+14155550000", help="Donor phone number")
    args = parser.parse_args()

    print("═" * 50)
    print("  REPLATE WHATSAPP SIMULATOR (V1)")
    print(f"  Testing with Phone: {args.phone}")
    print(f"  Using Model: {'MOCK' if MOCK_AI else 'gemini-flash-latest'}")
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
