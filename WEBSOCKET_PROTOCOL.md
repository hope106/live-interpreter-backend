# WebSocket Protocol Reference

## Server → Client Messages

### 1. Connected
Sent when WebSocket connection is established and session is ready.
```json
{
  "type": "connected",
  "sessionId": "uuid-string"
}
```

### 2. Input Transcription
User's speech being transcribed (partial and final).
```json
{
  "type": "input_transcription",
  "text": "transcribed text",
  "isFinal": false,
  "language": "ko"  // Only present when isFinal=true
}
```

### 3. Output Transcription
Gemini's response being transcribed (partial and final).
```json
{
  "type": "output_transcription",
  "text": "translated text",
  "isFinal": false,
  "language": "en"  // Only present when isFinal=true
}
```

### 4. Audio Response
Gemini's audio response data.
```json
{
  "type": "audio_response",
  "data": "base64-encoded-audio",
  "sampleRate": 24000
}
```

### 5. Turn Complete
Sent when conversation turn is complete.
```json
{
  "type": "turn_complete",
  "inputText": "complete input text",
  "outputText": "complete output text"
}
```

### 6. Speech State (NEW)
Indicates current speech detection state.
```json
{
  "type": "speech_state",
  "state": "speaking",  // "speaking" | "silent" | "processing"
  "timestamp": 1702345678901
}
```

**State Meanings**:
- `"speaking"`: VAD detected active speech in audio stream
- `"silent"`: VAD detected silence (no speech above threshold)
- `"processing"`: (Reserved for future use - turn being processed by Gemini)

**Usage Example**:
```javascript
// Frontend handling
if (message.type === 'speech_state') {
  if (message.state === 'speaking') {
    // User is speaking - show active microphone indicator
    microphoneIcon.classList.add('active');
  } else if (message.state === 'silent') {
    // Listening but no speech detected - show idle state
    microphoneIcon.classList.remove('active');
  }
}
```

### 7. Error
Error notification with optional error code.
```json
{
  "type": "error",
  "message": "error description",
  "code": "ERROR_CODE"  // Optional
}
```

**Common Error Codes**:
- `"ALREADY_INIT"`: Session already initialized
- `"NOT_READY"`: Session not initialized before operation

## Client → Server Messages

### 1. Init
Initialize session with configuration.
```json
{
  "type": "init",
  "config": {
    "language": "auto",      // "auto" | "ko" | "en"
    "useWhisper": false,     // Toggle Whisper STT pipeline
    "sampleRate": 16000      // 8000-48000
  }
}
```

### 2. Audio
Send audio chunk to server.
```json
{
  "type": "audio",
  "data": "base64-encoded-pcm",
  "timestamp": 1702345678901
}
```

**Audio Format**: PCM 16-bit signed little-endian, mono channel

### 3. Interrupt
Interrupt current Gemini response.
```json
{
  "type": "interrupt"
}
```

### 4. Close
Close WebSocket connection gracefully.
```json
{
  "type": "close"
}
```

## Message Flow Examples

### Successful Turn Flow
```
Client: {"type": "init", "config": {...}}
Server: {"type": "connected", "sessionId": "..."}

Client: {"type": "audio", "data": "...", "timestamp": 123}
Server: {"type": "speech_state", "state": "speaking", "timestamp": 123}
Client: {"type": "audio", "data": "...", "timestamp": 124}
Server: {"type": "input_transcription", "text": "안녕", "isFinal": false}
Client: {"type": "audio", "data": "...", "timestamp": 125}
Server: {"type": "input_transcription", "text": "안녕하세요", "isFinal": false}
Server: {"type": "speech_state", "state": "silent", "timestamp": 126}
Server: {"type": "input_transcription", "text": "안녕하세요", "isFinal": true, "language": "ko"}
Server: {"type": "audio_response", "data": "...", "sampleRate": 24000}
Server: {"type": "output_transcription", "text": "Hello", "isFinal": false}
Server: {"type": "audio_response", "data": "...", "sampleRate": 24000}
Server: {"type": "output_transcription", "text": "Hello.", "isFinal": true, "language": "en"}
Server: {"type": "turn_complete", "inputText": "안녕하세요", "outputText": "Hello."}
```

### Multiple Turns
The session remains active after `turn_complete`, allowing multiple consecutive turns without reconnection.

```
[Turn 1 completes with turn_complete message]
Client: {"type": "audio", "data": "...", "timestamp": 200}
Server: {"type": "speech_state", "state": "speaking", "timestamp": 200}
[Turn 2 begins automatically...]
```

## VAD Configuration

Speech state transitions are controlled by VAD (Voice Activity Detection) settings:

- **VAD_THRESHOLD** (default: 500): Minimum energy level (0-32768) to detect voice
- **VAD_HANGOVER_FRAMES** (default: 15): Silent frames (~20ms each) before ending speech

**Tuning Guide**:
- High threshold (>1000): Less sensitive, fewer false positives, may miss soft speech
- Low threshold (<300): More sensitive, more false positives from background noise
- High hangover (>20): Tolerates longer pauses, less fragmentation, slower turn detection
- Low hangover (<10): More responsive, may fragment natural speech with pauses
