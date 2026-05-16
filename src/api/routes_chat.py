from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from src.browser.chatgpt_page import ChatGPTPage
from src.models.request_models import ChatRequest, OpenAIChatCompletionRequest
from src.models.response_models import build_openai_response
from src.utils.errors import ErrorCode, RelayError, error_response

router = APIRouter()


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> JSONResponse:
    browser = request.app.state.browser
    if not browser.started or browser.page is None:
        return JSONResponse(
            status_code=503,
            content=error_response(
                ErrorCode.BROWSER_NOT_STARTED,
                "Browser is not attached. Open noVNC, sign in manually, then POST /browser/attach.",
            ),
        )

    lock: asyncio.Lock = request.app.state.chat_lock
    if lock.locked():
        return JSONResponse(
            status_code=429,
            content=error_response(ErrorCode.BUSY, "Browser is processing another request."),
        )

    async with lock:
        try:
            answer, duration = await ChatGPTPage(browser.page).ask(body.message)
            return JSONResponse(content={"ok": True, "answer": answer, "duration_seconds": duration})
        except RelayError as exc:
            browser.last_error = f"{exc.code.value}: {exc.message}"
            status_code = _status_code_for_error(exc.code)
            return JSONResponse(
                status_code=status_code,
                content=error_response(exc.code, exc.message, exc.debug_dir),
            )


@router.post("/v1/chat/completions")
async def openai_chat_completions(request: Request, body: OpenAIChatCompletionRequest) -> dict[str, Any]:
    if body.stream:
        raise HTTPException(
            status_code=400,
            detail=error_response(ErrorCode.SELECTOR_FAILED, "stream is not supported in browser-ai-relay."),
        )
    if body.tools or body.tool_choice:
        raise HTTPException(
            status_code=400,
            detail=error_response(ErrorCode.SELECTOR_FAILED, "tools and tool_choice are not supported."),
        )

    prompt = build_prompt_from_messages([msg.model_dump() for msg in body.messages])
    if not prompt.strip():
        raise HTTPException(
            status_code=400,
            detail=error_response(ErrorCode.RESPONSE_EMPTY, "No text user message found in messages."),
        )

    chat_response = await chat(request, ChatRequest(message=prompt))
    if chat_response.status_code >= 400:
        raise HTTPException(status_code=chat_response.status_code, detail=chat_response.body.decode("utf-8"))

    import json

    payload = json.loads(chat_response.body)
    return build_openai_response(body.model, payload["answer"], prompt)


def build_prompt_from_messages(messages: list[dict[str, Any]]) -> str:
    system_parts: list[str] = []
    user_parts: list[str] = []

    for message in messages:
        role = message.get("role")
        content = _content_to_text(message.get("content"))
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        elif role == "user":
            user_parts.append(content)

    if not user_parts:
        return ""

    prefix = "\n\n".join(system_parts).strip()
    user_text = user_parts[-1].strip()
    return f"{prefix}\n\n{user_text}".strip() if prefix else user_text


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                parts.append(str(item.get("text", "")).strip())
            else:
                raise HTTPException(
                    status_code=400,
                    detail=error_response(
                        ErrorCode.SELECTOR_FAILED,
                        "Only plain text content is supported. Images and files are intentionally disabled.",
                    ),
                )
        return "\n".join(part for part in parts if part)
    return str(content).strip()


def _status_code_for_error(code: ErrorCode) -> int:
    if code == ErrorCode.BUSY:
        return 429
    if code in {ErrorCode.NOT_LOGGED_IN, ErrorCode.AUTH_FAILED}:
        return 401
    if code == ErrorCode.BROWSER_NOT_STARTED:
        return 503
    return 500
