"""
# Akiflow SDK

Unofficial Python SDK for the [Akiflow](https://akiflow.com) task management software.

## Quick Start

Install the SDK:
```bash
pip install akiflow
# or
uv add akiflow
```

```python
from akiflow import Akiflow

# Interactive login (prompts for email + 2FA code)
client = Akiflow()

# Or reuse saved tokens (no interactive prompt)
client = Akiflow(access_token="eyJ...", refresh_token="def50200...")

# Create a task in your inbox
task = client.task.create("Buy groceries")

# Schedule a task
task = client.task.create(
    "Team standup",
    date="2026-03-27",
    datetime_="2026-03-27T09:00:00.000Z",
    duration=1800,
)

# Update, complete, or delete
client.task.update(task["id"], title="Team standup (moved)")
client.task.done(task["id"])
client.task.delete(task["id"])
```

## Authentication

Akiflow uses **passwordless email + OTP** authentication. On first use,
pass your `email` to trigger the interactive flow. The client prints
`access_token` and `refresh_token` after success — save them for reuse.

The **access token** expires in 30 minutes, but the **refresh token** is
long-lived (~13 months). The client auto-refreshes on 401, so passing just
a `refresh_token` is enough for persistent scripts.

## Debugging

Pass `debug=True` to print every request and response:

```python
client = Akiflow(email="you@example.com", debug=True)  # or omit email to be prompted

```

Pass `verify_ssl=False` to disable SSL verification (useful with Proxyman/Charles):

```python
client = Akiflow(access_token="...", verify_ssl=False)
```
"""

from .client import Akiflow
from .exceptions import AkiflowError, APIError, AuthError, TokenExpiredError
from .label import Label
from .task import Task

__all__ = ["Akiflow", "Label", "Task", "AkiflowError", "APIError", "AuthError", "TokenExpiredError"]
