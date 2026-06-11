"""Security gate proof for the realtime voice webhooks.

These endpoints are called server-to-server by Vapi and one of them can WRITE
the user's calendar, so they must never be publicly callable. This suite
proves the ``VAPI_WEBHOOK_SECRET`` gate BEFORE the calendar tool is wired:

    * an UNSIGNED request to either voice webhook -> 401
    * a request with the WRONG secret               -> 401
    * a request with the CORRECT secret             -> NOT 401 (reaches handler)
    * if no server secret is configured             -> 503 (fail closed)
"""

import importlib

import pytest
from fastapi.testclient import TestClient

from voice.auth import VAPI_SECRET_HEADER

# Both server-to-server voice webhooks that must be protected.
PROTECTED_ENDPOINTS = ["/api/voice/llm/chat/completions", "/api/voice/tools/calendar"]

TEST_SECRET = "test-secret-do-not-use-in-prod"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("VAPI_WEBHOOK_SECRET", TEST_SECRET)
    import main

    importlib.reload(main)
    return TestClient(main.app)


@pytest.mark.parametrize("endpoint", PROTECTED_ENDPOINTS)
def test_unsigned_request_is_rejected(client, endpoint):
    """No secret header at all -> 401. The endpoint is not publicly callable."""
    resp = client.post(endpoint, json={})
    assert resp.status_code == 401, resp.text


@pytest.mark.parametrize("endpoint", PROTECTED_ENDPOINTS)
def test_wrong_secret_is_rejected(client, endpoint):
    """Bad secret -> 401 (constant-time mismatch)."""
    resp = client.post(endpoint, json={}, headers={VAPI_SECRET_HEADER: "wrong-secret"})
    assert resp.status_code == 401, resp.text


@pytest.mark.parametrize("endpoint", PROTECTED_ENDPOINTS)
def test_correct_secret_passes_auth(client, endpoint):
    """Correct secret -> auth passes (NOT 401). Handler is reached."""
    resp = client.post(endpoint, json={}, headers={VAPI_SECRET_HEADER: TEST_SECRET})
    assert resp.status_code != 401, resp.text


@pytest.mark.parametrize("endpoint", PROTECTED_ENDPOINTS)
def test_fail_closed_when_secret_unset(monkeypatch, endpoint):
    """No server secret configured -> 503, never silently open."""
    monkeypatch.delenv("VAPI_WEBHOOK_SECRET", raising=False)
    import main

    importlib.reload(main)
    resp = TestClient(main.app).post(endpoint, json={}, headers={VAPI_SECRET_HEADER: "anything"})
    assert resp.status_code == 503, resp.text
