import client.api as api
from client import display as d


def run_donation(task: dict, session: dict):
    """Guide the driver through completing a pick-up."""
    d.header(f"Log Donation — {task['donor_name']}")
    d.blank()

    choice = d.menu(["Complete this pick-up", "Mark as missed (could not pick up)"], back_label="Cancel")
    if choice == "b":
        return

    if choice == "2":
        if d.confirm("Are you sure you want to mark this as missed?"):
            try:
                api.complete_task(task["id"], session["id"], {"outcome": "missed"})
                d.success("Task marked as missed.")
            except api.ApiError as e:
                d.error(str(e))
        return

    # Success path
    try:
        weight_str = input("  Enter total weight (lbs): ").strip()
        weight = float(weight_str)
    except (ValueError, KeyboardInterrupt, EOFError):
        d.error("Invalid weight.")
        return

    # In our Supabase demo, we'll just use the driver's default partner_id
    # or let them select if we had more logic. For now, keep it simple.
    partners = api.get_partners()
    partner_names = [p["name"] for p in partners]
    
    d.info("Where are you delivering this donation?")
    idx = d.choose("Select NPO partner", partner_names)
    if idx is None:
        return
    
    partner = partners[idx]

    d.info("Photo confirmation required.")
    input("  [Press Enter to simulate taking a photo] ")
    
    # Simulate a photo URL
    photo_url = f"https://storage.replate.org/mock/task_{task['id']}.jpg"

    try:
        api.complete_task(task["id"], session["id"], {
            "outcome": "completed",
            "weight": weight,
            "partner_id": partner["id"],
            "photo_url": photo_url
        })
        d.success("Donation logged! Thank you for your service.")
    except api.ApiError as e:
        d.error(str(e))
