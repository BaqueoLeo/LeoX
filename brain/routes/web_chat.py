"""Web chat router — exposes a REST endpoint for the iPhone web UI.

POST /web/message
  Header: X-Web-Secret: <secret>   (required if WEB_SECRET env var is set)
  Body:   { "text": str, "session_id": str }
  Return: { "reply": str }

The session_id (UUID generated client-side) maps to a jid prefixed with
"web_" so conversation history stays separate from WhatsApp sessions.
"""

import os
import logging

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from brain.orchestrator import handle_message

logger = logging.getLogger(__name__)

router = APIRouter()

_WEB_SECRET = os.getenv("WEB_SECRET", "")


class WebMessage(BaseModel):
    text: str
    session_id: str


class WebResponse(BaseModel):
    reply: str


def _check_secret(x_web_secret: str | None) -> None:
    """Validate X-Web-Secret header when WEB_SECRET is configured."""
    if not _WEB_SECRET:
        return
    if x_web_secret != _WEB_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Web-Secret")


@router.post("/message", response_model=WebResponse)
async def web_message(
    msg: WebMessage,
    x_web_secret: str | None = Header(default=None),
):
    """Receive a message from the web UI and return an AI response."""
    _check_secret(x_web_secret)

    if not msg.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    jid = f"web_{msg.session_id}"

    logger.info(f"[WebChat] session={msg.session_id[:8]}… text={msg.text[:80]}")

    result = await handle_message(
        sender=jid,
        text=msg.text,
        jid=jid,
        push_name="web",
    )

    reply = result.get("reply") or ""
    return WebResponse(reply=reply)
