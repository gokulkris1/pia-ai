"""Webhook authentication for the realtime voice endpoints.

The voice endpoints are called server-to-server by Vapi (our managed voice
orchestrator). One of them — the calendar tool webhook — can *write* the
user's calendar, so these endpoints must never be publicly callable.

Vapi signs every server request with a shared secret sent in the
``X-Vapi-Secret`` header (configured as the assistant's "Server URL Secret").
We verify it against ``VAPI_WEBHOOK_SECRET`` using a constant-time compare.

Fail-closed policy:
    * ``VAPI_WEBHOOK_SECRET`` not set on the server  -> 503 (misconfigured,
      never silently open).
    * Header missing or mismatched                   -> 401.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status

# Vapi's default header name for the server URL secret.
VAPI_SECRET_HEADER = "x-vapi-secret"


def _expected_secret() -> str:
    return (os.getenv("VAPI_WEBHOOK_SECRET") or "").strip()


async def require_vapi_auth(
    x_vapi_secret: str | None = Header(default=None, alias=VAPI_SECRET_HEADER),
) -> None:
    """FastAPI dependency: reject unsigned/unauthenticated voice webhook calls.

    Use as ``dependencies=[Depends(require_vapi_auth)]`` on every voice route
    that Vapi calls server-to-server.
    """
    expected = _expected_secret()

    # Fail closed: if no secret is configured, the endpoint is not callable.
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice webhook auth is not configured (VAPI_WEBHOOK_SECRET unset).",
        )

    provided = (x_vapi_secret or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing voice webhook signature.",
        )
