# Akiflow Python SDK

> **Work in Progress:** This project is under active development and is not yet ready for production use.

> **Disclaimer:** This project is **not affiliated with, endorsed by, or associated with Akiflow** in any way. It is an unofficial, community-built SDK. The underlying API is undocumented and **may change at any time without notice**, which could break this library. Use at your own risk.

A lightweight Python SDK for the Akiflow task management API. Built on `httpx` with full type annotations.

## Status

This is an early proof of concept. Currently implemented:

- **Tasks** — create, list, update, mark done, delete
- **Labels** — create, list, update, delete, lookup by name

Other Akiflow features are not yet covered.

## Installation

Requires Python 3.13+.

```bash
pip install akiflow
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install akiflow
```

## Quick Start

### Interactive Login

> **Note:** This SDK only supports Akiflow's passwordless email + OTP login. Other authentication methods (e.g., Google SSO) have not been tested and may not work.

The SDK uses Akiflow's passwordless email + OTP flow:

```python
from akiflow import Akiflow

client = Akiflow(email="you@example.com")  # prompts for OTP code
```

### Reusing Tokens

Save and reuse tokens to avoid logging in every time:

```python
from akiflow import Akiflow

client = Akiflow(
    access_token="eyJ...",
    refresh_token="def50200...",
)
```

The client automatically refreshes expired access tokens using the refresh token.

### Tasks

```python
# Create a task
task = client.task.create("Buy groceries")

# Create a scheduled task with priority
task = client.task.create(
    "Team meeting",
    datetime="2025-01-15T10:00:00",
    duration=3600,
    priority=2,
)

# List tasks
tasks = client.task.list()

# Mark done
client.task.done(task["id"])

# Delete
client.task.delete(task["id"])
```

### Labels

```python
# Create a label
label = client.label.create("Work", color="#FF0000")

# List labels
labels = client.label.list()

# Look up label ID by name
label_id = client.label.get_id("Work")

# Delete
client.label.delete(label_id)
```

## Debugging

Enable debug mode to print all HTTP requests and responses:

```python
client = Akiflow(email="you@example.com", debug=True)
```

To bypass SSL verification (useful with proxy tools like Proxyman or Charles):

```python
client = Akiflow(email="you@example.com", verify_ssl=False)
```

## Examples

See the [`examples/`](examples/) directory for complete working scripts:

- `login_and_create.py` — Interactive login with token persistence
- `token_and_create.py` — Reuse saved tokens
- `create_and_done.py` — Task lifecycle (create, done, delete)
- `label_lifecycle.py` — Label CRUD operations

## License

MIT
