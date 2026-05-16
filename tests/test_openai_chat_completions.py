from fastapi.testclient import TestClient

from src.main import create_app
from src.api.routes_chat import build_prompt_from_messages


def test_openai_chat_completion_rejects_stream():
    client = TestClient(create_app(start_browser=False))

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer change-me"},
        json={
            "model": "browser-chatgpt",
            "stream": True,
            "messages": [{"role": "user", "content": "你好"}],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "SELECTOR_FAILED"


def test_openai_prompt_builder_uses_last_user_message_for_simple_request():
    prompt = build_prompt_from_messages(
        [
            {"role": "system", "content": "用中文回答"},
            {"role": "user", "content": "你好"},
        ]
    )

    assert prompt == "用中文回答\n\n你好"
