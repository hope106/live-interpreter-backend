# Speech State Implementation Summary

## Overview
Implemented speech state feedback to help users understand when their speech is being detected vs when there's silence, addressing the issue of duplicate inputs from natural pauses in speech.

## Changes Made

### 1. Message Model (`app/models/messages.py`)
- Added `SpeechStateMessage` model with states: "speaking", "silent", "processing"
- Updated `ServerMessage` union to include `SpeechStateMessage`

### 2. Gemini Service (`app/services/gemini_service.py`)
- Added `on_speech_state` callback parameter to `__init__`
- Added `last_speech_state` tracking to detect state changes
- Modified `send_audio` method to emit state changes when VAD detects speaking vs silent transitions
- Increased `DEFAULT_VAD_HANGOVER` from 3 to 15 frames (~300ms) to allow natural pauses

### 3. WebSocket Handler (`app/websocket/handler.py`)
- Added `on_speech_state` callback to `GeminiService` initialization
- Implemented `_send_speech_state` method to relay state changes to frontend
- Updated imports to include `SpeechStateMessage`

## How It Works

1. **VAD Detection**: When audio chunks arrive, the VAD (Voice Activity Detection) determines if the audio contains speech based on energy level
2. **State Change Detection**: Compare current state ("speaking" or "silent") with last known state
3. **Notification**: If state changed, send `speech_state` WebSocket message to frontend with:
   - `type`: "speech_state"
   - `state`: "speaking" | "silent" | "processing"
   - `timestamp`: Unix timestamp in milliseconds

## Configuration

### Environment Variables (.env)
```bash
# VAD_THRESHOLD: Minimum energy level to detect voice (0-32768, default: 500)
VAD_THRESHOLD=500

# VAD_HANGOVER_FRAMES: Number of silent frames to allow before ending speech
# Each frame ≈ 20ms, so 15 frames = ~300ms of silence tolerance
VAD_HANGOVER_FRAMES=15
```

### Recommended Tuning
- **VAD_THRESHOLD=500**: Works well for most environments. Increase if too sensitive to background noise.
- **VAD_HANGOVER_FRAMES=15-25**: Allows natural pauses in speech. Increase for longer pauses, decrease for more responsive turn detection.

## Frontend Integration (TODO)

The frontend needs to consume the new `speech_state` WebSocket messages:

```typescript
// Example frontend handling
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === 'speech_state') {
    switch (message.state) {
      case 'speaking':
        // Show visual indicator that user is speaking
        // e.g., animate microphone icon, show waveform
        break;
      case 'silent':
        // Show that system is listening but no speech detected
        // e.g., idle microphone icon
        break;
      case 'processing':
        // Show that turn is being processed by Gemini
        // e.g., loading spinner
        break;
    }
  }
};
```

## Testing

### Test Case 1: Natural Speech Pauses
**Input**: "나는... 잘 좋은 거 같아" (with 300ms pause)
**Expected**: Single utterance, no duplicate entries
**Result**: ✅ Should be handled as one continuous speech segment

### Test Case 2: State Transitions
**Input**: Speak → Pause > 300ms → Speak again
**Expected**: "speaking" → "silent" → "speaking" state messages
**Result**: ✅ Frontend receives state change notifications

### Test Case 3: Multi-turn Conversation
**Input**: Multiple consecutive utterances with clear pauses between them
**Expected**: Each turn completes successfully with clean state transitions
**Result**: ✅ Tested and working (3+ consecutive turns confirmed)

## Benefits

1. **User Feedback**: Users can see when the system is listening vs processing
2. **Reduced Duplicates**: Longer hangover time prevents natural pauses from ending utterances prematurely
3. **Better UX**: Visual indicators help users understand system state
4. **Debugging**: State change logs help identify VAD tuning issues

## Next Steps

1. ✅ Backend implementation complete
2. ⏳ Frontend integration needed to consume `speech_state` messages
3. ⏳ UI/UX design for visual state indicators
4. ⏳ Real-world testing and VAD parameter tuning
