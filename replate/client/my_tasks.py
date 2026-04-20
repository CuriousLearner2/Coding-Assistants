import client.api as api
from client import display as d
from client.donation import run_donation


def _task_summary(task: dict) -> str:
    time_range = d.fmt_time_range(task.get("start_time"), task.get("end_time"))
    addr = d.fmt_address(task.get("address_json", {}))
    return f"{task['donor_name']:<28}  {time_range}\n     {addr}"


def run_my_tasks(session: dict):
    view = "claimed"  # 'claimed' (in progress) or 'completed/missed' (history)

    while True:
        view_label = "In Progress" if view == "claimed" else "History"
        d.header(f"REPLATE — My Tasks ({view_label})")
        d.blank()

        try:
            all_tasks = api.get_my_tasks(session["id"])
            if view == "claimed":
                tasks = [t for t in all_tasks if t["status"] == "claimed"]
            else:
                tasks = [t for t in all_tasks if t["status"] in ("completed", "missed")]
        except api.ApiError as e:
            d.error(str(e))
            return

        if not tasks:
            d.info(f"No tasks in {view_label.lower()}.")
        else:
            for i, task in enumerate(tasks, 1):
                print(f"  {i:>2}. {_task_summary(task)}")
                d.blank()

        d.divider()
        options = ["Switch to History" if view == "claimed" else "Switch to In Progress"]
        if tasks and view == "claimed":
            options.append("Complete a pick-up")
            options.append("Release pick-up (unclaim)")

        choice = d.menu(options, back_label="Main menu")

        if choice == "b":
            break
        elif choice == "1":
            view = "completed" if view == "claimed" else "claimed"
        elif choice == "2" and tasks and view == "claimed":
            labels = [task["donor_name"] for task in tasks]
            idx = d.choose("Select a pick-up to log", labels)
            if idx is not None:
                run_donation(tasks[idx], session)
        elif choice == "3" and tasks and view == "claimed":
            labels = [task["donor_name"] for task in tasks]
            idx = d.choose("Select a pick-up to release", labels)
            if idx is not None:
                task = tasks[idx]
                if d.confirm(f"Are you sure you want to release the pick-up from {task['donor_name']}?"):
                    try:
                        api.release_task(task["id"], session["id"])
                        d.success("Pick-up released. It is now available for other drivers.")
                        tasks.pop(idx)
                    except api.ApiError as e:
                        d.error(str(e))
        else:
            d.error("Invalid choice.")
