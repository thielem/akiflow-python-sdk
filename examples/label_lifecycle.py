"""End-to-end label + task lifecycle demo."""

import json
from pathlib import Path

from akiflow import Akiflow

TOKEN_FILE = Path(__file__).parent / ".tokens.json"

tokens = json.loads(TOKEN_FILE.read_text())
client = Akiflow(
    access_token=tokens["access_token"],
    refresh_token=tokens["refresh_token"],
    debug=True,
    verify_ssl=False,
)

# 1. Create label
label = client.label.create("sdk_test", color="palette-pink")
print(f"\n✅ Created label: {label['id']} — {label['title']}")
input("\nPress Enter to create a task in this label...")

# 2. Create task assigned to the label (by name)
task = client.task.create("sdk_test Task", label="sdk_test")
print(f"\n✅ Created task: {task['id']} — {task['title']} (listId={task['listId']})")
input("\nPress Enter to mark the task as done...")

# 3. Mark task done
task = client.task.done(task["id"])
print(f"\n✅ Task done: {task['done']} at {task['done_at']}")
input("\nPress Enter to rename the label...")

# 4. Rename label
label = client.label.update(label["id"], title="sdk_test_renamed")
print(f"\n✅ Renamed label: {label['title']}")
input("\nPress Enter to delete the label...")

# 5. Delete label
label = client.label.delete(label["id"])
print(f"\n✅ Deleted label: deleted_at={label['deleted_at']}")

# Save refreshed tokens
TOKEN_FILE.write_text(
    json.dumps(
        {
            "access_token": client.access_token,
            "refresh_token": client.refresh_token,
        }
    )
)
print("\nDone. Tokens updated.")
