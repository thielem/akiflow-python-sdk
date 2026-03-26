"""Label API — create, update, delete, and list Akiflow labels (projects)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import Akiflow


class Label:
    """Operations on Akiflow labels/projects, available as `client.label`.

    Labels are what Akiflow calls "projects" in the UI. Tasks reference
    labels via their `listId` field. Labels can be organized into folders
    using `parent_id` and `type="folder"`.

    Example:
        ```python
        from akiflow import Akiflow

        client = Akiflow(refresh_token="def50200...")

        # Create a label
        label = client.label.create("My Project", color="palette-green")

        # List all labels
        result = client.label.list()
        for lb in result["data"]:
            print(lb["title"], lb["id"])

        # Find label ID by name
        label_id = client.label.get_id("My Project")

        # Update
        client.label.update(label["id"], title="Renamed Project")

        # Delete
        client.label.delete(label["id"])
        ```
    """

    # Cache of name -> id, populated on first lookup
    _name_cache: dict[str, str] | None = None

    def __init__(self, client: Akiflow):
        self._client = client
        self._name_cache = None

    def list(self, *, sync_token: str | None = None, limit: int = 2500) -> dict:
        """Fetch labels, with optional incremental sync.

        Args:
            sync_token: Cursor from a previous `list()` response.
            limit: Max labels per page (default 2500).

        Returns:
            Dict with `data` (list of label dicts), `sync_token`, and
            `has_next_page`.
        """
        params: dict[str, Any] = {"limit": str(limit)}
        if sync_token:
            params["sync_token"] = sync_token
        return self._client._get("/v5/labels", params=params)

    def create(
        self,
        title: str,
        *,
        color: str | None = None,
        icon: str | None = None,
        parent_id: str | None = None,
        type: str | None = None,
        **extra: Any,
    ) -> dict:
        """Create a new label.

        Args:
            title: Label name.
            color: Color palette name (e.g. `"palette-green"`, `"palette-pink"`).
            icon: Emoji icon.
            parent_id: UUID of a folder label to nest under.
            type: Set to `"folder"` to create a folder, or `None` for a label.
            **extra: Additional fields passed directly to the API.

        Returns:
            The created label dict.

        Example:
            ```python
            label = client.label.create("Work", color="palette-cobalt")
            folder = client.label.create("Area", type="folder")
            nested = client.label.create("Sub-project", parent_id=folder["id"])
            ```
        """
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        label_id = str(uuid.uuid4())
        sorting = int(datetime.now(timezone.utc).timestamp() * 1000)

        label: dict[str, Any] = {
            "id": label_id,
            "title": title,
            "color": color,
            "icon": icon,
            "sorting": sorting,
            "parent_id": parent_id,
            "type": type,
            "data": {},
            "global_created_at": now,
            "global_updated_at": now,
            "deleted_at": None,
            **extra,
        }

        resp = self._client._patch("/v5/labels", json=[label])
        created = resp["data"][0] if resp.get("data") else resp
        # Invalidate name cache
        self._name_cache = None
        return created

    def update(self, label_id: str, **fields: Any) -> dict:
        """Update a label by ID.

        Args:
            label_id: UUID of the label to update.
            **fields: Any label fields to update (e.g. `title`, `color`, `icon`).

        Returns:
            The updated label dict.

        Example:
            ```python
            client.label.update(label_id, title="New Name", color="palette-red")
            ```
        """
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload: dict[str, Any] = {
            "id": label_id,
            "global_updated_at": now,
        }
        payload.update(fields)

        resp = self._client._patch("/v5/labels", json=[payload])
        self._name_cache = None
        if resp.get("data"):
            return resp["data"][0]
        return resp

    def delete(self, label_id: str) -> dict:
        """Soft-delete a label.

        Args:
            label_id: UUID of the label to delete.

        Returns:
            The updated label dict with `deleted_at` set.

        Example:
            ```python
            client.label.delete("d7f7c026-bd8a-4c3a-8c16-d9677ee959e9")
            ```
        """
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload: dict[str, Any] = {
            "id": label_id,
            "title": None,
            "color": None,
            "sorting": None,
            "icon": None,
            "parent_id": None,
            "type": None,
            "data": {},
            "deleted_at": now,
            "global_updated_at": now,
        }
        resp = self._client._patch("/v5/labels", json=[payload])
        self._name_cache = None
        if resp.get("data"):
            return resp["data"][0]
        return resp

    def _build_name_cache(self) -> dict[str, str]:
        """Fetch all labels and build a lowercase name -> id mapping."""
        result = self.list()
        cache: dict[str, str] = {}
        for lb in result.get("data", []):
            if lb.get("title") and not lb.get("deleted_at"):
                cache[lb["title"].lower()] = lb["id"]
        return cache

    def get_id(self, name: str) -> str | None:
        """Resolve a label name to its UUID.

        Case-insensitive. Returns `None` if no label matches.

        Args:
            name: Label name to look up.

        Returns:
            Label UUID, or `None` if not found.

        Example:
            ```python
            label_id = client.label.get_id("Work")
            ```
        """
        if self._name_cache is None:
            self._name_cache = self._build_name_cache()
        return self._name_cache.get(name.lower())

    def resolve_id(self, label: str) -> str:
        """Resolve a label name or UUID to a UUID.

        If `label` looks like a UUID, returns it as-is. Otherwise, looks
        it up by name (case-insensitive).

        Args:
            label: Label UUID or name.

        Returns:
            Label UUID.

        Raises:
            ValueError: If the name doesn't match any label.

        Example:
            ```python
            # Both return the same UUID:
            client.label.resolve_id("d7f7c026-bd8a-4c3a-8c16-d9677ee959e9")
            client.label.resolve_id("Work")
            ```
        """
        try:
            uuid.UUID(label)
            return label
        except ValueError:
            pass

        label_id = self.get_id(label)
        if label_id is None:
            raise ValueError(f"No label found with name: {label!r}")
        return label_id
