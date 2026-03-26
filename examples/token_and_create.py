"""Step 2: Load saved tokens, create another test task (no interactive auth)."""

import json
from pathlib import Path

from akiflow import Akiflow

TOKEN_FILE = Path(__file__).parent / ".tokens.json"

tokens = json.loads(TOKEN_FILE.read_text())
print("Loaded tokens from file")

client = Akiflow(
    access_token=tokens["access_token"],
    refresh_token=tokens["refresh_token"],
    verify_ssl=False
)

task = client.task.create("Test task from SDK (token reuse)")
print(f"\nCreated task: {task['id']} — {task['title']}")

# Update tokens file in case they were refreshed
TOKEN_FILE.write_text(
    json.dumps(
        {
            "access_token": client.access_token,
            "refresh_token": client.refresh_token,
        }
    )
)
print("Tokens updated")
