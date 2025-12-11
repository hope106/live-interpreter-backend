from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class InitConfig(BaseModel):
    language: str = Field(default="auto", description="Target input language or auto")
    useWhisper: bool = Field(default=False, description="Toggle Whisper STT pipeline")
    sampleRate: int = Field(default=16000, ge=8000, le=48000)


class InitMessage(BaseModel):
    type: Literal["init"]
    config: InitConfig


class AudioMessage(BaseModel):
    type: Literal["audio"]
    data: str = Field(description="Base64 encoded PCM chunk")
    timestamp: int


class InterruptMessage(BaseModel):
    type: Literal["interrupt"]


class CloseMessage(BaseModel):
    type: Literal["close"]


ClientMessage = Union[InitMessage, AudioMessage, InterruptMessage, CloseMessage]


class ConnectedMessage(BaseModel):
    type: Literal["connected"] = "connected"
    sessionId: str


class TranscriptionMessage(BaseModel):
    type: Literal["input_transcription", "output_transcription"]
    text: str
    isFinal: bool = False
    language: Optional[str] = None


class AudioResponseMessage(BaseModel):
    type: Literal["audio_response"] = "audio_response"
    data: str
    sampleRate: int


class TurnCompleteMessage(BaseModel):
    type: Literal["turn_complete"] = "turn_complete"
    inputText: str
    outputText: str


class SpeechStateMessage(BaseModel):
    """Indicates current speech detection state"""
    type: Literal["speech_state"] = "speech_state"
    state: Literal["speaking", "silent", "processing"]
    timestamp: int


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: Optional[str] = None


ServerMessage = Union[
    ConnectedMessage,
    TranscriptionMessage,
    AudioResponseMessage,
    TurnCompleteMessage,
    SpeechStateMessage,
    ErrorMessage,
]
