"""
Seed data for the dummy backend.
Includes drivers, partners, and tasks.
"""

DRIVERS = [
    {
        "id": 1,
        "email": "alice@example.com",
        "password_hash": "pbkdf2:sha256:600000$mock$...",  # Password1
        "first_name": "Alice",
        "last_name": "Volunteer",
        "phone": "4155550123",
        "partner_id": 1,
        "lat": 37.7749, "lon": -122.4194,  # San Francisco
    }
]

PARTNERS = [
    {"id": 1, "name": "SF-Marin Food Bank", "active": True},
    {"id": 2, "name": "Glide Memorial Kitchen", "active": True},
    {"id": 3, "name": "St. Anthony Foundation", "active": True},
]

TASKS = [
    {
        "id": 101,
        "encrypted_id": "enc_abc123",
        "date": "2026-04-18",
        "start_time": "10:00",
        "end_time": "11:00",
        "donor_name": "Google Cafeteria",
        "address": {"street": "1600 Amphitheatre Pkwy", "city": "Mountain View", "state": "CA", "zip": "94043"},
        "lat": 37.4220, "lon": -122.0841,
        "contact_name": "Jane Smith",
        "contact_phone": "6505550100",
        "contact_email": "jane@google.com",
        "food_description": "Mixed entrees",
        "category": "Prepared Meals",
        "tray_type": "full",
        "tray_count": 8,
        "quantity_lb": 120.0, # 8 * 15 lbs
        "access_instructions": "Check in at lobby reception",
        "status": "available",
        "driver_id": None,
    },
    {
        "id": 102,
        "encrypted_id": "enc_def456",
        "date": "2026-04-18",
        "start_time": "14:00",
        "end_time": "15:30",
        "donor_name": "LinkedIn Café",
        "address": {"street": "222 2nd St", "city": "San Francisco", "state": "CA", "zip": "94105"},
        "lat": 37.7877, "lon": -122.3974,
        "contact_name": "Mike Jones",
        "contact_phone": "4155550200",
        "contact_email": "mike@linkedin.com",
        "food_description": "Assorted salads",
        "category": "Produce",
        "tray_type": "half",
        "tray_count": 4,
        "quantity_lb": 28.0, # 4 * 7 lbs
        "access_instructions": "Loading dock on 2nd St",
        "status": "available",
        "driver_id": None,
    }
]
