"""Exception hierarchy for the Akiflow SDK."""


class AkiflowError(Exception):
    """Base exception for all Akiflow SDK errors."""


class AuthError(AkiflowError):
    """Raised when authentication fails (bad OTP, expired link, etc.)."""


class APIError(AkiflowError):
    """Raised on non-2xx responses from the Akiflow API.

    Attributes:
        status_code: HTTP status code.
        message: Error message from the response body.
    """

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class TokenExpiredError(APIError):
    """Raised when the access token is expired and cannot be refreshed.

    This typically means the refresh token has also expired or was revoked.
    Re-authenticate with `Akiflow(email=...)` to get new tokens.
    """
