from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class OpenAIMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | list[dict[str, Any]] | None = None


class OpenAIChatCompletionRequest(BaseModel):
    model: str = "browser-chatgpt"
    messages: list[OpenAIMessage] = Field(..., min_length=1)
    stream: bool = False
    tools: list[Any] | None = None
    tool_choice: Any | None = None
