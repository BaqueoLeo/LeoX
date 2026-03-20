"""HTTP client for the WhatsApp service (Baileys).

Used by the brain to send messages proactively (morning brief,
event reminders, commitment confirmations, etc.).
"""

import os
import logging

import httpx

logger = logging.getLogger(__name__)

WA_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://localhost:3000")
MY_NUMBER = os.getenv("MY_WHATSAPP_NUMBER", "")


async def send_text(to: str, text: str) -> bool:
    """Send a text message via WhatsApp."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(f"{WA_URL}/send", json={"to": to, "text": text})
            return r.status_code == 200
        except Exception as e:
            logger.error(f"[WA Client] Error enviando texto: {e}")
            return False


async def send_voice(to: str, audio_base64: str) -> bool:
    """Send a voice note via WhatsApp."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.post(
                f"{WA_URL}/send", json={"to": to, "audio": audio_base64}
            )
            return r.status_code == 200
        except Exception as e:
            logger.error(f"[WA Client] Error enviando voz: {e}")
            return False


async def send_to_user(text: str) -> bool:
    """Send a message to the configured user (MY_WHATSAPP_NUMBER)."""
    if not MY_NUMBER:
        logger.error("[WA Client] MY_WHATSAPP_NUMBER no configurado")
        return False
    return await send_text(MY_NUMBER, text)


async def get_status() -> dict | None:
    """Check WhatsApp service connection status."""
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.get(f"{WA_URL}/status")
            return r.json()
        except Exception:
            return None
