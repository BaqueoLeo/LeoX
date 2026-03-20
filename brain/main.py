"""FastAPI app — LeoX Brain."""

from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from brain.orchestrator import handle_message

load_dotenv()

app = FastAPI(title="LeoX Brain", version="1.0.0")


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


@app.get("/health")
async def health():
    return {"status": "ok", "service": "brain"}
