import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
TO_PHONE = "+14152791719"

def send_test_message():
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": TO_PHONE,
        "type": "text",
        "text": {"body": "👋 Hello from Replate! This is a test message to verify your WhatsApp integration is working."}
    }
    
    print(f"Sending test message to {TO_PHONE}...")
    response = requests.post(url, json=payload, headers=headers)
    
    if response.ok:
        print("✅ Success! Message sent.")
        print(f"Response: {response.json()}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    send_test_message()
