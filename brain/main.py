"""FastAPI app — LeoX Brain."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from brain.orchestrator import handle_message
from brain.routes.web_chat import router as web_router

load_dotenv()

app = FastAPI(title="LeoX Brain", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(web_router, prefix="/web")

_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


class IncomingMessage(BaseModel):
    """Message forwarded from the WhatsApp service."""

    from_: str = ""
    text: str = ""
    jid: str = ""
    timestamp: int = 0
    pushName: str = ""

    class Config:
        populate_by_name = True
        # Allow 'from' field (reserved keyword) via alias
        fields = {"from_": {"alias": "from"}}


class BrainResponse(BaseModel):
    reply: str | None = None
    format: str = "text"  # "text" | "voice"
    audio: str | None = None  # base64 encoded OGG if voice


@app.post("/message", response_model=BrainResponse)
async def receive_message(msg: IncomingMessage):
    """Receive a message from WhatsApp and return a response."""
    result = await handle_message(
        sender=msg.from_ or "",
        text=msg.text,
        jid=msg.jid,
        push_name=msg.pushName,
    )
    return result


@app.get("/")
async def index():
    return FileResponse(str(_STATIC_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "service": "brain"}
