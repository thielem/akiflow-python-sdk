"""Main client module."""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from .auth import interactive_login, refresh_access_token
from .exceptions import APIError, TokenExpiredError
from .label import LabelAPI
from .task import TaskAPI

API_BASE = "https://api.akiflow.com"


class Akiflow:
    """Unofficial Akiflow API client.

    Provides access to Akiflow resources through sub-clients:

    - `client.task` — create, update, delete, and list tasks
    - `client.label` — create, update, delete, and list labels/projects

    There are three ways to authenticate:

    **Interactive login** (prompts for 2FA code):
    ```python
    client = Akiflow(email="you@example.com")
    ```

    **Access token + refresh token** (no prompt, auto-refreshes):
    ```python
    client = Akiflow(access_token="eyJ...", refresh_token="def50200...")
    ```

    **Refresh token only** (exchanges for access token on init):
    ```python
    client = Akiflow(refresh_token="def50200...")
    ```

    Args:
        email: Akiflow account email. Triggers interactive OTP flow.
        access_token: JWT access token (expires in 30 min).
        refresh_token: Long-lived refresh token (~13 months). Enables auto-refresh.
        client_id: Client UUID sent with requests. Auto-generated if omitted.
        auto_refresh: Automatically refresh expired tokens on 401. Default `True`.
        debug: Print request/response details to stdout. Default `False`.
        verify_ssl: Verify SSL certificates. Set `False` for proxy tools. Default `True`.
    """

    def __init__(
        self,
        *,
        email: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        client_id: str | None = None,
        auto_refresh: bool = True,
        debug: bool = False,
        verify_ssl: bool = True,
    ):
        self._client_id = client_id or str(uuid.uuid4())
        self._auto_refresh = auto_refresh
        self._debug = debug
        self._verify_ssl = verify_ssl
        self._access_token: str | None = access_token
        self._refresh_token: str | None = refresh_token

        if email and not access_token:
            tokens = interactive_login(email, client_id=self._client_id, verify_ssl=self._verify_ssl)
            self._access_token = tokens["access_token"]
            self._refresh_token = tokens["refresh_token"]
            self._client_id = tokens["client_id"]
            print(f"\nAuthenticated successfully. Save these for next time:")
            print(f"  access_token:  {self._access_token[:50]}...")
            print(f"  refresh_token: {self._refresh_token[:50]}...")

        if not self._access_token:
            if self._refresh_token:
                self._do_refresh()
            else:
                raise ValueError("Provide email (for interactive login) or access_token/refresh_token")

        self._http = httpx.Client(
            base_url=API_BASE,
            headers=self._auth_headers(),
            timeout=30.0,
            verify=self._verify_ssl,
        )

        self.label = LabelAPI(self)
        """Label/project operations. See `akiflow.label.LabelAPI`."""

        self.task = TaskAPI(self)
        """Task operations. See `akiflow.task.TaskAPI`."""

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Akiflow-Platform": "web",
            "Akiflow-Version": "2.69.3",
            "Akiflow-Client-Id": self._client_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _do_refresh(self) -> None:
        if not self._refresh_token:
            raise TokenExpiredError(401, "No refresh token available")
        tokens = refresh_access_token(self._refresh_token, client_id=self._client_id, verify_ssl=self._verify_ssl)
        self._access_token = tokens["access_token"]
        self._refresh_token = tokens["refresh_token"]
        self._client_id = tokens["client_id"]
        if hasattr(self, "_http"):
            self._http.headers.update(self._auth_headers())

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        if self._debug:
            body = kwargs.get("json")
            print(f"\n>>> {method} {API_BASE}{path}")
            if kwargs.get("params"):
                print(f"    params: {kwargs['params']}")
            if body is not None:
                print(f"    body:   {json.dumps(body, indent=2)}")

        resp = self._http.request(method, path, **kwargs)

        if self._debug:
            print(f"<<< {resp.status_code}")
            try:
                print(f"    body:   {json.dumps(resp.json(), indent=2)}")
            except Exception:
                print(f"    body:   {resp.text[:500]}")

        # Auto-refresh on 401
        if resp.status_code == 401 and self._auto_refresh and self._refresh_token:
            if self._debug:
                print("    (refreshing token...)")
            self._do_refresh()
            resp = self._http.request(method, path, **kwargs)
            if self._debug:
                print(f"<<< {resp.status_code} (after refresh)")
                try:
                    print(f"    body:   {json.dumps(resp.json(), indent=2)}")
                except Exception:
                    print(f"    body:   {resp.text[:500]}")

        if resp.status_code == 401:
            raise TokenExpiredError(401, resp.json().get("message", "Unauthorized"))
        if not resp.is_success:
            raise APIError(resp.status_code, resp.text)

        return resp.json()

    def _get(self, path: str, **kwargs: Any) -> dict:
        return self._request("GET", path, **kwargs)

    def _patch(self, path: str, **kwargs: Any) -> dict:
        return self._request("PATCH", path, **kwargs)

    @property
    def access_token(self) -> str | None:
        """Current JWT access token (may change after auto-refresh)."""
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        """Current refresh token (rotates on each refresh)."""
        return self._refresh_token

    def close(self) -> None:
        """Close the underlying HTTP connection."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
