from __future__ import annotations

import json
from datetime import datetime

import httpx

from akiflow import Akiflow


def _json_response(payload: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=payload)


def _make_client(handler, **kwargs) -> Akiflow:
    client = Akiflow(**kwargs)
    client._http.close()
    client._http = httpx.Client(
        base_url="https://api.akiflow.com",
        headers=client._auth_headers(),
        transport=httpx.MockTransport(handler),
    )
    return client


def test_interactive_login_and_create_task(monkeypatch):
    monkeypatch.setattr(
        "akiflow.client.interactive_login",
        lambda email, client_id, verify_ssl: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "client_id": client_id,
        },
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == "/v5/tasks"
        payload = json.loads(request.content)
        assert payload[0]["title"] == "Test task from SDK (interactive login)"
        return _json_response({"data": [{"id": payload[0]["id"], "title": payload[0]["title"]}]})

    client = _make_client(handler, email="moritz@example.com")
    task = client.task.create("Test task from SDK (interactive login)")

    assert client.access_token == "access-token"
    assert client.refresh_token == "refresh-token"
    assert task["title"] == "Test task from SDK (interactive login)"
    assert task["id"]


def test_token_reuse_and_create_task():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == "/v5/tasks"
        payload = json.loads(request.content)
        assert payload[0]["title"] == "Test task from SDK (token reuse)"
        return _json_response({"data": [{"id": payload[0]["id"], "title": payload[0]["title"]}]})

    client = _make_client(
        handler,
        access_token="existing-access-token",
        refresh_token="existing-refresh-token",
        verify_ssl=False,
    )
    task = client.task.create("Test task from SDK (token reuse)")

    assert client.access_token == "existing-access-token"
    assert client.refresh_token == "existing-refresh-token"
    assert task["title"] == "Test task from SDK (token reuse)"


def test_create_schedule_done_and_delete_task():
    created_task = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == "/v5/tasks"
        payload = json.loads(request.content)[0]

        if payload.get("title") == "SDK demo task":
            created_task.update({"id": payload["id"], "title": payload["title"]})
            return _json_response({"data": [{"id": payload["id"], "title": payload["title"]}]})

        if payload.get("status") == 2 and payload.get("duration") == 1800:
            assert payload["id"] == created_task["id"]
            assert payload["datetime"] == "2026-03-27T09:00:00.000Z"
            assert payload["date"] == "2026-03-27"
            return _json_response({"data": [{"id": payload["id"], "title": created_task["title"], "status": 2}]})

        if payload.get("done") is True:
            assert payload["id"] == created_task["id"]
            datetime.fromisoformat(payload["done_at"].replace("Z", "+00:00"))
            return _json_response(
                {
                    "data": [
                        {
                            "id": payload["id"],
                            "title": created_task["title"],
                            "done": True,
                            "date": payload["date"],
                            "done_at": payload["done_at"],
                        }
                    ]
                }
            )

        if payload.get("status") == 10:
            assert payload["id"] == created_task["id"]
            assert payload["trashed_at"]
            return _json_response(
                {"data": [{"id": payload["id"], "title": created_task["title"], "trashed_at": payload["trashed_at"]}]}
            )

        raise AssertionError(f"Unexpected payload: {payload}")

    client = _make_client(handler, access_token="access-token", refresh_token="refresh-token")

    task = client.task.create("SDK demo task")
    scheduled = client.task.update(
        task["id"],
        date="2026-03-27",
        datetime_="2026-03-27T09:00:00.000Z",
        duration=1800,
        status=2,
    )
    done = client.task.done(task["id"], date="2026-03-27")
    deleted = client.task.delete(task["id"])

    assert scheduled["status"] == 2
    assert done["done"] is True
    assert deleted["trashed_at"]


def test_label_lifecycle_with_task_assignment():
    state = {
        "label": None,
        "task": None,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PATCH" and request.url.path == "/v5/labels":
            payload = json.loads(request.content)[0]

            if payload.get("title") == "sdk_test":
                state["label"] = {"id": payload["id"], "title": payload["title"]}
                return _json_response({"data": [payload]})

            if payload.get("title") == "sdk_test_renamed":
                assert payload["id"] == state["label"]["id"]
                state["label"]["title"] = payload["title"]
                return _json_response({"data": [{"id": payload["id"], "title": payload["title"]}]})

            if payload.get("deleted_at"):
                assert payload["id"] == state["label"]["id"]
                return _json_response({"data": [{"id": payload["id"], "deleted_at": payload["deleted_at"]}]})

        if request.method == "GET" and request.url.path == "/v5/labels":
            return _json_response({"data": [state["label"]]})

        if request.method == "PATCH" and request.url.path == "/v5/tasks":
            payload = json.loads(request.content)[0]

            if payload.get("title") == "sdk_test Task":
                assert payload["listId"] == state["label"]["id"]
                state["task"] = {"id": payload["id"], "title": payload["title"]}
                return _json_response(
                    {"data": [{"id": payload["id"], "title": payload["title"], "listId": payload["listId"]}]}
                )

            if payload.get("done") is True:
                assert payload["id"] == state["task"]["id"]
                return _json_response(
                    {
                        "data": [
                            {
                                "id": payload["id"],
                                "title": state["task"]["title"],
                                "done": True,
                                "done_at": payload["done_at"],
                            }
                        ]
                    }
                )

        raise AssertionError(f"Unexpected request: {request.method} {request.url.path}")

    client = _make_client(handler, access_token="access-token", refresh_token="refresh-token", verify_ssl=False)

    label = client.label.create("sdk_test", color="palette-pink")
    task = client.task.create("sdk_test Task", label="sdk_test")
    done = client.task.done(task["id"])
    renamed = client.label.update(label["id"], title="sdk_test_renamed")
    deleted = client.label.delete(label["id"])

    assert label["title"] == "sdk_test"
    assert task["listId"] == label["id"]
    assert done["done"] is True
    assert renamed["title"] == "sdk_test_renamed"
    assert deleted["deleted_at"]
