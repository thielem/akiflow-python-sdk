"""Low-level authentication helpers.

Most users should use `Akiflow(email=...)` instead of calling these directly.
These are exposed for advanced use cases like custom token storage.
"""

from __future__ import annotations

import uuid
from urllib.parse import unquote

import httpx

from .exceptions import AuthError

WEB_BASE = "https://web.akiflow.com"
DEFAULT_HEADERS = {
    "Akiflow-Platform": "web",
    "Akiflow-Version": "2.69.3",
}


def _extract_xsrf(cookies: httpx.Cookies) -> str:
    token = cookies.get("XSRF-TOKEN")
    if not token:
        raise AuthError("No XSRF-TOKEN cookie received")
    return unquote(token)


def interactive_login(email: str, client_id: str | None = None, verify_ssl: bool = True) -> dict:
    """Run the full interactive auth flow: email -> OTP -> tokens.

    Sends a one-time code to `email`, prompts via `input()`, and exchanges
    the verified session for OAuth tokens.

    Args:
        email: Akiflow account email address.
        client_id: Optional client UUID. Auto-generated if omitted.
        verify_ssl: Set to False to skip SSL verification (for proxies).

    Returns:
        Dict with `access_token`, `refresh_token`, `expires_in`, `client_id`.

    Raises:
        AuthError: If login or OTP verification fails.

    Example:
        ```python
        from akiflow.auth import interactive_login

        tokens = interactive_login("you@example.com")
        print(tokens["access_token"])
        ```
    """
    cid = client_id or str(uuid.uuid4())

    with httpx.Client(follow_redirects=True, verify=verify_ssl) as http:
        # Step 1: get CSRF cookie
        resp = http.get(f"{WEB_BASE}/csrf-cookie")
        resp.raise_for_status()
        xsrf = _extract_xsrf(http.cookies)

        # Step 2: request OTP email
        resp = http.post(
            f"{WEB_BASE}/auth/login",
            json={"email": email, "remember": True},
            headers={**DEFAULT_HEADERS, "X-XSRF-TOKEN": xsrf},
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise AuthError(f"Login request failed: {body.get('message')}")

        redirect_url = body["redirect"]

        # Step 3: prompt user for OTP code
        code = input(f"Enter the 6-digit code sent to {email}: ").strip()
        if not code:
            raise AuthError("No code provided")

        # Refresh XSRF after login call (cookie may have rotated)
        xsrf = _extract_xsrf(http.cookies)

        # Step 4: verify OTP
        resp = http.post(
            redirect_url,
            json={"email": email, "code": code},
            headers={**DEFAULT_HEADERS, "X-XSRF-TOKEN": xsrf},
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise AuthError(f"OTP verification failed: {body.get('message')}")

        # Refresh XSRF after OTP verification
        xsrf = _extract_xsrf(http.cookies)

        # Step 5: get user info + tokens
        resp = http.get(
            f"{WEB_BASE}/user/me",
            headers={**DEFAULT_HEADERS, "X-XSRF-TOKEN": xsrf},
        )
        resp.raise_for_status()
        user_data = resp.json()["data"]

        return {
            "access_token": user_data["access_token"],
            "refresh_token": user_data["refresh_token"],
            "expires_in": user_data["expires_in"],
            "client_id": cid,
        }


def refresh_access_token(
    refresh_token: str,
    client_id: str | None = None,
    oauth_client_id: str = "10",
    verify_ssl: bool = True,
) -> dict:
    """Exchange a refresh token for a new access + refresh token pair.

    The refresh token is rotated on each call (the old one is invalidated).

    Args:
        refresh_token: Current refresh token (`def50200...`).
        client_id: Optional client UUID. Auto-generated if omitted.
        oauth_client_id: OAuth client ID (`"10"` for web).
        verify_ssl: Set to False to skip SSL verification.

    Returns:
        Dict with `access_token`, `refresh_token`, `expires_in`, `client_id`.

    Example:
        ```python
        from akiflow.auth import refresh_access_token

        new_tokens = refresh_access_token("def50200...")
        print(new_tokens["access_token"])
        ```
    """
    cid = client_id or str(uuid.uuid4())

    with httpx.Client(follow_redirects=True, verify=verify_ssl) as http:
        # Need CSRF cookie first
        resp = http.get(f"{WEB_BASE}/csrf-cookie")
        resp.raise_for_status()
        xsrf = _extract_xsrf(http.cookies)

        resp = http.post(
            f"{WEB_BASE}/oauth/refreshToken",
            json={"client_id": oauth_client_id, "refresh_token": refresh_token},
            headers={
                **DEFAULT_HEADERS,
                "X-XSRF-TOKEN": xsrf,
                "Akiflow-Client-Id": cid,
            },
        )
        resp.raise_for_status()
        body = resp.json()

        return {
            "access_token": body["access_token"],
            "refresh_token": body["refresh_token"],
            "expires_in": body["expires_in"],
            "client_id": cid,
        }
