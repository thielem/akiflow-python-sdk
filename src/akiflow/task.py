"""Task API — create, update, delete, and list Akiflow tasks."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import Akiflow


class TaskAPI:
    """Operations on Akiflow tasks, available as `client.task`.

    All mutations go through `PATCH /v5/tasks` (Akiflow uses upsert semantics).
    Deletion is a soft-delete via `trashed_at`.

    Example:
        ```python
        from akiflow import Akiflow

        client = Akiflow(refresh_token="def50200...")

        # Create
        task = client.task.create("Buy groceries")

        # Update
        client.task.update(task["id"], title="Buy organic groceries")

        # Mark done
        client.task.done(task["id"])

        # Delete
        client.task.delete(task["id"])

        # List all tasks
        result = client.task.list()
        for t in result["data"]:
            print(t["title"], t["done"])
        ```
    """

    def __init__(self, client: Akiflow):
        self._client = client

    def list(self, *, sync_token: str | None = None, limit: int = 2500) -> dict:
        """Fetch tasks, with optional incremental sync.

        Args:
            sync_token: Cursor from a previous `list()` response. Pass this
                to get only tasks changed since the last call.
            limit: Max tasks per page (default 2500).

        Returns:
            Dict with `data` (list of task dicts), `sync_token` (cursor for
            next call), and `has_next_page`.

        Example:
            ```python
            # Full sync
            result = client.task.list()
            tasks = result["data"]
            cursor = result["sync_token"]

            # Incremental sync (only changes since last call)
            result = client.task.list(sync_token=cursor)
            ```
        """
        params: dict[str, Any] = {"limit": str(limit)}
        if sync_token:
            params["sync_token"] = sync_token
        return self._client._get("/v5/tasks", params=params)

    def create(
        self,
        title: str,
        *,
        description: str | None = None,
        date: str | None = None,
        datetime_: str | None = None,
        datetime_tz: str | None = None,
        duration: int | None = None,
        due_date: str | None = None,
        priority: int | None = None,
        tags_ids: list[str] | None = None,
        label: str | None = None,
        list_id: str | None = None,
        section_id: str | None = None,
        links: list[str] | None = None,
        **extra: Any,
    ) -> dict:
        """Create a new task.

        By default, tasks land in the **inbox** (`status=1`). To schedule a
        task on a specific date/time, pass `date` and `datetime_`.

        Args:
            title: Task title.
            description: HTML description body.
            date: Planned date (`"2026-03-27"`).
            datetime_: Planned datetime in UTC (`"2026-03-27T09:00:00.000Z"`).
            datetime_tz: Timezone for display (default `"Europe/Zurich"`).
            duration: Duration in seconds (e.g. `1800` for 30 min).
            due_date: Hard due date (`"2026-03-28"`).
            priority: Priority level.
            tags_ids: List of tag UUIDs.
            label: Label/project name **or** UUID. Resolved automatically
                via `client.label.resolve_id()`. Takes precedence over `list_id`.
            list_id: Project/list UUID (use `label` for name-based lookup).
            section_id: Section within a project.
            links: List of URL strings.
            **extra: Additional fields passed directly to the API.

        Returns:
            The created task dict as returned by the API.

        Example:
            ```python
            # Inbox task
            task = client.task.create("Buy groceries")

            # Task assigned to a label by name
            task = client.task.create("Review PR", label="Work")

            # Scheduled task with duration
            task = client.task.create(
                "Team standup",
                date="2026-03-27",
                datetime_="2026-03-27T09:00:00.000Z",
                duration=1800,
            )
            ```
        """
        if label is not None:
            list_id = self._client.label.resolve_id(label)

        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        task_id = str(uuid.uuid4())
        sorting = int(datetime.now(timezone.utc).timestamp() * 1000)

        task: dict[str, Any] = {
            "id": task_id,
            "title": title,
            "description": description,
            "status": 1,
            "done": False,
            "done_at": None,
            "date": date,
            "datetime": datetime_,
            "datetime_tz": datetime_tz or "Europe/Zurich",
            "original_date": None,
            "original_datetime": None,
            "duration": duration,
            "due_date": due_date,
            "priority": priority,
            "sorting": sorting,
            "sorting_label": sorting,
            "tags_ids": tags_ids,
            "links": links or [],
            "listId": list_id,
            "section_id": section_id,
            "calendar_id": None,
            "time_slot_id": None,
            "recurring_id": None,
            "recurrence": None,
            "recurrence_version": None,
            "plan_unit": None,
            "plan_period": None,
            "origin": None,
            "connector_id": None,
            "origin_id": None,
            "origin_account_id": None,
            "doc": None,
            "content": None,
            "data": {},
            "search_text": "",
            "trashed_at": None,
            "deleted_at": None,
            "global_created_at": now,
            "global_updated_at": now,
            "global_list_id_updated_at": now if list_id else None,
            "global_tags_ids_updated_at": None,
            **extra,
        }

        resp = self._client._patch("/v5/tasks", json=[task])
        # Return the single created task
        if resp.get("data"):
            return resp["data"][0]
        return resp

    def update(self, task_id: str, **fields: Any) -> dict:
        """Update a task by ID.

        Only pass the fields you want to change. The `global_updated_at`
        timestamp is set automatically.

        Args:
            task_id: UUID of the task to update.
            **fields: Any task fields to update. Use `label` for name-based
                project lookup, `list_id` for UUID-based, and `datetime_`
                for the datetime field.

        Returns:
            The updated task dict.

        Example:
            ```python
            # Rename
            client.task.update(task_id, title="New title")

            # Assign to a label by name
            client.task.update(task_id, label="Work")

            # Reschedule
            client.task.update(
                task_id,
                date="2026-04-01",
                datetime_="2026-04-01T14:00:00.000Z",
            )
            ```
        """
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload: dict[str, Any] = {
            "id": task_id,
            "global_updated_at": now,
        }

        # Resolve label name/UUID -> listId
        if "label" in fields:
            label = fields.pop("label")
            if label is not None:
                fields["list_id"] = self._client.label.resolve_id(label)
            else:
                fields["list_id"] = None

        # Map python-friendly names to API names
        if "list_id" in fields:
            payload["listId"] = fields.pop("list_id")
            payload["global_list_id_updated_at"] = now
        if "datetime_" in fields:
            payload["datetime"] = fields.pop("datetime_")

        payload.update(fields)

        resp = self._client._patch("/v5/tasks", json=[payload])
        if resp.get("data"):
            return resp["data"][0]
        return resp

    def delete(self, task_id: str) -> dict:
        """Soft-delete a task.

        Sets `trashed_at` to the current time. The task can still be
        recovered in Akiflow's trash.

        Args:
            task_id: UUID of the task to delete.

        Returns:
            The updated task dict with `trashed_at` set.

        Example:
            ```python
            client.task.delete("59442bbd-a57d-464f-9fa2-2cb9678379ee")
            ```
        """
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload = {
            "id": task_id,
            "status": 10,
            "trashed_at": now,
            "global_updated_at": now,
        }
        resp = self._client._patch("/v5/tasks", json=[payload])
        if resp.get("data"):
            return resp["data"][0]
        return resp

    def done(self, task_id: str, *, date: str | None = None) -> dict:
        """Mark a task as done.

        Args:
            task_id: UUID of the task to complete.
            date: Date in ``YYYY-MM-DD`` format. Defaults to today.
                A date is required for the task to appear in Akiflow's
                done list.

        Returns:
            The updated task dict with `done=True`.

        Example:
            ```python
            client.task.done("59442bbd-a57d-464f-9fa2-2cb9678379ee")
            client.task.done(task_id, date="2026-03-20")
            ```
        """
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.update(task_id, done=True, done_at=now, date=date, status=2)
