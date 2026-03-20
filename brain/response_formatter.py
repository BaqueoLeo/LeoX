"""Ensures responses stay short and colloquial.

Phase 1: Basic text formatting.
Phase 2+: Will include voice/text decision logic with ElevenLabs.
"""


def format_response(text: str) -> dict:
    """Format the AI response for WhatsApp delivery.

    Returns dict with 'reply', 'format', and optionally 'audio'.
    """
    # Trim excessive whitespace
    text = text.strip()

    # Remove common assistant-like prefixes the LLM might add
    prefixes_to_strip = [
        "¡Claro! ",
        "¡Por supuesto! ",
        "Con gusto, ",
        "Sure! ",
        "Of course! ",
    ]
    for prefix in prefixes_to_strip:
        if text.startswith(prefix):
            text = text[len(prefix):]

    return {
        "reply": text,
        "format": "text",
        "audio": None,
    }
