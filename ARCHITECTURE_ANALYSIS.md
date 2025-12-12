# Live Interpreter Backend - 아키텍처 분석 문서

## 📋 목차
1. [시스템 개요](#시스템-개요)
2. [구성 의도 및 설계 철학](#구성-의도-및-설계-철학)
3. [핵심 컴포넌트 분석](#핵심-컴포넌트-분석)
4. [Gemini API 통합 상세](#gemini-api-통합-상세)
5. [데이터 흐름 및 메시지 프로토콜](#데이터-흐름-및-메시지-프로토콜)
6. [UI 통신 방식](#ui-통신-방식)
7. [VAD (Voice Activity Detection) 시스템](#vad-voice-activity-detection-시스템)
8. [에러 처리 및 상태 관리](#에러-처리-및-상태-관리)

---

## 시스템 개요

### 프로젝트 목적
실시간 음성 통역 시스템의 백엔드 서버로, 클라이언트(브라우저/프론트엔드)와 Google Gemini Live API 사이의 **브로커(Broker)** 역할을 수행합니다.

### 기술 스택
```yaml
프레임워크: FastAPI 0.124.2
비동기 런타임: uvicorn[standard] 0.38.0
WebSocket: websockets 15.0.1
AI 모델: Google GenAI SDK 1.55.0
데이터 검증: Pydantic 2.7.0
환경 설정: python-dotenv 1.2.1
```

### 사용 모델
```python
MODEL_NAME = "gemini-2.5-flash-native-audio-preview-09-2025"

# 특징:
# - Gemini 2.5 Flash 계열의 Native Audio 지원 모델
# - 음성 입력을 직접 처리하여 음성 출력 생성
# - 2025년 9월 프리뷰 버전 (최신 멀티모달 기능)
```

---

## 구성 의도 및 설계 철학

### 1. 계층화된 아키텍처 (Layered Architecture)

```
┌─────────────────────────────────────────────┐
│         Client (Browser/React App)          │
│              WebSocket 연결                  │
└─────────────────────────────────────────────┘
                    ↓ ↑
┌─────────────────────────────────────────────┐
│        FastAPI WebSocket Endpoint           │
│           (app/main.py:42-46)               │
└─────────────────────────────────────────────┘
                    ↓ ↑
┌─────────────────────────────────────────────┐
│         WebSocketHandler Layer              │
│         (app/websocket/handler.py)          │
│   - 메시지 라우팅                              │
│   - 세션 관리                                 │
│   - 콜백 처리                                 │
└─────────────────────────────────────────────┘
                    ↓ ↑
┌─────────────────────────────────────────────┐
│           GeminiService Layer               │
│      (app/services/gemini_service.py)       │
│   - Gemini Live API 통신                     │
│   - VAD (음성 활동 감지)                       │
│   - 오디오/텍스트 처리                          │
│   - 턴 상태 관리                               │
└─────────────────────────────────────────────┘
                    ↓ ↑
┌─────────────────────────────────────────────┐
│        Google Gemini Live API               │
│     (WebSocket 기반 실시간 통신)                │
└─────────────────────────────────────────────┘
```

### 2. 설계 원칙

#### A. 단일 책임 원칙 (Single Responsibility)
- **app/main.py**: FastAPI 애플리케이션 부트스트랩만 담당
- **WebSocketHandler**: 클라이언트 메시지 라우팅만 처리
- **GeminiService**: Gemini API와의 통신만 관리
- **models/messages.py**: 메시지 스키마 정의만 담당

#### B. 의존성 역전 (Dependency Inversion)
```python
# WebSocketHandler는 구체적 구현이 아닌 콜백 인터페이스에 의존
class GeminiService:
    def __init__(
        self,
        on_input_transcription: Callable[[str, bool], Awaitable[None]],
        on_output_transcription: Callable[[str, bool], Awaitable[None]],
        on_audio_response: Callable[[str, int], Awaitable[None]],
        on_turn_complete: Callable[[str, str], Awaitable[None]],
        on_speech_state: Optional[Callable[[str, int], Awaitable[None]]] = None,
        # ...
    ):
```
→ GeminiService는 WebSocketHandler의 구현을 알 필요 없이, 콜백만으로 통신

#### C. 비동기 우선 (Async-First)
```python
# 모든 I/O 작업은 비동기 처리
async def handle(self) -> None:
    await self.websocket.accept()
    while True:
        data = await self.websocket.receive_text()
        # ...

async def send_audio(self, base64_audio: str) -> None:
    await self.session.send_realtime_input(audio=blob)
```
→ 동시 다중 세션 처리 가능, 블로킹 없음

---

## 핵심 컴포넌트 분석

### 1. FastAPI 애플리케이션 (app/main.py)

#### 초기화 프로세스
```python
# 1. 환경 변수 로드 (.env 파일을 최우선으로 로드)
load_dotenv(override=True)  # 중요: override=True로 .env 우선 적용

# 2. CORS 설정 (크로스 오리진 요청 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),  # 환경변수 기반 동적 설정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 엔드포인트 구성
```python
# ✅ Health Check (모니터링/헬스체크용)
@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

# 🔌 WebSocket Endpoint (실시간 통역 세션)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    handler = WebSocketHandler(websocket)
    await handler.handle()
```

### 2. WebSocket 핸들러 (app/websocket/handler.py)

#### 세션 생명주기 관리
```python
class WebSocketHandler:
    async def handle(self) -> None:
        # 1. 연결 수락
        await self.websocket.accept()

        try:
            # 2. 메시지 루프
            while True:
                data = await self.websocket.receive_text()
                message = parse_client_message(data)

                # 3. 메시지 타입별 라우팅
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
            # 클라이언트 연결 종료
        except Exception as exc:
            # 에러 발생 시 클라이언트에 에러 전송
            await send_error(self.websocket, str(exc))
        finally:
            # 4. 리소스 정리
            await self._cleanup()
```

#### 초기화 처리 (_handle_init)
```python
async def _handle_init(self, message: InitMessage) -> None:
    # 1. 세션 ID 생성
    self.session_id = str(uuid.uuid4())

    # 2. GeminiService 인스턴스 생성 (콜백 주입)
    self.gemini_service = GeminiService(
        on_input_transcription=self._send_input_transcription,
        on_output_transcription=self._send_output_transcription,
        on_audio_response=self._send_audio_response,
        on_turn_complete=self._send_turn_complete,
        on_speech_state=self._send_speech_state,
        input_sample_rate=message.config.sampleRate,
    )

    # 3. Gemini Live API 연결
    await self.gemini_service.connect()

    # 4. 클라이언트에 연결 완료 알림
    connected = ConnectedMessage(sessionId=self.session_id)
    await self.websocket.send_json(connected.model_dump())
```

### 3. Gemini 서비스 (app/services/gemini_service.py)

#### Gemini Live API 연결 프로세스
```python
async def connect(self) -> None:
    # 1. Gemini Live API 설정
    config = {
        "generation_config": {
            "response_modalities": ["AUDIO"],  # 음성 출력 모드
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": "Zephyr"  # 음성 프리셋
                    }
                }
            },
        },
        "system_instruction": {
            "parts": [{"text": SYSTEM_INSTRUCTION}]
        },
        "tools": [],
        "input_audio_transcription": {},   # 입력 음성 인식 활성화
        "output_audio_transcription": {},  # 출력 음성 인식 활성화
    }

    # 2. 세션 매니저 생성 (컨텍스트 매니저 패턴)
    self.session_manager = self.client.aio.live.connect(
        model=MODEL_NAME,
        config=config
    )

    # 3. 세션 시작
    self.session = await self.session_manager.__aenter__()

    # 4. 메시지 수신 태스크 시작
    self.receive_task = asyncio.create_task(self._receive_messages())
```

#### 시스템 지시문 (SYSTEM_INSTRUCTION)
```python
SYSTEM_INSTRUCTION = """You are an ultra-fast, bidirectional simultaneous interpreter for a voice-to-voice translation system.

### CORE INSTRUCTIONS:
1. Auto-detect: Korean → English, English → Korean.
2. Output ONLY translated speech text with zero fluff.
3. Favor natural spoken tone with breathable punctuation.
"""
```
→ Gemini 모델의 역할과 동작 방식을 정의

---

## Gemini API 통합 상세

### 1. 모델 호출 방식

#### A. 실시간 오디오 스트리밍
```python
async def send_audio(self, base64_audio: str) -> None:
    # 1. Base64 디코딩
    audio_bytes = base64.b64decode(base64_audio)

    # 2. VAD (음성 활동 감지) 체크
    if self.vad:
        should_forward, energy = self.vad.should_forward(audio_bytes)
        if not should_forward:
            return  # 무음 구간은 전송하지 않음

    # 3. Gemini Live API 형식으로 변환
    mime_type = f"audio/pcm;rate={self.input_sample_rate}"
    blob = genai.types.Blob(data=audio_bytes, mime_type=mime_type)

    # 4. 실시간 입력 전송 (스트리밍)
    await self.session.send_realtime_input(audio=blob)
```

#### B. 메시지 수신 루프
```python
async def _receive_messages(self) -> None:
    while True:  # 무한 루프로 지속적 수신
        try:
            async for message in self.session.receive():
                await self._handle_message(message)

            # 턴 완료 후에도 루프 계속 유지
            await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            raise  # disconnect 시 정상 종료
        except Exception as exc:
            logger.error("수신 루프 에러: %s", exc)
            raise
```

### 2. Gemini 응답 메시지 처리

```python
async def _handle_message(self, message: LiveServerMessage) -> None:
    # 1. 입력 음성 인식 (사용자가 말한 내용)
    input_trans = getattr(message.server_content, "input_transcription", None)
    if input_trans and input_trans.text:
        self.current_input_text += input_trans.text
        await self.on_input_transcription(self.current_input_text, False)

    # 2. 출력 음성 인식 (AI가 생성한 번역 텍스트)
    output_trans = getattr(message.server_content, "output_transcription", None)
    if output_trans and output_trans.text:
        self.current_output_text += output_trans.text
        await self.on_output_transcription(self.current_output_text, False)

    # 3. 모델 턴 응답 (AI가 생성한 오디오)
    model_turn = getattr(message.server_content, "model_turn", None)
    if model_turn and model_turn.parts:
        for part in model_turn.parts:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                # 바이너리 오디오를 Base64로 인코딩
                encoded = base64.b64encode(inline.data).decode("ascii")
                await self.on_audio_response(encoded, 24000)

    # 4. 턴 완료 (대화 턴 종료)
    if getattr(message.server_content, "turn_complete", False):
        await self.on_input_transcription(self.current_input_text, True)
        await self.on_output_transcription(self.current_output_text, True)
        await self.on_turn_complete(self.current_input_text, self.current_output_text)

        # 상태 리셋
        self.current_input_text = ""
        self.current_output_text = ""
        self.is_turn_complete = True
        self.turn_complete_time = time.time()
```

### 3. 모델 구성 파라미터

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| `model` | `gemini-2.5-flash-native-audio-preview-09-2025` | 음성 입출력 지원 Gemini 2.5 Flash |
| `response_modalities` | `["AUDIO"]` | 응답을 음성으로 생성 |
| `voice_name` | `"Zephyr"` | Gemini의 Zephyr 음성 프리셋 사용 |
| `input_audio_transcription` | `{}` | 사용자 음성 자동 인식 활성화 |
| `output_audio_transcription` | `{}` | AI 음성 자동 인식 활성화 |
| `system_instruction` | 통역 지시문 | 양방향 동시통역 역할 부여 |

---

## 데이터 흐름 및 메시지 프로토콜

### 1. 클라이언트 → 서버 메시지

#### A. InitMessage (세션 초기화)
```typescript
{
  type: "init",
  config: {
    language: "auto" | "ko" | "en",  // 입력 언어
    useWhisper: boolean,              // Whisper STT 사용 여부 (현재 미구현)
    sampleRate: number                // 샘플레이트 (16000Hz 권장)
  }
}
```

#### B. AudioMessage (오디오 청크 전송)
```typescript
{
  type: "audio",
  data: string,      // Base64 인코딩된 PCM 오디오
  timestamp: number  // 클라이언트 타임스탬프
}
```

#### C. InterruptMessage (AI 응답 중단)
```typescript
{
  type: "interrupt"
}
```

#### D. CloseMessage (세션 종료)
```typescript
{
  type: "close"
}
```

### 2. 서버 → 클라이언트 메시지

#### A. ConnectedMessage (연결 완료)
```typescript
{
  type: "connected",
  sessionId: string  // UUID 세션 ID
}
```

#### B. TranscriptionMessage (음성 인식 결과)
```typescript
{
  type: "input_transcription" | "output_transcription",
  text: string,           // 인식된 텍스트
  isFinal: boolean,       // 최종 결과 여부
  language?: "ko" | "en"  // 언어 (최종 결과일 때만)
}
```

#### C. AudioResponseMessage (AI 음성 응답)
```typescript
{
  type: "audio_response",
  data: string,      // Base64 인코딩된 PCM 오디오
  sampleRate: number // 24000Hz (Gemini 고정값)
}
```

#### D. TurnCompleteMessage (턴 완료)
```typescript
{
  type: "turn_complete",
  inputText: string,   // 사용자가 말한 최종 텍스트
  outputText: string   // AI가 생성한 최종 번역 텍스트
}
```

#### E. SpeechStateMessage (음성 상태 알림)
```typescript
{
  type: "speech_state",
  state: "speaking" | "silent" | "processing",
  timestamp: number
}
```

#### F. ErrorMessage (에러 알림)
```typescript
{
  type: "error",
  message: string,
  code?: string  // "ALREADY_INIT", "NOT_READY" 등
}
```

### 3. 전체 데이터 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                     Client (Browser)                        │
└─────────────────────────────────────────────────────────────┘
                           ↓ ↑
              [InitMessage] ↓ ↑ [ConnectedMessage]
              [AudioMessage]↓ ↑ [TranscriptionMessage]
                            ↓ ↑ [AudioResponseMessage]
                            ↓ ↑ [SpeechStateMessage]
                            ↓ ↑ [TurnCompleteMessage]
┌─────────────────────────────────────────────────────────────┐
│               WebSocketHandler (app/websocket)              │
│  - 메시지 파싱 및 라우팅                                         │
│  - 콜백 함수를 통한 응답 전송                                     │
└─────────────────────────────────────────────────────────────┘
                           ↓ ↑
          [Audio Blob PCM] ↓ ↑ [LiveServerMessage]
┌─────────────────────────────────────────────────────────────┐
│             GeminiService (app/services)                    │
│  - VAD 필터링                                                 │
│  - Gemini Live API 스트리밍                                   │
│  - 턴 상태 관리                                                │
└─────────────────────────────────────────────────────────────┘
                           ↓ ↑
              [Realtime Audio Input] ↓ ↑ [Server Content]
┌─────────────────────────────────────────────────────────────┐
│           Google Gemini Live API (WebSocket)                │
│  - gemini-2.5-flash-native-audio-preview-09-2025            │
│  - 음성 입력 → 음성 출력 (End-to-End)                            │
│  - 실시간 transcription                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## UI 통신 방식

### 1. WebSocket 연결 설정

#### 클라이언트 연결 예시
```javascript
// WebSocket 연결
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  // 1. 세션 초기화
  ws.send(JSON.stringify({
    type: 'init',
    config: {
      language: 'auto',
      useWhisper: false,
      sampleRate: 16000
    }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'connected':
      console.log('Session ID:', message.sessionId);
      break;

    case 'input_transcription':
      updateInputText(message.text, message.isFinal);
      break;

    case 'output_transcription':
      updateOutputText(message.text, message.isFinal);
      break;

    case 'audio_response':
      playAudio(message.data, message.sampleRate);
      break;

    case 'turn_complete':
      saveTurnHistory(message.inputText, message.outputText);
      break;

    case 'speech_state':
      updateSpeechIndicator(message.state);
      break;

    case 'error':
      showError(message.message);
      break;
  }
};
```

### 2. 오디오 스트리밍 방식

#### 마이크 입력 → 서버 전송
```javascript
// MediaRecorder로 오디오 캡처
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => {
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'audio/webm;codecs=pcm'
    });

    mediaRecorder.ondataavailable = async (event) => {
      // 1. 오디오 청크를 PCM으로 변환
      const audioBuffer = await event.data.arrayBuffer();
      const pcmData = convertToPCM16(audioBuffer);

      // 2. Base64 인코딩
      const base64Audio = btoa(
        String.fromCharCode(...new Uint8Array(pcmData))
      );

      // 3. 서버로 전송
      ws.send(JSON.stringify({
        type: 'audio',
        data: base64Audio,
        timestamp: Date.now()
      }));
    };

    mediaRecorder.start(100); // 100ms 간격으로 청크 생성
  });
```

#### 서버 응답 오디오 → 재생
```javascript
function playAudio(base64Data, sampleRate) {
  // 1. Base64 디코딩
  const binaryString = atob(base64Data);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  // 2. AudioBuffer 생성
  const audioContext = new AudioContext({ sampleRate });
  const audioBuffer = audioContext.createBuffer(
    1,                              // 모노 채널
    bytes.length / 2,               // PCM16 = 2바이트/샘플
    sampleRate
  );

  const channelData = audioBuffer.getChannelData(0);
  const int16Array = new Int16Array(bytes.buffer);

  for (let i = 0; i < int16Array.length; i++) {
    channelData[i] = int16Array[i] / 32768.0; // PCM16 → Float32
  }

  // 3. 재생
  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  source.start();
}
```

### 3. UI 상태 관리 예시

```javascript
class InterpreterUI {
  constructor() {
    this.ws = null;
    this.sessionId = null;
    this.isRecording = false;
    this.inputText = '';
    this.outputText = '';
  }

  connect() {
    this.ws = new WebSocket('ws://localhost:8000/ws');
    this.ws.onmessage = this.handleMessage.bind(this);
  }

  handleMessage(event) {
    const msg = JSON.parse(event.data);

    if (msg.type === 'connected') {
      this.sessionId = msg.sessionId;
      this.onConnected();
    } else if (msg.type === 'input_transcription') {
      this.inputText = msg.text;
      this.updateInputDisplay(msg.text, msg.isFinal);
    } else if (msg.type === 'output_transcription') {
      this.outputText = msg.text;
      this.updateOutputDisplay(msg.text, msg.isFinal);
    } else if (msg.type === 'audio_response') {
      this.playAudioChunk(msg.data, msg.sampleRate);
    } else if (msg.type === 'turn_complete') {
      this.onTurnComplete(msg.inputText, msg.outputText);
    } else if (msg.type === 'speech_state') {
      this.updateSpeechIndicator(msg.state);
    }
  }

  startRecording() {
    // 마이크 활성화 및 오디오 스트리밍 시작
  }

  stopRecording() {
    // 마이크 비활성화
  }

  interrupt() {
    this.ws.send(JSON.stringify({ type: 'interrupt' }));
  }

  close() {
    this.ws.send(JSON.stringify({ type: 'close' }));
  }
}
```

---

## VAD (Voice Activity Detection) 시스템

### 1. SimpleVAD 구현

```python
class SimpleVAD:
    """PCM 진폭 기반 음성 활동 감지기"""

    def __init__(self, threshold: int, hangover_frames: int = 3):
        self.threshold = threshold         # 에너지 임계값
        self.hangover_frames = hangover_frames  # 무음 허용 프레임 수
        self._silence_frames = 0
        self._in_speech = False

    def should_forward(self, audio_bytes: bytes) -> Tuple[bool, float]:
        # 1. PCM 샘플 변환
        samples = array("h")  # signed 16-bit integers
        samples.frombytes(audio_bytes)

        # 2. 평균 에너지 계산
        avg_energy = sum(abs(sample) for sample in samples) / len(samples)

        # 3. 임계값 체크
        if avg_energy >= self.threshold:
            self._in_speech = True
            self._silence_frames = 0
            return True, avg_energy

        # 4. Hangover 처리 (자연스러운 말 끊김 허용)
        if self._in_speech and self._silence_frames < self.hangover_frames:
            self._silence_frames += 1
            return True, avg_energy

        # 5. 무음으로 판정
        self._in_speech = False
        return False, avg_energy
```

### 2. VAD 설정

```python
# 환경 변수로 제어
DEFAULT_VAD_THRESHOLD = int(os.getenv("VAD_THRESHOLD", "500"))
DEFAULT_VAD_HANGOVER = int(os.getenv("VAD_HANGOVER_FRAMES", "15"))

# Hangover 효과:
# 15 frames × 20ms(100ms chunk 기준) ≈ 300ms 무음 허용
# → 자연스러운 말하기 패턴에서 단어 사이 쉼표 처리
```

### 3. VAD 동작 플로우

```
오디오 청크 수신
    ↓
평균 에너지 계산
    ↓
┌──────────────────────────────┐
│ 에너지 >= 임계값?               │
└──────────────────────────────┘
    ↓ YES          ↓ NO
발화 시작      ┌──────────────┐
전송 허용      │ 발화 중?       │
             └──────────────┘
                  ↓ YES    ↓ NO
              ┌────────────────┐
              │ Hangover 남음?  │
              └────────────────┘
                ↓ YES    ↓ NO
              전송 허용  차단
                        (무음)
```

---

## 에러 처리 및 상태 관리

### 1. 에러 처리 계층

#### A. WebSocket 레벨
```python
try:
    while True:
        data = await self.websocket.receive_text()
        # ...
except WebSocketDisconnect:
    logger.info("클라이언트 연결 종료")
except Exception as exc:
    logger.exception("WebSocket 에러")
    await send_error(self.websocket, str(exc))
finally:
    await self._cleanup()
```

#### B. Gemini Service 레벨
```python
try:
    await self.session.send_realtime_input(audio=blob)
except Exception as exc:
    logger.error("Gemini 전송 실패: %s", exc)
    raise  # WebSocketHandler로 전파
```

### 2. 상태 관리

#### A. 턴 상태 (Turn State)
```python
class GeminiService:
    def __init__(self, ...):
        self.current_input_text = ""      # 현재 턴 입력 누적
        self.current_output_text = ""     # 현재 턴 출력 누적
        self.is_turn_complete = False     # 턴 완료 플래그
        self.turn_complete_time = None    # 턴 완료 시각
```

#### B. 턴 완료 후 재시작 로직
```python
# 턴 완료 시
if turn_complete:
    self.is_turn_complete = True
    self.turn_complete_time = time.time()

# 새 오디오 수신 시
if self.is_turn_complete and energy > threshold:
    elapsed = time.time() - self.turn_complete_time

    # 최소 100ms 대기 (Gemini 세션 안정화)
    if elapsed < 0.1:
        await asyncio.sleep(0.1 - elapsed)

    logger.info("새 턴 시작 (%.2fs 경과)", elapsed)
    self.is_turn_complete = False
```

### 3. 리소스 정리 (Cleanup)

```python
async def _cleanup(self) -> None:
    if self.gemini_service:
        await self.gemini_service.disconnect()
        self.gemini_service = None

async def disconnect(self) -> None:
    # 1. 수신 태스크 취소
    if self.receive_task:
        self.receive_task.cancel()
        await self.receive_task  # CancelledError 대기

    # 2. 세션 매니저 종료
    if self.session_manager:
        await self.session_manager.__aexit__(None, None, None)

    # 3. 참조 해제
    self.session = None
```

---

## 보안 고려사항

### ⚠️ 현재 코드의 보안 이슈

```python
# WARNING: SSL 인증서 검증 비활성화 (개발 전용)
def _unverified_create_default_context(*args, **kwargs):
    context = _original_create_default_context(*args, **kwargs)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # ❌ 프로덕션에서 절대 금지
    return context
```

### 권장 사항
1. **프로덕션 배포 전 SSL 검증 복구**
2. **API 키 환경변수 관리** (.env 파일을 .gitignore에 추가)
3. **CORS 오리진 화이트리스트** (프로덕션 도메인만 허용)
4. **Rate Limiting** 추가 (DDoS 방지)
5. **인증/인가 시스템** 추가 (무분별한 세션 생성 방지)

---

## 성능 최적화 요소

### 1. VAD를 통한 대역폭 절약
```
VAD 활성화:
무음 구간 차단 → Gemini API 호출 감소 → 비용 절감 + 지연시간 개선

예시:
- 총 오디오: 10초
- 실제 발화: 6초
- 무음: 4초
→ VAD로 40% 데이터 절감
```

### 2. 비동기 I/O
- 동시 다중 세션 처리 가능
- 블로킹 없이 오디오 스트리밍

### 3. 증분 Transcription
```python
# 부분 결과를 누적하여 전송
self.current_input_text += chunk_text
await self.on_input_transcription(self.current_input_text, False)

# 최종 결과만 별도 표시
await self.on_input_transcription(self.current_input_text, True)
```
→ 사용자에게 실시간 피드백 제공

---

## 주요 환경 변수

| 환경 변수 | 기본값 | 설명 |
|-----------|--------|------|
| `GEMINI_API_KEY` | (필수) | Gemini API 인증 키 |
| `HOST` | `localhost` | 서버 호스트 |
| `PORT` | `8000` | 서버 포트 |
| `DEBUG` | `True` | 디버그 모드 (자동 리로드) |
| `CORS_ORIGINS` | `http://localhost:3000,...` | CORS 허용 오리진 |
| `LOG_LEVEL` | `DEBUG` | 로그 레벨 |
| `VAD_THRESHOLD` | `500` | VAD 에너지 임계값 (0=비활성화) |
| `VAD_HANGOVER_FRAMES` | `15` | VAD Hangover 프레임 수 |

---

## 시퀀스 다이어그램

### 전체 흐름

```
Client          FastAPI         WebSocketHandler              GeminiService         Gemini API
  │                  │                  │                           │                   │
  │─────connect─────>│                  │                           │                   │
  │<───accept────────│                  │                           │                   │
  │                  │                  │                           │                   │
  │──InitMessage────>│─────────────────>│                           │                   │
  │                  │                  │──new GeminiService ────>  │                   │
  │                  │                  │                           │──connect()─────>  │
  │                  │                  │                           │<─session open───  │
  │                  │                  │<─start receive task   ────│                   │
  │<───Connected─────│<─────────────────│                           │                   │
  │                  │                  │                           │                   │
  │──AudioMessage────>│────────────────>│                           │                   │
  │                  │                  │──send_audio()──>          │                   │
  │                  │                  │                           │──VAD check ────── │
  │                  │                  │                           │──send_realtime ─> │
  │                  │                  │                           │<─ServerMessage ── │
  │                  │                  │<─on_input_transcription── │                   │
  │<───TranscriptionMsg─<───────────────│                           │                   │
  │                  │                  │                           │<─model_turn  ─────│
  │                  │                  │<─on_audio_response ───────│                   │
  │<───AudioResponse──<─────────────────│                           │                   │
  │                  │                  │                           │<─turn_complete  ──│
  │                  │                  │<─on_turn_complete ────────│                   │
  │<───TurnComplete───<─────────────────│                           │                   │
  │                  │                  │                           │                   │
  │──CloseMessage────>│────────────────>│                           │                   │
  │                  │                  │──cleanup()         ──────>│                   │
  │                  │                  │                           │──disconnect()──>  │
  │<───close─────────│                  │                           │<─session close──  │
  │                  │                  │                           │                   │
```

---

## 마치며

이 문서는 Live Interpreter Backend의 핵심 아키텍처와 구현 세부사항을 다룹니다.

### 핵심 포인트 요약

1. **계층화된 설계**: FastAPI → WebSocketHandler → GeminiService → Gemini API
2. **비동기 우선**: 모든 I/O는 async/await로 처리
3. **콜백 기반 통신**: 의존성 역전 원칙으로 느슨한 결합
4. **실시간 스트리밍**: WebSocket 양방향 통신 + Gemini Live API
5. **VAD 최적화**: 무음 구간 필터링으로 성능 및 비용 절감
6. **Pydantic 검증**: 타입 안전한 메시지 프로토콜

### 다음 단계

- [ ] Whisper STT 통합 (현재 플래그만 존재)
- [ ] 프로덕션 배포 (SSL 인증서 복구, CORS 강화)
- [ ] Rate Limiting 및 인증 시스템
- [ ] 메트릭 수집 (Prometheus/Grafana)
- [ ] E2E 테스트 추가

---

**작성일**: 2025-12-12
**버전**: 1.0.0
