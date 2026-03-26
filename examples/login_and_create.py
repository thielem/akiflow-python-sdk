"""Step 1: Interactive login, create a test task, save tokens to file."""

import json
from pathlib import Path

from akiflow import Akiflow

TOKEN_FILE = Path(__file__).parent / ".tokens.json"

email = input("Email: ").strip()
client = Akiflow(email=email)

# Save tokens for reuse
TOKEN_FILE.write_text(
    json.dumps(
        {
            "access_token": client.access_token,
            "refresh_token": client.refresh_token,
        }
    )
)
print(f"\nTokens saved to {TOKEN_FILE}")

# Create a test task
task = client.task.create("Test task from SDK (interactive login)")
print(f"\nCreated task: {task['id']} — {task['title']}")
