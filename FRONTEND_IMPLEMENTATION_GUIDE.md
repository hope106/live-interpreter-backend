# 프론트엔드 음성 상태 UI 구현 가이드

이 가이드는 백엔드에서 전송하는 `speech_state` 메시지를 받아서 사용자에게 시각적 피드백을 제공하는 방법을 설명합니다.

## 1. WebSocket 메시지 수신 구현

### 기본 메시지 핸들러 추가

프론트엔드의 WebSocket 메시지 핸들러에 `speech_state` 처리를 추가해야 합니다.

```typescript
// WebSocket 메시지 핸들러 예시
websocket.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'connected':
      handleConnected(message.sessionId);
      break;

    case 'input_transcription':
      handleInputTranscription(message.text, message.isFinal);
      break;

    case 'output_transcription':
      handleOutputTranscription(message.text, message.isFinal);
      break;

    case 'audio_response':
      handleAudioResponse(message.data, message.sampleRate);
      break;

    case 'turn_complete':
      handleTurnComplete(message.inputText, message.outputText);
      break;

    case 'speech_state':  // 새로 추가
      handleSpeechState(message.state, message.timestamp);
      break;

    case 'error':
      handleError(message.message, message.code);
      break;
  }
};
```

### 음성 상태 핸들러 구현

```typescript
// 현재 음성 상태를 추적하는 변수
let currentSpeechState: 'speaking' | 'silent' | 'processing' = 'silent';

function handleSpeechState(state: string, timestamp: number) {
  console.log(`[${new Date(timestamp).toISOString()}] Speech state: ${state}`);

  currentSpeechState = state as 'speaking' | 'silent' | 'processing';

  // UI 업데이트
  updateMicrophoneIndicator(state);
  updateStatusText(state);
}
```

## 2. UI 컴포넌트 구현 방법

### 방법 1: 마이크 아이콘 애니메이션 (추천)

가장 직관적인 방법입니다. 사용자가 말할 때 마이크 아이콘이 시각적으로 반응합니다.

```typescript
function updateMicrophoneIndicator(state: string) {
  const micIcon = document.getElementById('microphone-icon');

  // 기존 클래스 제거
  micIcon.classList.remove('speaking', 'silent', 'processing');

  // 새 상태 클래스 추가
  micIcon.classList.add(state);
}
```

**CSS 스타일 예시**:
```css
#microphone-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

/* 대기 중 (침묵) */
#microphone-icon.silent {
  background-color: #e0e0e0;
  border: 2px solid #9e9e9e;
}

/* 말하는 중 */
#microphone-icon.speaking {
  background-color: #4caf50;
  border: 2px solid #2e7d32;
  animation: pulse 1.5s ease-in-out infinite;
  box-shadow: 0 0 20px rgba(76, 175, 80, 0.6);
}

/* 처리 중 */
#microphone-icon.processing {
  background-color: #2196f3;
  border: 2px solid #1565c0;
  animation: spin 1s linear infinite;
}

/* 펄스 애니메이션 (말하는 중) */
@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 20px rgba(76, 175, 80, 0.6);
  }
  50% {
    transform: scale(1.1);
    box-shadow: 0 0 30px rgba(76, 175, 80, 0.8);
  }
}

/* 회전 애니메이션 (처리 중) */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
```

### 방법 2: 파형 시각화 (고급)

실시간 오디오 파형을 표시하면 더욱 생동감 있는 UI가 됩니다.

```typescript
// 파형 캔버스 설정
const waveformCanvas = document.getElementById('waveform') as HTMLCanvasElement;
const waveformCtx = waveformCanvas.getContext('2d');
let animationId: number | null = null;

function updateWaveform(state: string) {
  if (state === 'speaking') {
    startWaveformAnimation();
  } else {
    stopWaveformAnimation();
  }
}

function startWaveformAnimation() {
  if (animationId !== null) return;

  const bars = 20;
  const barWidth = waveformCanvas.width / bars;

  function animate() {
    waveformCtx.clearRect(0, 0, waveformCanvas.width, waveformCanvas.height);

    for (let i = 0; i < bars; i++) {
      const height = Math.random() * waveformCanvas.height * 0.8 + 10;
      const x = i * barWidth;
      const y = (waveformCanvas.height - height) / 2;

      waveformCtx.fillStyle = '#4caf50';
      waveformCtx.fillRect(x, y, barWidth - 2, height);
    }

    animationId = requestAnimationFrame(animate);
  }

  animate();
}

function stopWaveformAnimation() {
  if (animationId !== null) {
    cancelAnimationFrame(animationId);
    animationId = null;
    waveformCtx.clearRect(0, 0, waveformCanvas.width, waveformCanvas.height);
  }
}

function handleSpeechState(state: string, timestamp: number) {
  currentSpeechState = state as any;
  updateMicrophoneIndicator(state);
  updateWaveform(state);  // 파형 업데이트 추가
  updateStatusText(state);
}
```

### 방법 3: 상태 텍스트 표시

간단하지만 명확한 피드백을 제공합니다.

```typescript
function updateStatusText(state: string) {
  const statusElement = document.getElementById('speech-status');

  const statusMessages = {
    speaking: '🎤 말씀하세요...',
    silent: '👂 듣고 있습니다...',
    processing: '⏳ 처리 중...'
  };

  statusElement.textContent = statusMessages[state] || '';
  statusElement.className = `status-${state}`;
}
```

**CSS 스타일**:
```css
#speech-status {
  font-size: 14px;
  font-weight: 500;
  padding: 8px 16px;
  border-radius: 20px;
  transition: all 0.3s ease;
}

.status-speaking {
  color: #2e7d32;
  background-color: #e8f5e9;
}

.status-silent {
  color: #616161;
  background-color: #f5f5f5;
}

.status-processing {
  color: #1565c0;
  background-color: #e3f2fd;
}
```

## 3. React 컴포넌트 예시

React를 사용하는 경우 다음과 같이 구현할 수 있습니다.

```tsx
import { useState, useEffect } from 'react';

interface SpeechStateIndicatorProps {
  websocket: WebSocket | null;
}

export function SpeechStateIndicator({ websocket }: SpeechStateIndicatorProps) {
  const [speechState, setSpeechState] = useState<'speaking' | 'silent' | 'processing'>('silent');

  useEffect(() => {
    if (!websocket) return;

    const handleMessage = (event: MessageEvent) => {
      const message = JSON.parse(event.data);

      if (message.type === 'speech_state') {
        setSpeechState(message.state);
      }
    };

    websocket.addEventListener('message', handleMessage);

    return () => {
      websocket.removeEventListener('message', handleMessage);
    };
  }, [websocket]);

  return (
    <div className="speech-state-indicator">
      <div className={`microphone-icon ${speechState}`}>
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
      </div>

      <div className={`status-text status-${speechState}`}>
        {speechState === 'speaking' && '🎤 말씀하세요...'}
        {speechState === 'silent' && '👂 듣고 있습니다...'}
        {speechState === 'processing' && '⏳ 처리 중...'}
      </div>
    </div>
  );
}
```

**React 컴포넌트 CSS**:
```css
.speech-state-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.microphone-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.microphone-icon.silent {
  background-color: #e0e0e0;
  color: #757575;
}

.microphone-icon.speaking {
  background-color: #4caf50;
  color: white;
  animation: pulse 1.5s ease-in-out infinite;
}

.microphone-icon.processing {
  background-color: #2196f3;
  color: white;
  animation: spin 1s linear infinite;
}

.status-text {
  font-size: 14px;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 16px;
}

.status-speaking {
  color: #2e7d32;
  background-color: #e8f5e9;
}

.status-silent {
  color: #616161;
  background-color: #f5f5f5;
}

.status-processing {
  color: #1565c0;
  background-color: #e3f2fd;
}
```

## 4. Vue.js 컴포넌트 예시

```vue
<template>
  <div class="speech-state-indicator">
    <div :class="['microphone-icon', speechState]">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
        <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
      </svg>
    </div>

    <div :class="['status-text', `status-${speechState}`]">
      {{ statusMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';

interface Props {
  websocket: WebSocket | null;
}

const props = defineProps<Props>();

const speechState = ref<'speaking' | 'silent' | 'processing'>('silent');

const statusMessage = computed(() => {
  switch (speechState.value) {
    case 'speaking':
      return '🎤 말씀하세요...';
    case 'silent':
      return '👂 듣고 있습니다...';
    case 'processing':
      return '⏳ 처리 중...';
    default:
      return '';
  }
});

const handleMessage = (event: MessageEvent) => {
  const message = JSON.parse(event.data);

  if (message.type === 'speech_state') {
    speechState.value = message.state;
  }
};

onMounted(() => {
  if (props.websocket) {
    props.websocket.addEventListener('message', handleMessage);
  }
});

onUnmounted(() => {
  if (props.websocket) {
    props.websocket.removeEventListener('message', handleMessage);
  }
});
</script>

<style scoped>
/* 위의 CSS 스타일과 동일 */
</style>
```

## 5. Claude CLI로 구현하기

프론트엔드 프로젝트 디렉토리로 이동한 후 Claude CLI를 실행하세요.

### 단계별 명령어

```bash
# 1. 프론트엔드 디렉토리로 이동
cd /path/to/your/frontend/project

# 2. Claude CLI 실행
claude

# 3. Claude에게 다음과 같이 요청
```

**Claude CLI 프롬프트 예시**:

```
백엔드에서 WebSocket으로 speech_state 메시지를 보내고 있어.
메시지 형식은 다음과 같아:

{
  "type": "speech_state",
  "state": "speaking" | "silent" | "processing",
  "timestamp": 1702345678901
}

현재 프로젝트에 다음 기능을 구현해줘:

1. WebSocket 메시지 핸들러에 speech_state 케이스 추가
2. 음성 상태에 따라 마이크 아이콘이 시각적으로 변하는 UI 컴포넌트 생성
   - speaking: 초록색 배경, 펄스 애니메이션
   - silent: 회색 배경, 정적
   - processing: 파란색 배경, 회전 애니메이션
3. 상태 텍스트 표시 ("말씀하세요...", "듣고 있습니다...", "처리 중...")

현재 사용 중인 프레임워크는 [React/Vue/Vanilla JS]이고,
WebSocket 연결은 [파일명과 위치]에서 관리하고 있어.
```

### React 프로젝트용 상세 프롬프트

```
React 프로젝트에 음성 상태 인디케이터를 추가하고 싶어.

요구사항:
1. src/components/SpeechStateIndicator.tsx 파일 생성
2. props로 websocket 객체를 받음
3. speech_state 메시지를 수신하여 상태 업데이트
4. 마이크 아이콘과 상태 텍스트를 표시하는 UI
5. CSS 애니메이션 포함 (펄스, 회전)

기존 WebSocket 연결 코드 위치: src/hooks/useWebSocket.ts
메인 컴포넌트 위치: src/App.tsx

위 가이드 문서(FRONTEND_IMPLEMENTATION_GUIDE.md)의 React 예시를 참고해서 구현해줘.
```

### Vue.js 프로젝트용 상세 프롬프트

```
Vue.js 프로젝트에 음성 상태 인디케이터를 추가하고 싶어.

요구사항:
1. src/components/SpeechStateIndicator.vue 파일 생성
2. Composition API 사용
3. props로 websocket 객체를 받음
4. speech_state 메시지를 수신하여 상태 업데이트
5. 마이크 아이콘과 상태 텍스트를 표시하는 UI
6. CSS 애니메이션 포함 (펄스, 회전)

기존 WebSocket 연결 코드 위치: src/composables/useWebSocket.ts
메인 컴포넌트 위치: src/App.vue

위 가이드 문서(FRONTEND_IMPLEMENTATION_GUIDE.md)의 Vue 예시를 참고해서 구현해줘.
```

### Vanilla JS 프로젝트용 상세 프롬프트

```
Vanilla JavaScript 프로젝트에 음성 상태 인디케이터를 추가하고 싶어.

요구사항:
1. 기존 WebSocket 메시지 핸들러에 speech_state 케이스 추가
2. updateMicrophoneIndicator() 함수 구현
3. HTML에 마이크 아이콘과 상태 텍스트 엘리먼트 추가
4. CSS 애니메이션 정의 (펄스, 회전)

기존 WebSocket 연결 코드 위치: js/websocket.js
메인 HTML 파일: index.html

위 가이드 문서(FRONTEND_IMPLEMENTATION_GUIDE.md)의 Vanilla JS 예시를 참고해서 구현해줘.
```

## 6. 테스트 방법

구현 후 다음과 같이 테스트하세요:

1. **WebSocket 연결 확인**
   ```javascript
   console.log('WebSocket connected:', websocket.readyState === WebSocket.OPEN);
   ```

2. **메시지 수신 로그**
   ```javascript
   websocket.onmessage = (event) => {
     const message = JSON.parse(event.data);
     console.log('Received:', message.type, message);
     // 기존 핸들러...
   };
   ```

3. **실제 음성 테스트**
   - 말하기 시작 → 마이크 아이콘이 초록색으로 변하고 펄스 애니메이션 표시
   - 말 멈춤 → 300ms 후 회색으로 변함
   - 계속 말하기 → 초록색 유지

4. **브라우저 개발자 도구**
   ```
   Network → WS → Messages 탭에서 speech_state 메시지 확인
   ```

## 7. 문제 해결

### 메시지가 수신되지 않는 경우

```javascript
// 디버깅 코드 추가
websocket.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('[WS] Message type:', message.type);

  if (message.type === 'speech_state') {
    console.log('[WS] Speech state:', message.state, 'at', new Date(message.timestamp));
  }

  // 기존 핸들러...
};
```

### 애니메이션이 작동하지 않는 경우

1. CSS 클래스가 제대로 추가되었는지 확인
   ```javascript
   console.log('Microphone classes:', micIcon.className);
   ```

2. 브라우저 호환성 확인 (CSS 애니메이션 지원)
   ```javascript
   console.log('Animation support:',
     CSS.supports('animation', 'pulse 1s ease-in-out infinite'));
   ```

### 상태 전환이 너무 빠른 경우

디바운싱 추가:
```typescript
let stateChangeTimeout: NodeJS.Timeout | null = null;

function handleSpeechState(state: string, timestamp: number) {
  // 이전 타이머 취소
  if (stateChangeTimeout) {
    clearTimeout(stateChangeTimeout);
  }

  // 50ms 디바운싱
  stateChangeTimeout = setTimeout(() => {
    currentSpeechState = state as any;
    updateMicrophoneIndicator(state);
    updateStatusText(state);
  }, 50);
}
```

## 8. 추가 개선 아이디어

### 1. 음성 레벨 표시
백엔드에서 에너지 레벨도 전송하도록 수정하면 실시간 볼륨 미터 구현 가능

### 2. 진동 피드백 (모바일)
```javascript
if (state === 'speaking' && navigator.vibrate) {
  navigator.vibrate(50);
}
```

### 3. 소리 피드백
```javascript
const beep = new Audio('/sounds/beep.mp3');
if (state === 'speaking') {
  beep.play();
}
```

### 4. 접근성 개선
```html
<div
  role="status"
  aria-live="polite"
  aria-label="음성 상태"
>
  {statusMessage}
</div>
```

## 요약

1. WebSocket 메시지 핸들러에 `speech_state` 케이스 추가
2. UI 컴포넌트 생성 (마이크 아이콘 + 상태 텍스트)
3. CSS 애니메이션 정의 (펄스, 회전)
4. 상태에 따라 UI 업데이트
5. Claude CLI로 프레임워크별 구현 요청

이 가이드를 참고하여 Claude CLI에게 구현을 요청하면 됩니다!
