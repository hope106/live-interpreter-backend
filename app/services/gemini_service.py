from __future__ import annotations

import asyncio
import base64
import contextlib
import os
import time
from array import array
from typing import Awaitable, Callable, Optional, Tuple

import ssl
import google.genai as genai
from google.genai.types import LiveServerMessage
from dotenv import load_dotenv

from ..utils.logging import get_logger

# Load environment variables from .env file
load_dotenv()

# WARNING: The following lines disable SSL certificate verification globally.
# This is a security risk and should only be used for local development.
_original_create_default_context = ssl.create_default_context
def _unverified_create_default_context(*args, **kwargs):
    context = _original_create_default_context(*args, **kwargs)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context
ssl.create_default_context = _unverified_create_default_context

logger = get_logger(__name__)


class SimpleVAD:
    """Minimal voice activity detector based on PCM amplitude."""

    def __init__(self, threshold: int, hangover_frames: int = 3):
        self.threshold = max(threshold, 0)
        self.hangover_frames = max(hangover_frames, 0)
        self._silence_frames = 0
        self._in_speech = False

    def should_forward(self, audio_bytes: bytes) -> Tuple[bool, float]:
        if len(audio_bytes) < 2:
            return False, 0.0
        trimmed = audio_bytes[: len(audio_bytes) - (len(audio_bytes) % 2)]
        if not trimmed:
            return False, 0.0
        samples = array("h")
        samples.frombytes(trimmed)
        if not samples:
            return False, 0.0
        avg_energy = sum(abs(sample) for sample in samples) / len(samples)
        if avg_energy >= self.threshold:
            self._in_speech = True
            self._silence_frames = 0
            return True, avg_energy
        if self._in_speech and self._silence_frames < self.hangover_frames:
            self._silence_frames += 1
            return True, avg_energy
        self._in_speech = False
        self._silence_frames = min(self._silence_frames + 1, self.hangover_frames)
        return False, avg_energy

SYSTEM_INSTRUCTION = """You are an ultra-fast, bidirectional simultaneous interpreter for a voice-to-voice translation system.

### CORE INSTRUCTIONS:
1. Auto-detect: Korean → English, English → Korean.
2. Output ONLY translated speech text with zero fluff.
3. Favor natural spoken tone with breathable punctuation.
"""

MODEL_NAME = "gemini-2.5-flash-native-audio-preview-09-2025"
DEFAULT_VAD_THRESHOLD = int(os.getenv("VAD_THRESHOLD", "500"))
# Hangover frames: allow natural pauses in speech
# 15 frames ≈ 300ms silence tolerance (good for natural speech patterns)
DEFAULT_VAD_HANGOVER = int(os.getenv("VAD_HANGOVER_FRAMES", "15"))


class GeminiService:
    def __init__(
        self,
        on_input_transcription: Callable[[str, bool], Awaitable[None]],
        on_output_transcription: Callable[[str, bool], Awaitable[None]],
        on_audio_response: Callable[[str, int], Awaitable[None]],
        on_turn_complete: Callable[[str, str], Awaitable[None]],
        on_speech_state: Optional[Callable[[str, int], Awaitable[None]]] = None,
        input_sample_rate: int = 16000,
    ):
        self.on_input_transcription = on_input_transcription
        self.on_output_transcription = on_output_transcription
        self.on_audio_response = on_audio_response
        self.on_turn_complete = on_turn_complete
        self.on_speech_state = on_speech_state
        self.input_sample_rate = input_sample_rate

        self.session_manager: Optional[any] = None
        self.session: Optional[any] = None
        self.receive_task: Optional[asyncio.Task] = None
        self.current_input_text = ""
        self.current_output_text = ""
        self.is_turn_complete = False  # Track if waiting for new turn
        self.turn_complete_time: Optional[float] = None
        self.last_speech_state: Optional[str] = None  # Track speech state changes
        self.vad = (
            SimpleVAD(
                threshold=DEFAULT_VAD_THRESHOLD,
                hangover_frames=DEFAULT_VAD_HANGOVER,
            )
            if DEFAULT_VAD_THRESHOLD > 0
            else None
        )

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=api_key)

    async def connect(self) -> None:
        # Use new Google GenAI SDK Live API
        logger.info("🔌 Connecting to Gemini Live API...")
        config = {
            "generation_config": {
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": "Zephyr"
                        }
                    }
                },
            },
            "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
            "tools": [],
            "input_audio_transcription": {},
            "output_audio_transcription": {},
        }

        self.session_manager = self.client.aio.live.connect(
            model=MODEL_NAME,
            config=config
        )
        self.session = await self.session_manager.__aenter__()
        self.receive_task = asyncio.create_task(self._receive_messages())
        logger.info("✅ Connected to Gemini Live session successfully")
        logger.debug("VAD enabled: %s (threshold=%d)", bool(self.vad), DEFAULT_VAD_THRESHOLD)

    async def send_audio(self, base64_audio: str) -> None:
        if not self.session:
            logger.error("❌ Attempted to send audio but Gemini session is not connected!")
            raise RuntimeError("Gemini session not connected")

        audio_bytes = base64.b64decode(base64_audio)

        # Check VAD first
        if self.vad:
            should_forward, energy = self.vad.should_forward(audio_bytes)

            # Notify speech state changes
            current_state = "speaking" if should_forward else "silent"
            if self.on_speech_state and current_state != self.last_speech_state:
                await self.on_speech_state(current_state, int(time.time() * 1000))
                self.last_speech_state = current_state

            if not should_forward:
                # logger.debug("⏭️ Skipping silent chunk (energy=%.2f)", energy)
                return

            # First audio after turn complete - allow brief settling time
            if self.is_turn_complete and energy > self.vad.threshold:
                elapsed = time.time() - (self.turn_complete_time or 0)

                # Ensure minimum delay after turn complete (100ms recommended)
                min_delay = 0.1  # 100ms
                if elapsed < min_delay:
                    wait_time = min_delay - elapsed
                    logger.debug("⏳ Waiting %.0fms for session to be ready...", wait_time * 1000)
                    await asyncio.sleep(wait_time)
                    elapsed = time.time() - (self.turn_complete_time or 0)

                logger.info("▶️ New turn started (%.2fs after previous turn complete, energy=%.2f)",
                           elapsed, energy)
                self.is_turn_complete = False
                self.turn_complete_time = None

            #logger.debug("🎤 Forwarding audio chunk (energy=%.2f, size=%d bytes)", energy, len(audio_bytes))
        else:
            logger.error("🎤 Sending audio chunk (VAD disabled, size=%d bytes)", len(audio_bytes))

        # Gemini Live expects audio blobs via send_realtime_input
        mime_type = f"audio/pcm;rate={self.input_sample_rate}"
        blob = genai.types.Blob(data=audio_bytes, mime_type=mime_type)

        try:
            await self.session.send_realtime_input(audio=blob)
        except Exception as exc:
            logger.error("❌ Failed to send audio to Gemini: %s", exc, exc_info=True)
            raise

    async def send_text(self, text: str) -> None:
        if not self.session:
            raise RuntimeError("Gemini session not connected")
        # Use new API for client content
        client_content = genai.types.LiveClientContent(
            content=genai.types.Content(
                parts=[genai.types.Part(text=text)]
            )
        )
        await self.session.send_client_content(client_content)

    async def interrupt(self) -> None:
        self.current_output_text = ""

    async def disconnect(self) -> None:
        logger.info("🔌 Disconnecting from Gemini Live session...")

        if self.receive_task:
            logger.debug("Cancelling receive task...")
            self.receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.receive_task
            self.receive_task = None
            logger.debug("✅ Receive task cancelled")

        if self.session_manager:
            logger.debug("Closing session manager...")
            await self.session_manager.__aexit__(None, None, None)
            self.session_manager = None
            logger.debug("✅ Session manager closed")

        self.session = None
        logger.info("✅ Gemini Live session disconnected successfully")

    async def _receive_messages(self) -> None:
        assert self.session is not None
        logger.info("🔄 Gemini receive loop started")
        message_count = 0
        last_message_time = time.time()

        try:
            while True:  # Keep receiving messages indefinitely
                try:
                    async for message in self.session.receive():
                        message_count += 1
                        current_time = time.time()
                        time_since_last = current_time - last_message_time
                        logger.debug("📬 Message #%d received from Gemini (%.2fs since last message)",
                                   message_count, time_since_last)
                        last_message_time = current_time
                        await self._handle_message(message)

                    # If receive() completes normally (e.g., after turn_complete),
                    # continue the loop to wait for more messages
                    logger.info("📭 Receive stream ended, waiting for new messages... (total: %d)", message_count)
                    await asyncio.sleep(0.01)  # Brief pause before resuming

                except StopAsyncIteration:
                    # Normal end of stream, continue waiting
                    logger.debug("🔄 Stream iteration ended, resuming...")
                    await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            logger.info("🛑 Gemini receive loop cancelled (expected on disconnect, total messages: %d)", message_count)
            raise
        except Exception as exc:
            logger.error("❌ Gemini receive loop error after %d messages: %s", message_count, exc, exc_info=True)
            logger.error("⚠️ Receive loop terminated - no more responses will be processed!")
            raise

    async def _handle_message(self, message: LiveServerMessage) -> None:
        # 메시지 타입 디버깅
        # logger.debug("📨 Received Gemini message type: %s", type(message.server_content).__name__)

        input_trans = getattr(message.server_content, "input_transcription", None)
        if input_trans is not None:
            chunk_text = input_trans.text or ""
            if chunk_text.strip():
                logger.debug("🎤 입력 인식 텍스트: %s", chunk_text)
                self.current_input_text += chunk_text
                await self.on_input_transcription(self.current_input_text, False)

        output_trans = getattr(message.server_content, "output_transcription", None)
        if output_trans and output_trans.text:
            logger.debug("🔊 출력 인식 텍스트: %s", output_trans.text)
            self.current_output_text += output_trans.text
            await self.on_output_transcription(self.current_output_text, False)

        model_turn = getattr(message.server_content, "model_turn", None)
        if model_turn and getattr(model_turn, "parts", None):
            # logger.debug("🎵 모델 응답 오디오 수신 (parts: %d)", len(model_turn.parts))
            for part in model_turn.parts:
                inline = getattr(part, "inline_data", None)
                if inline and inline.data:
                    # Gemini returns raw bytes; convert to base64 for WebSocket JSON payloads
                    encoded = base64.b64encode(inline.data).decode("ascii")
                    await self.on_audio_response(encoded, 24000)

        if getattr(message.server_content, "turn_complete", False):
            logger.info("✅ Turn complete - Input: '%s' | Output: '%s'",
                       self.current_input_text, self.current_output_text)
            await self.on_input_transcription(self.current_input_text, True)
            await self.on_output_transcription(self.current_output_text, True)
            await self.on_turn_complete(self.current_input_text, self.current_output_text)

            # 상태 리셋
            self.current_input_text = ""
            self.current_output_text = ""
            self.is_turn_complete = True
            self.turn_complete_time = time.time()
            logger.debug("🔄 Session state reset for next turn")
            logger.info("⏸️ Waiting for session to be ready for next input...")
