import client.api as api
from client import display as d


def run_onboarding(session: dict) -> dict | None:
    """One-time setup for new drivers to choose their NPO partner."""
    d.header("REPLATE — Choose Your NPO Partner")
    d.blank()
    d.info("Please select the organization you will be volunteering with.")
    d.info("This can be changed later in your account settings.")
    d.blank()

    try:
        partners = api.get_partners()
    except api.ApiError as e:
        d.error(f"Could not fetch partners: {e}")
        return None

    if not partners:
        d.error("No NPO partners are currently available. Contact Replate staff.")
        return None

    names = [p["name"] for p in partners]
    idx = d.choose("Select your NPO partner", names)
    
    if idx is None:
        return None

    partner = partners[idx]
    
    try:
        updated_driver = api.update_driver(session["id"], {"partner_id": partner["id"]})
        d.success(f"Welcome aboard! You are now linked with {partner['name']}.")
        
        # Update local session
        new_session = {**session, **updated_driver}
        from client.session import save_session
        save_session(new_session)
        return new_session
    except api.ApiError as e:
        d.error(f"Failed to save choice: {e}")
        return None
