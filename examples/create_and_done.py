"""Create a task interactively, schedule it, then mark it done on keypress."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from akiflow import Akiflow

TOKEN_FILE = Path(__file__).parent / ".tokens.json"

# --- authenticate -----------------------------------------------------------
if TOKEN_FILE.exists():
    tokens = json.loads(TOKEN_FILE.read_text())
    client = Akiflow(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        verify_ssl=False
    )
    print("Authenticated from saved tokens")
else:
    email = input("Email: ").strip()
    client = Akiflow(email=email, verify_ssl=False)
    print("Authenticated via OTP")

# --- create task -------------------------------------------------------------
name = input("\nTask name (enter for 'SDK demo task'): ").strip() or "SDK demo task"
task = client.task.create(name)
print(f"\nCreated task: {task['id']} — {task['title']}")

input("\nPress Enter to schedule...")
# --- schedule for 30 min from now --------------------------------------------
start = datetime.now(timezone.utc) + timedelta(minutes=30)
task = client.task.update(
    task["id"],
    date=start.strftime("%Y-%m-%d"),
    datetime_=start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    duration=1800,
    status=2,
)
print(f"Scheduled for {start.strftime('%H:%M')} UTC (30 min from now)")

# --- wait, then mark done ----------------------------------------------------
input("\nPress Enter to mark done...")
task = client.task.done(task["id"])
print(f"Done! ✓  {task['title']}")

# --- delete ------------------------------------------------------------------
input("\nPress Enter to delete the task...")
client.task.delete(task["id"])
print(f"Deleted: {task['title']}")

# --- persist tokens ----------------------------------------------------------
TOKEN_FILE.write_text(
    json.dumps(
        {
            "access_token": client.access_token,
            "refresh_token": client.refresh_token,
        }
    )
)
print("Tokens saved")
