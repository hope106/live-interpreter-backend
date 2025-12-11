from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

from ..models.messages import ClientMessage, ErrorMessage


def parse_client_message(raw_data: str) -> ClientMessage:
    """Convert incoming JSON string into a strongly typed Pydantic model."""
    data = json.loads(raw_data)
    msg_type = data.get("type")
    if msg_type == "init":
        from ..models.messages import InitMessage

        return InitMessage.model_validate(data)
    if msg_type == "audio":
        from ..models.messages import AudioMessage

        return AudioMessage.model_validate(data)
    if msg_type == "interrupt":
        from ..models.messages import InterruptMessage

        return InterruptMessage.model_validate(data)
    if msg_type == "close":
        from ..models.messages import CloseMessage

        return CloseMessage.model_validate(data)
    raise ValueError(f"Unknown message type: {msg_type}")


async def send_error(websocket: WebSocket, message: str, code: str | None = None) -> None:
    """Utility to send consistent error payloads to the client."""
    payload = ErrorMessage(message=message, code=code)
    await websocket.send_json(payload.model_dump())
