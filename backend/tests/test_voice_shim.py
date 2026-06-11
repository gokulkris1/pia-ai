"""Local verification for the voice LLM shim + calendar tool webhook.

These mock the brain / calendar dispatch so they run with NO API keys, proving:
  * the LLM shim emits OpenAI-shaped SSE chunks (text + tool_calls + [DONE])
  * the calendar tool webhook honours the Vapi tool-call contract
    ({message:{toolCalls:[...]}} -> {results:[{toolCallId, result}]})
"""

import importlib

import pytest
from fastapi.testclient import TestClient

from voice.auth import VAPI_SECRET_HEADER

TEST_SECRET = "test-secret-do-not-use-in-prod"
AUTH = {VAPI_SECRET_HEADER: TEST_SECRET}


@pytest.fixture()
def app_module(monkeypatch):
    monkeypatch.setenv("VAPI_WEBHOOK_SECRET", TEST_SECRET)
    import main

    importlib.reload(main)
    return main


def test_llm_shim_emits_openai_sse(app_module, monkeypatch):
    import voice.llm_shim as shim

    async def fake_stream(system_prompt, messages, tools=None, **kwargs):
        yield {"type": "text", "text": "Hello "}
        yield {"type": "text", "text": "there"}
        yield {
            "type": "tool_call",
            "id": "call_1",
            "name": "read_calendar",
            "arguments": '{"query": "today"}',
        }
        yield {"type": "done", "finish_reason": "tool_calls"}

    monkeypatch.setattr(shim, "stream_response", fake_stream)

    resp = TestClient(app_module.app).post(
        "/api/voice/llm/chat/completions",
        headers=AUTH,
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 200, resp.text
    text = resp.text
    assert "chat.completion.chunk" in text
    assert "Hello " in text and "there" in text
    assert "read_calendar" in text  # tool call surfaced as OpenAI tool_calls
    assert "data: [DONE]" in text


def test_calendar_tool_webhook_contract(app_module, monkeypatch):
    import voice.tools as vt

    monkeypatch.setattr(vt, "dispatch", lambda call_id, name, args: f"did {name}")

    resp = TestClient(app_module.app).post(
        "/api/voice/tools/calendar",
        headers=AUTH,
        json={
            "message": {
                "call": {"id": "c1"},
                "toolCalls": [
                    {
                        "id": "t1",
                        "function": {"name": "read_calendar", "arguments": '{"query": "today"}'},
                    }
                ],
            }
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["results"][0]["toolCallId"] == "t1"
    assert data["results"][0]["result"] == "did read_calendar"


def test_config_is_public_and_env_swappable(app_module, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voiceXYZ")
    monkeypatch.setenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")
    monkeypatch.setenv("PIA_VOICE_MODE", "vapi")

    resp = TestClient(app_module.app).get("/api/voice/config")  # no auth header
    assert resp.status_code == 200, resp.text
    cfg = resp.json()
    assert cfg["voiceMode"] == "vapi"
    assert cfg["assistantOverrides"]["voice"]["provider"] == "11labs"
    assert cfg["assistantOverrides"]["voice"]["voiceId"] == "voiceXYZ"
    assert cfg["assistantOverrides"]["voice"]["model"] == "eleven_flash_v2_5"
    assert cfg["assistantOverrides"]["transcriber"]["provider"] == "deepgram"


def test_config_defaults_to_hope_voice(app_module, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)

    cfg = TestClient(app_module.app).get("/api/voice/config").json()
    # Hope is the default voice + listed first in the dev switcher shortlist.
    assert cfg["voiceId"] == "zGjIP4SZlMnY9m93k97r"
    assert cfg["assistantOverrides"]["voice"]["voiceId"] == "zGjIP4SZlMnY9m93k97r"
    assert cfg["devVoices"][0]["id"] == "zGjIP4SZlMnY9m93k97r"
    assert {v["id"] for v in cfg["devVoices"]} == {
        "zGjIP4SZlMnY9m93k97r",
        "EQx6HGDYjkDpcli6vorJ",
        "0WKkG7JmcKK7MkwhnMIe",
        "6fZce9LFNG3iEITDfqZZ",
    }
    # Stability ~45% / high similarity as requested.
    assert cfg["assistantOverrides"]["voice"]["stability"] == 0.45
    assert cfg["assistantOverrides"]["voice"]["similarityBoost"] == 0.9


def test_dev_voice_override_is_allow_listed(app_module, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    client = TestClient(app_module.app)

    # A hardcoded dev voice is honoured.
    cfg = client.get("/api/voice/config?voiceId=EQx6HGDYjkDpcli6vorJ").json()
    assert cfg["voiceId"] == "EQx6HGDYjkDpcli6vorJ"

    # Anything not on the allow-list falls back to the default (no arbitrary voice).
    cfg = client.get("/api/voice/config?voiceId=not-a-real-voice").json()
    assert cfg["voiceId"] == "zGjIP4SZlMnY9m93k97r"
