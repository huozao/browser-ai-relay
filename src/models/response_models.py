from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


class BrowserStatusResponse(BaseModel):
    ok: bool = True
    browser_started: bool
    chrome_running: bool = False
    cdp_attached: bool = False
    chrome_version: str | None = None
    current_url: str | None = None
    chat_input_found: bool = False
    send_button_found: bool = False
    assistant_message_found: bool = False
    cloudflare_challenge_detected: bool = False
    auth_error_detected: bool = False
    login_status: str = "unknown"
    last_error: str | None = None


class ChatSuccessResponse(BaseModel):
    ok: bool = True
    answer: str
    duration_seconds: float


class OpenAIChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str


class OpenAIChoice(BaseModel):
    index: int = 0
    message: OpenAIChoiceMessage
    finish_reason: str = "stop"


class OpenAIUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenAIChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "browser-chatgpt"
    choices: list[OpenAIChoice]
    usage: OpenAIUsage = Field(default_factory=OpenAIUsage)


def build_openai_response(model: str, answer: str, prompt: str) -> dict[str, Any]:
    prompt_tokens = max(1, len(prompt) // 4)
    completion_tokens = max(1, len(answer) // 4)
    response = OpenAIChatCompletionResponse(
        model=model,
        choices=[OpenAIChoice(message=OpenAIChoiceMessage(content=answer))],
        usage=OpenAIUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )
    return response.model_dump()
