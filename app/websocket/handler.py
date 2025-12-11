from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from ..models.messages import (
    AudioMessage,
    CloseMessage,
    ConnectedMessage,
    InitMessage,
    InterruptMessage,
    TranscriptionMessage,
    TurnCompleteMessage,
    AudioResponseMessage,
    SpeechStateMessage,
)
from ..services.gemini_service import GeminiService
from ..utils.logging import get_logger
from .protocol import parse_client_message, send_error

logger = get_logger(__name__)


class WebSocketHandler:
    """Routes client WebSocket messages to the Gemini Live session."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id: str = ""
        self.gemini_service: Optional[GeminiService] = None
        self.use_whisper = False
        self.receive_task: Optional[asyncio.Task] = None

    async def handle(self) -> None:
        await self.websocket.accept()
        logger.debug("WebSocket accepted from %s", self.websocket.client)

        try:
            while True:
                data = await self.websocket.receive_text()
                message = parse_client_message(data)
                if isinstance(message, InitMessage):
                    await self._handle_init(message)
                elif isinstance(message, AudioMessage):
                    await self._handle_audio(message)
                elif isinstance(message, InterruptMessage):
                    await self._handle_interrupt()
                elif isinstance(message, CloseMessage):
                    await self._handle_close()
                    break
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected: %s", self.session_id or "unknown")
        except Exception as exc:
            logger.exception("WebSocket handler error")
            await send_error(self.websocket, str(exc))
        finally:
            await self._cleanup()

    async def _handle_init(self, message: InitMessage) -> None:
        if self.gemini_service:
            await send_error(self.websocket, "Session already initialized", code="ALREADY_INIT")
            return

        self.session_id = str(uuid.uuid4())
        self.use_whisper = message.config.useWhisper

        self.gemini_service = GeminiService(
            on_input_transcription=self._send_input_transcription,
            on_output_transcription=self._send_output_transcription,
            on_audio_response=self._send_audio_response,
            on_turn_complete=self._send_turn_complete,
            on_speech_state=self._send_speech_state,
            input_sample_rate=message.config.sampleRate,
        )
        await self.gemini_service.connect()

        connected = ConnectedMessage(sessionId=self.session_id)
        await self.websocket.send_json(connected.model_dump())
        logger.debug("Session initialized: %s", self.session_id)

    async def _handle_audio(self, message: AudioMessage) -> None:
        if not self.gemini_service:
            await send_error(self.websocket, "Session not initialized", code="NOT_READY")
            return
        preview = message.data[:32]
        # logger.debug(
        #     "Received audio chunk ts=%s size=%d preview=%s%s",
        #     message.timestamp,
        #     len(message.data),
        #     preview,
        #     "..." if len(message.data) > len(preview) else "",
        # )
        await self.gemini_service.send_audio(message.data)

    async def _handle_interrupt(self) -> None:
        if self.gemini_service:
            await self.gemini_service.interrupt()

    async def _handle_close(self) -> None:
        await self.websocket.close()

    async def _cleanup(self) -> None:
        if self.gemini_service:
            await self.gemini_service.disconnect()
            self.gemini_service = None

    async def _send_input_transcription(self, text: str, is_final: bool) -> None:
        if is_final:
            logger.info("Input transcription (final): %s", text)
        else:
            logger.debug("Input transcription (partial): %s", text)
        payload = TranscriptionMessage(
            type="input_transcription",
            text=text,
            isFinal=is_final,
            language="ko" if is_final else None,
        )
        await self.websocket.send_json(payload.model_dump())

    async def _send_output_transcription(self, text: str, is_final: bool) -> None:
        if is_final:
            logger.info("Output transcription (final): %s", text)
        else:
            logger.debug("Output transcription (partial): %s", text)
        payload = TranscriptionMessage(
            type="output_transcription",
            text=text,
            isFinal=is_final,
            language="en" if is_final else None,
        )
        await self.websocket.send_json(payload.model_dump())

    async def _send_audio_response(self, base64_audio: str, sample_rate: int) -> None:
        payload = AudioResponseMessage(data=base64_audio, sampleRate=sample_rate)
        await self.websocket.send_json(payload.model_dump())

    async def _send_turn_complete(self, input_text: str, output_text: str) -> None:
        payload = TurnCompleteMessage(inputText=input_text, outputText=output_text)
        await self.websocket.send_json(payload.model_dump())

    async def _send_speech_state(self, state: str, timestamp: int) -> None:
        payload = SpeechStateMessage(state=state, timestamp=timestamp)
        await self.websocket.send_json(payload.model_dump())
