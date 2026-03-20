"""Central orchestrator — routes incoming messages through the AI pipeline.

Phase 1: Simple message → AI → response flow.
Phase 2+: Memory retrieval, commitment detection, voice decisions.
"""

import logging
from collections import deque

from brain.ai_router import get_ai_response
from brain.personality import get_system_prompt
from brain.response_formatter import format_response

logger = logging.getLogger(__name__)

# Short-term memory: last N messages per conversation
MAX_HISTORY = 20
_conversations: dict[str, deque] = {}


def _get_history(jid: str) -> list[dict]:
    """Get conversation history for a given chat."""
    if jid not in _conversations:
        _conversations[jid] = deque(maxlen=MAX_HISTORY)
    return list(_conversations[jid])


def _add_to_history(jid: str, role: str, content: str):
    """Add a message to conversation history."""
    if jid not in _conversations:
        _conversations[jid] = deque(maxlen=MAX_HISTORY)
    _conversations[jid].append({"role": role, "content": content})


async def handle_message(
    sender: str,
    text: str,
    jid: str,
    push_name: str = "",
) -> dict:
    """Process an incoming WhatsApp message and return a response.

    Returns dict with 'reply', 'format', and optionally 'audio'.
    """
    if not text.strip():
        return {"reply": None, "format": "text", "audio": None}

    logger.info(f"[Orchestrator] {push_name or sender}: {text[:80]}")

    # Build conversation context
    _add_to_history(jid, "user", text)
    messages = _get_history(jid)

    # Get system prompt
    system = get_system_prompt()

    # Get AI response with fallback chain
    ai_result = await get_ai_response(system, messages)

    logger.info(f"[Orchestrator] Respondió {ai_result.provider}/{ai_result.model}")

    # Add response to history
    _add_to_history(jid, "assistant", ai_result.text)

    # Format for WhatsApp
    return format_response(ai_result.text)
