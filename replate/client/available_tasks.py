from datetime import date, timedelta

import client.api as api
from client import display as d


def _task_summary(task: dict) -> str:
    time_range = d.fmt_time_range(task.get("start_time"), task.get("end_time"))
    addr = d.fmt_address(task.get("address_json", {}))
    dist = d.fmt_distance(task.get("distance_km"))
    dist_str = f"  [{dist}]" if dist else ""
    
    review_prefix = "⚠️ [REVIEW] " if task.get("requires_review") else ""
    donor_name = f"{review_prefix}{task['donor_name']}"
    
    return f"{donor_name:<38}  {time_range}{dist_str}\n     {addr}"


def _show_task_detail(task: dict, session: dict) -> bool:
    """Display full task detail. Returns True if task was claimed."""
    d.header(f"Pick-up Detail — {task['donor_name']}")
    d.blank()
    if task.get("requires_review"):
        d.error("AI REVIEW REQUIRED: Details were extracted automatically.")
        d.info("  Please verify food type and quantity upon arrival.")
        d.blank()

    d.info(f"Date:      {d.fmt_date(task['date'])}")
    d.info(f"Time:      {d.fmt_time_range(task.get('start_time'), task.get('end_time'))}")
    d.blank()
    d.info(f"Location:  {task['donor_name']}")
    d.info(f"Address:   {d.fmt_address(task.get('address_json', {}))}")
    if task.get("access_instructions"):
        d.info(f"Access:    {task['access_instructions']}")
    d.blank()
    d.info(f"Contact:   {task.get('contact_name', '')}")
    d.info(f"Phone:     {task.get('contact_phone', '')}")
    d.info(f"Email:     {task.get('contact_email', '')}")
    d.blank()
    d.info(f"Food:      {task.get('food_description', '')}")
    
    if task.get("category"):
        d.info(f"Quantity:  {d.fmt_quantity(task.get('category'), task.get('quantity_lb', 0))}")
    else:
        d.info(f"Trays:     {d.fmt_tray(task.get('tray_type', ''), task.get('tray_count', 0))}")
    d.blank()

    choice = d.menu(["Claim this pick-up"], back_label="Back to list")
    if choice == "1":
        try:
            api.claim_task(task['encrypted_id'], session["id"])
            d.success("Pick-up claimed! It now appears in My Tasks.")
            return True
        except api.ConflictError:
            d.error("This pick-up was just claimed by another driver.")
        except api.ApiError as e:
            d.error(str(e))
    return False


def run_available_tasks(session: dict):
    today = date.today()
    selected_date = today

    while True:
        date_label = "Today" if selected_date == today else "Tomorrow"
        d.header(f"REPLATE — Available Pick-ups ({date_label})")
        d.blank()

        try:
            tasks = api.get_available_tasks(selected_date.isoformat())
        except api.ApiError as e:
            d.error(str(e))
            return

        if not tasks:
            d.info(f"No pick-ups available for {d.fmt_date(selected_date.isoformat())}.")
        else:
            for i, task in enumerate(tasks, 1):
                print(f"  {i:>2}. {_task_summary(task)}")
                d.blank()

        d.divider()
        options = ["Switch to Tomorrow" if selected_date == today else "Switch to Today"]
        if tasks:
            options.append("View pick-up details")
        choice = d.menu(options, back_label="Main menu")

        if choice == "b":
            return
        elif choice == "1":
            selected_date = today + timedelta(days=1) if selected_date == today else today
        elif choice == "2" and tasks:
            labels = [task["donor_name"] for task in tasks]
            idx = d.choose("Select a pick-up to view", labels)
            if idx is not None:
                claimed = _show_task_detail(tasks[idx], session)
                if claimed:
                    # Remove from list so display stays accurate
                    tasks.pop(idx)
        else:
            d.error("Invalid choice.")
