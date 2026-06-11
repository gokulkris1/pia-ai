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
