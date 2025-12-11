# Gemini Live Interpreter v2 - 백엔드 분리 아키텍처 설계

## 📋 목차
1. [개요](#개요)
2. [아키텍처 비교](#아키텍처-비교)
3. [기술 스택](#기술-스택)
4. [시스템 아키텍처](#시스템-아키텍처)
5. [프론트엔드 변경사항](#프론트엔드-변경사항)
6. [백엔드 구조](#백엔드-구조)
7. [Rust + Whisper 통합](#rust--whisper-통합)
8. [배포 전략](#배포-전략)
9. [구현 단계](#구현-단계)
10. [프롬프트 가이드](#프롬프트-가이드)

---

## 개요

### 목표
기존 클라이언트 사이드 Gemini Live Interpreter를 백엔드 분리 아키텍처로 재구성하여:
- **보안 강화**: API 키를 백엔드에서 관리
- **성능 개선**: Rust 기반 Whisper STT로 고성능 음성 인식 제공
- **확장성**: 마이크로서비스 아키텍처로 각 컴포넌트 독립 배포

### 핵심 변경사항
- ✅ UI는 기존 React 코드 유지
- ✅ Gemini API 호출을 백엔드로 이동
- ✅ WebSocket 기반 실시간 양방향 통신
- ✅ Rust + Whisper로 STT 성능 향상
- ✅ Netlify (프론트엔드) + Render.com (백엔드) 배포

---

## 아키텍처 비교

### 현재 아키텍처 (v1)
```
┌─────────────────────────────────────────┐
│         브라우저 (React)                 │
│  ┌────────────────────────────────────┐ │
│  │ • 마이크 입력 (Web Audio API)      │ │
│  │ • Gemini API 직접 호출             │ │
│  │ • 오디오 처리 및 재생              │ │
│  │ • 전사 텍스트 표시                 │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
            ↓
    ┌──────────────┐
    │ Gemini API   │
    └──────────────┘
```

**문제점:**
- API 키가 클라이언트에 노출
- 브라우저 성능에 의존적인 오디오 처리
- 서버 사이드 로직 추가 어려움
- 확장성 제한

### 새 아키텍처 (v2)
```
┌─────────────────────────────────────────┐
│   브라우저 (React - Netlify)             │
│  ┌────────────────────────────────────┐ │
│  │ • 마이크 입력 (Web Audio API)      │ │
│  │ • WebSocket 클라이언트             │ │
│  │ • 오디오 재생                      │ │
│  │ • UI/UX                            │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
            ↕ WebSocket (실시간 양방향)
┌─────────────────────────────────────────┐
│  백엔드 서버 (Python - Render.com)       │
│  ┌────────────────────────────────────┐ │
│  │ FastAPI + WebSocket                │ │
│  │ ┌────────────┐  ┌───────────────┐ │ │
│  │ │ Gemini API │  │ Rust Whisper  │ │ │
│  │ │ Integration│  │ STT Service   │ │ │
│  │ └────────────┘  └───────────────┘ │ │
│  │ • 오디오 스트림 처리               │ │
│  │ • 번역 로직                        │ │
│  │ • API 키 관리                      │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**장점:**
- ✅ API 키 보안
- ✅ 고성능 STT (Rust + Whisper)
- ✅ 서버 사이드 로직 확장 용이
- ✅ 각 컴포넌트 독립 배포 및 스케일링

---

## 기술 스택

### 프론트엔드 (Netlify)
| 기술 | 버전 | 역할 |
|------|------|------|
| React | 19.2.1 | UI 프레임워크 |
| TypeScript | 5.8.2 | 타입 안정성 |
| Vite | 6.2.0 | 빌드 도구 |
| Tailwind CSS | CDN | 스타일링 |
| Lucide React | 0.559.0 | 아이콘 |
| **WebSocket** | **Native API** | **실시간 통신** |

**추가 필요 의존성:**
```json
{
  "dependencies": {
    // 기존 유지
    "react": "^19.2.1",
    "react-dom": "^19.2.1",
    "lucide-react": "^0.559.0",
    
    // 제거: @google/genai (백엔드로 이동)
  }
}
```

### 백엔드 (Render.com)
| 기술 | 버전/타입 | 역할 |
|------|-----------|------|
| Python | 3.11+ | 주 언어 |
| FastAPI | Latest | 웹 프레임워크 + WebSocket |
| uvicorn | Latest | ASGI 서버 |
| websockets | Latest | WebSocket 지원 |
| google-generativeai | Latest | Gemini API 클라이언트 |
| pydantic | Latest | 데이터 검증 |
| python-dotenv | Latest | 환경변수 관리 |
| **PyO3** | **Latest** | **Rust 바인딩** |

**requirements.txt:**
```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
websockets>=12.0
google-generativeai>=0.3.0
pydantic>=2.5.0
python-dotenv>=1.0.0
pyo3>=0.20.0
numpy>=1.24.0
```

### Rust STT 모듈
| 기술 | 역할 |
|------|------|
| Rust | 1.75+ |
| whisper.cpp | OpenAI Whisper C++ 구현 |
| whisper-rs | Rust 바인딩 |
| PyO3 | Python-Rust FFI |

**Cargo.toml:**
```toml
[package]
name = "whisper-stt"
version = "0.1.0"
edition = "2021"

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
whisper-rs = "0.10"
tokio = { version = "1", features = ["full"] }

[lib]
name = "whisper_stt"
crate-type = ["cdylib"]
```

---

## 시스템 아키텍처

### 전체 데이터 흐름

```
1. 사용자 음성 입력
   ↓
2. 브라우저: Web Audio API로 PCM 추출
   ↓
3. 브라우저 → 백엔드: WebSocket으로 오디오 청크 전송
   ↓
4. 백엔드: 오디오 처리 선택
   ├─ Option A: Gemini Native Audio API
   │  └─ Gemini API로 오디오 직접 전송
   │     └─ 번역 + TTS 응답 수신
   └─ Option B: Whisper STT + Gemini Text
      ├─ Rust Whisper로 STT 처리
      ├─ 텍스트를 Gemini Text API로 번역
      └─ (선택) Gemini TTS로 음성 합성
   ↓
5. 백엔드 → 브라우저: WebSocket으로 결과 전송
   ├─ 전사 텍스트 (실시간 스트리밍)
   ├─ 번역 텍스트
   └─ 오디오 데이터 (base64 PCM)
   ↓
6. 브라우저: 오디오 재생 + UI 업데이트
```

### WebSocket 메시지 프로토콜

#### 클라이언트 → 서버

**1. 연결 초기화**
```json
{
  "type": "init",
  "config": {
    "language": "auto",  // "ko", "en", "auto"
    "useWhisper": false,  // true: Whisper STT 사용
    "sampleRate": 16000
  }
}
```

**2. 오디오 스트림**
```json
{
  "type": "audio",
  "data": "base64_encoded_pcm_data",
  "timestamp": 1234567890
}
```

**3. 인터럽트 (사용자 말할 때 AI 중단)**
```json
{
  "type": "interrupt"
}
```

**4. 연결 종료**
```json
{
  "type": "close"
}
```

#### 서버 → 클라이언트

**1. 연결 확인**
```json
{
  "type": "connected",
  "sessionId": "uuid-session-id"
}
```

**2. 입력 전사 (실시간)**
```json
{
  "type": "input_transcription",
  "text": "안녕하세요",
  "isFinal": false,
  "language": "ko"
}
```

**3. 출력 전사 (실시간)**
```json
{
  "type": "output_transcription",
  "text": "Hello",
  "isFinal": false,
  "language": "en"
}
```

**4. 오디오 응답**
```json
{
  "type": "audio_response",
  "data": "base64_encoded_pcm_data",
  "sampleRate": 24000
}
```

**5. 턴 완료**
```json
{
  "type": "turn_complete",
  "inputText": "안녕하세요",
  "outputText": "Hello"
}
```

**6. 에러**
```json
{
  "type": "error",
  "message": "API rate limit exceeded",
  "code": "RATE_LIMIT"
}
```

---

## 프론트엔드 변경사항

### 1. WebSocket 클라이언트 구현

**새 파일: `src/services/WebSocketService.ts`**
```typescript
export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  
  constructor(
    private url: string,
    private onMessage: (data: any) => void,
    private onError: (error: any) => void
  ) {}

  connect(config: { language: string; useWhisper: boolean; sampleRate: number }) {
    this.ws = new WebSocket(this.url);
    
    this.ws.onopen = () => {
      console.log('WebSocket Connected');
      this.reconnectAttempts = 0;
      this.send({ type: 'init', config });
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.onMessage(data);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket Error:', error);
      this.onError(error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket Disconnected');
      this.attemptReconnect();
    };
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  sendAudioData(pcmData: string, timestamp: number) {
    this.send({ type: 'audio', data: pcmData, timestamp });
  }

  interrupt() {
    this.send({ type: 'interrupt' });
  }

  disconnect() {
    if (this.ws) {
      this.send({ type: 'close' });
      this.ws.close();
      this.ws = null;
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect({ language: 'auto', useWhisper: false, sampleRate: 16000 });
      }, 2000 * this.reconnectAttempts);
    }
  }
}
```

### 2. App.tsx 수정

**주요 변경사항:**
```typescript
import { WebSocketService } from './services/WebSocketService';

function App() {
  const [wsService, setWsService] = useState<WebSocketService | null>(null);
  
  // Gemini 연결 대신 WebSocket 연결
  const connectToBackend = async () => {
    try {
      setConnectionState(ConnectionState.CONNECTING);
      setError(null);

      // 1. 오디오 컨텍스트 초기화 (기존 코드 유지)
      const InputContextClass = (window.AudioContext || (window as any).webkitAudioContext);
      const inputCtx = new InputContextClass({ sampleRate: 16000 });
      const outputCtx = new InputContextClass({ sampleRate: 24000 });
      
      // ... (기존 오디오 설정 코드)

      // 2. WebSocket 연결
      const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
      const ws = new WebSocketService(
        wsUrl,
        handleWebSocketMessage,  // 메시지 핸들러
        handleWebSocketError     // 에러 핸들러
      );
      
      ws.connect({
        language: 'auto',
        useWhisper: false,  // 옵션으로 변경 가능
        sampleRate: 16000
      });
      
      setWsService(ws);

      // 3. 마이크 스트림 (기존 코드와 유사하지만 ws.sendAudioData로 전송)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const source = inputCtx.createMediaStreamSource(stream);
      
      const processor = inputCtx.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (e) => {
        if (isMuted || !ws) return;
        const inputData = e.inputBuffer.getChannelData(0);
        const pcmBlob = createPcmBlob(inputData);
        
        // Base64로 인코딩하여 전송
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = reader.result?.toString().split(',')[1];
          if (base64) {
            ws.sendAudioData(base64, Date.now());
          }
        };
        reader.readAsDataURL(pcmBlob);
      };
      
      source.connect(processor);
      processor.connect(inputCtx.destination);
      
      setConnectionState(ConnectionState.CONNECTED);
      
    } catch (e: any) {
      console.error(e);
      setError(e.message || "Failed to connect");
      setConnectionState(ConnectionState.ERROR);
      stopAudio();
    }
  };

  // WebSocket 메시지 핸들러
  const handleWebSocketMessage = useCallback((message: any) => {
    switch (message.type) {
      case 'connected':
        console.log('Session ID:', message.sessionId);
        break;
        
      case 'input_transcription':
        if (message.isFinal) {
          // 최종 텍스트를 messages에 추가
        } else {
          // 실시간 텍스트 업데이트
          setStreamingUserText(message.text);
        }
        break;
        
      case 'output_transcription':
        if (message.isFinal) {
          // 최종 텍스트를 messages에 추가
        } else {
          setStreamingModelText(message.text);
        }
        break;
        
      case 'audio_response':
        // 오디오 재생 (기존 코드 재사용)
        const audioData = message.data;
        if (audioData && outputAudioContextRef.current && outputGainRef.current) {
          const ctx = outputAudioContextRef.current;
          decodeAudioData(base64ToArrayBuffer(audioData), ctx)
            .then(buffer => {
              const source = ctx.createBufferSource();
              source.buffer = buffer;
              source.connect(outputGainRef.current!);
              source.start(nextStartTimeRef.current);
              nextStartTimeRef.current += buffer.duration;
            });
        }
        break;
        
      case 'turn_complete':
        // 턴 완료 처리
        break;
        
      case 'error':
        setError(message.message);
        break;
    }
  }, []);

  const handleWebSocketError = useCallback((error: any) => {
    setError("WebSocket connection error");
    setConnectionState(ConnectionState.ERROR);
  }, []);

  return (
    // ... (기존 UI 코드 유지)
  );
}
```

### 3. 환경변수 설정

**.env.local (로컬 개발용)**
```env
VITE_WS_URL=ws://localhost:8000/ws
```

**.env.production (Netlify 배포용)**
```env
VITE_WS_URL=wss://your-render-app.onrender.com/ws
```

**netlify.toml**
```toml
[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

---

## 백엔드 구조

### 프로젝트 구조
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 앱 진입점
│   ├── websocket/
│   │   ├── __init__.py
│   │   ├── handler.py          # WebSocket 핸들러
│   │   └── protocol.py         # 메시지 프로토콜 정의
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_service.py   # Gemini API 통합
│   │   └── whisper_service.py  # Whisper STT 통합
│   ├── models/
│   │   ├── __init__.py
│   │   └── messages.py         # Pydantic 모델
│   └── utils/
│       ├── __init__.py
│       └── audio.py            # 오디오 처리 유틸
├── rust_stt/                   # Rust STT 모듈
│   ├── Cargo.toml
│   ├── src/
│   │   └── lib.rs
│   └── models/                 # Whisper 모델 파일
├── requirements.txt
├── Dockerfile
└── render.yaml                 # Render.com 배포 설정
```

### 1. main.py

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.websocket.handler import WebSocketHandler

load_dotenv()

app = FastAPI(title="Gemini Live Interpreter Backend")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite 로컬 개발
        "https://your-netlify-app.netlify.app"  # Netlify 배포
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    handler = WebSocketHandler(websocket)
    await handler.handle()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### 2. websocket/handler.py

```python
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging
from typing import Optional

from ..services.gemini_service import GeminiService
from ..services.whisper_service import WhisperService
from ..models.messages import InitMessage, AudioMessage

logger = logging.getLogger(__name__)

class WebSocketHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.gemini_service: Optional[GeminiService] = None
        self.whisper_service: Optional[WhisperService] = None
        self.session_id: str = ""
        self.use_whisper: bool = False
    
    async def handle(self):
        await self.websocket.accept()
        
        try:
            while True:
                # 메시지 수신
                data = await self.websocket.receive_text()
                message = json.loads(data)
                
                msg_type = message.get("type")
                
                if msg_type == "init":
                    await self.handle_init(message)
                elif msg_type == "audio":
                    await self.handle_audio(message)
                elif msg_type == "interrupt":
                    await self.handle_interrupt()
                elif msg_type == "close":
                    break
                    
        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {self.session_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}")
            await self.send_error(str(e))
        finally:
            await self.cleanup()
    
    async def handle_init(self, message: dict):
        """초기화 메시지 처리"""
        config = message.get("config", {})
        self.use_whisper = config.get("useWhisper", False)
        
        # 세션 ID 생성
        import uuid
        self.session_id = str(uuid.uuid4())
        
        # Gemini 서비스 초기화
        self.gemini_service = GeminiService(
            on_input_transcription=self.on_input_transcription,
            on_output_transcription=self.on_output_transcription,
            on_audio_response=self.on_audio_response,
            on_turn_complete=self.on_turn_complete
        )
        await self.gemini_service.connect()
        
        # Whisper 서비스 초기화 (필요시)
        if self.use_whisper:
            self.whisper_service = WhisperService()
        
        # 연결 확인 전송
        await self.websocket.send_json({
            "type": "connected",
            "sessionId": self.session_id
        })
    
    async def handle_audio(self, message: dict):
        """오디오 데이터 처리"""
        audio_data = message.get("data")
        timestamp = message.get("timestamp")
        
        if self.use_whisper and self.whisper_service:
            # Whisper STT 사용
            transcription = await self.whisper_service.transcribe(audio_data)
            if transcription:
                await self.gemini_service.send_text(transcription)
        else:
            # Gemini Native Audio 사용
            await self.gemini_service.send_audio(audio_data)
    
    async def handle_interrupt(self):
        """인터럽트 처리"""
        if self.gemini_service:
            await self.gemini_service.interrupt()
    
    # 콜백 메서드들
    async def on_input_transcription(self, text: str, is_final: bool):
        await self.websocket.send_json({
            "type": "input_transcription",
            "text": text,
            "isFinal": is_final
        })
    
    async def on_output_transcription(self, text: str, is_final: bool):
        await self.websocket.send_json({
            "type": "output_transcription",
            "text": text,
            "isFinal": is_final
        })
    
    async def on_audio_response(self, audio_data: str, sample_rate: int):
        await self.websocket.send_json({
            "type": "audio_response",
            "data": audio_data,
            "sampleRate": sample_rate
        })
    
    async def on_turn_complete(self, input_text: str, output_text: str):
        await self.websocket.send_json({
            "type": "turn_complete",
            "inputText": input_text,
            "outputText": output_text
        })
    
    async def send_error(self, message: str, code: str = "UNKNOWN"):
        await self.websocket.send_json({
            "type": "error",
            "message": message,
            "code": code
        })
    
    async def cleanup(self):
        """리소스 정리"""
        if self.gemini_service:
            await self.gemini_service.disconnect()
        if self.whisper_service:
            self.whisper_service.cleanup()
```

### 3. services/gemini_service.py

```python
import os
import asyncio
import base64
from typing import Callable, Awaitable
import logging

import google.generativeai as genai
from google.generativeai.types import LiveServerMessage

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are an ultra-fast, bidirectional simultaneous interpreter for a voice-to-voice translation system.

### CORE INSTRUCTIONS:
1. **Auto-Detection:**
   - If the input is primarily KOREAN, translate to ENGLISH.
   - If the input is primarily ENGLISH, translate to KOREAN.

2. **Zero-Latency Output:**
   - Output **ONLY** the translated text/speech.
   - **STRICTLY FORBIDDEN:** Do not output markdown, prefixes, explanations.
   - Start the translation immediately.

3. **TTS Optimization (Spoken Style):**
   - Translate into natural **spoken language**.
   - Use punctuation strategically to create natural breathing pauses.
"""

MODEL_NAME = 'gemini-2.5-flash-native-audio-preview-09-2025'

class GeminiService:
    def __init__(
        self,
        on_input_transcription: Callable[[str, bool], Awaitable[None]],
        on_output_transcription: Callable[[str, bool], Awaitable[None]],
        on_audio_response: Callable[[str, int], Awaitable[None]],
        on_turn_complete: Callable[[str, str], Awaitable[None]]
    ):
        self.on_input_transcription = on_input_transcription
        self.on_output_transcription = on_output_transcription
        self.on_audio_response = on_audio_response
        self.on_turn_complete = on_turn_complete
        
        self.session = None
        self.current_input_text = ""
        self.current_output_text = ""
        
        # API 키 설정
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        genai.configure(api_key=api_key)
    
    async def connect(self):
        """Gemini Live 세션 연결"""
        config = {
            "model": MODEL_NAME,
            "config": {
                "response_modalities": ["AUDIO"],
                "system_instruction": SYSTEM_INSTRUCTION,
                "speech_config": {
                    "voice_config": {"prebuilt_voice_config": {"voice_name": "Zephyr"}}
                },
                "input_audio_transcription": {},
                "output_audio_transcription": {},
            }
        }
        
        try:
            client = genai.Client()
            self.session = await client.live.connect(**config)
            
            # 메시지 수신 태스크 시작
            asyncio.create_task(self._receive_messages())
            
            logger.info("Gemini Live session connected")
        except Exception as e:
            logger.error(f"Failed to connect to Gemini: {e}")
            raise
    
    async def send_audio(self, base64_audio: str):
        """오디오 데이터 전송"""
        if not self.session:
            raise RuntimeError("Session not connected")
        
        try:
            audio_bytes = base64.b64decode(base64_audio)
            await self.session.send_realtime_input({"media": audio_bytes})
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
    
    async def send_text(self, text: str):
        """텍스트 전송 (Whisper 사용 시)"""
        if not self.session:
            raise RuntimeError("Session not connected")
        
        try:
            await self.session.send(text)
        except Exception as e:
            logger.error(f"Error sending text: {e}")
    
    async def interrupt(self):
        """인터럽트 신호 전송"""
        # Gemini Live API에 인터럽트 메서드가 있다면 사용
        # 없다면 새 세션으로 재연결
        self.current_output_text = ""
    
    async def disconnect(self):
        """세션 종료"""
        if self.session:
            # 세션 종료 로직
            self.session = None
    
    async def _receive_messages(self):
        """Gemini로부터 메시지 수신"""
        try:
            async for message in self.session:
                await self._handle_message(message)
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
    
    async def _handle_message(self, message: LiveServerMessage):
        """Gemini 메시지 처리"""
        # 입력 전사
        input_tx = message.server_content.input_transcription.text if message.server_content.input_transcription else None
        if input_tx:
            self.current_input_text += input_tx
            await self.on_input_transcription(self.current_input_text, False)
        
        # 출력 전사
        output_tx = message.server_content.output_transcription.text if message.server_content.output_transcription else None
        if output_tx:
            self.current_output_text += output_tx
            await self.on_output_transcription(self.current_output_text, False)
        
        # 오디오 응답
        if message.server_content.model_turn and message.server_content.model_turn.parts:
            for part in message.server_content.model_turn.parts:
                if part.inline_data and part.inline_data.data:
                    audio_data = part.inline_data.data
                    # base64 인코딩된 PCM 데이터
                    await self.on_audio_response(audio_data, 24000)
        
        # 턴 완료
        if message.server_content.turn_complete:
            await self.on_input_transcription(self.current_input_text, True)
            await self.on_output_transcription(self.current_output_text, True)
            await self.on_turn_complete(self.current_input_text, self.current_output_text)
            
            # 리셋
            self.current_input_text = ""
            self.current_output_text = ""
        
        # 인터럽트
        if message.server_content.interrupted:
            self.current_output_text = ""
```

### 4. services/whisper_service.py

```python
import base64
import numpy as np
import logging
from typing import Optional

# Rust 모듈 import
try:
    import whisper_stt
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logging.warning("Whisper STT module not available")

logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self, model_path: str = "./rust_stt/models/ggml-base.bin"):
        if not WHISPER_AVAILABLE:
            raise RuntimeError("Whisper STT module not installed")
        
        self.model = whisper_stt.WhisperModel(model_path)
        logger.info(f"Whisper model loaded from {model_path}")
    
    async def transcribe(self, base64_audio: str) -> Optional[str]:
        """오디오 전사"""
        try:
            # base64 디코딩
            audio_bytes = base64.b64decode(base64_audio)
            
            # PCM 데이터를 numpy array로 변환
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Whisper 추론 (Rust 모듈 호출)
            result = self.model.transcribe(audio_array.tolist())
            
            return result.get("text", "")
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return None
    
    def cleanup(self):
        """리소스 정리"""
        if hasattr(self, 'model'):
            del self.model
```

---

## Rust + Whisper 통합

### 1. Rust 모듈 구조

**rust_stt/src/lib.rs**
```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;
use whisper_rs::{WhisperContext, WhisperContextParameters, FullParams, SamplingStrategy};
use std::path::Path;

#[pyclass]
struct WhisperModel {
    ctx: WhisperContext,
}

#[pymethods]
impl WhisperModel {
    #[new]
    fn new(model_path: String) -> PyResult<Self> {
        let path = Path::new(&model_path);
        let ctx = WhisperContext::new_with_params(
            path.to_str().unwrap(),
            WhisperContextParameters::default(),
        )
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{:?}", e)))?;
        
        Ok(WhisperModel { ctx })
    }

    fn transcribe(&mut self, audio_data: Vec<f32>, py: Python) -> PyResult<PyObject> {
        let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });
        params.set_language(Some("auto"));
        params.set_translate(false);
        params.set_print_progress(false);
        params.set_print_special(false);
        params.set_print_realtime(false);

        let mut state = self.ctx.create_state()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{:?}", e)))?;

        state.full(params, &audio_data)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{:?}", e)))?;

        let num_segments = state.full_n_segments()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{:?}", e)))?;

        let mut full_text = String::new();
        for i in 0..num_segments {
            let segment = state.full_get_segment_text(i)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{:?}", e)))?;
            full_text.push_str(&segment);
        }

        let result = PyDict::new_bound(py);
        result.set_item("text", full_text)?;
        
        Ok(result.into())
    }
}

#[pymodule]
fn whisper_stt(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<WhisperModel>()?;
    Ok(())
}
```

### 2. 빌드 및 설치

**빌드 스크립트: `build_rust.sh`**
```bash
#!/bin/bash

cd rust_stt

# Rust 빌드
cargo build --release

# Python 패키지로 복사
cp target/release/libwhisper_stt.so ../app/whisper_stt.so
# 또는 macOS의 경우:
# cp target/release/libwhisper_stt.dylib ../app/whisper_stt.so
# Windows의 경우:
# cp target/release/whisper_stt.dll ../app/whisper_stt.pyd

echo "Rust module built successfully"
```

### 3. Whisper 모델 다운로드

```bash
#!/bin/bash
# download_models.sh

mkdir -p rust_stt/models
cd rust_stt/models

# Base 모델 다운로드 (74MB)
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin

# 또는 다른 모델:
# Small (466MB): ggml-small.bin
# Medium (1.5GB): ggml-medium.bin
# Large (2.9GB): ggml-large-v3.bin

echo "Whisper models downloaded"
```

---

## 배포 전략

### Netlify (프론트엔드)

**1. 환경변수 설정**
- Netlify Dashboard → Site settings → Environment variables
- `VITE_WS_URL`: `wss://your-backend.onrender.com/ws`

**2. netlify.toml**
```toml
[build]
  command = "npm run build"
  publish = "dist"
  
[build.environment]
  NODE_VERSION = "20"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
```

**3. 배포 명령**
```bash
# 로컬에서 테스트
npm run build
npm run preview

# Git push로 자동 배포
git push origin main
```

### Render.com (백엔드)

**1. render.yaml**
```yaml
services:
  - type: web
    name: gemini-interpreter-backend
    env: python
    region: oregon
    plan: starter  # 또는 standard
    buildCommand: |
      pip install -r requirements.txt
      chmod +x build_rust.sh
      ./build_rust.sh
      chmod +x download_models.sh
      ./download_models.sh
    startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: GEMINI_API_KEY
        sync: false  # Render Dashboard에서 설정
      - key: PORT
        value: 8000
```

**2. Dockerfile (선택사항 - 커스텀 빌드)**
```dockerfile
FROM rust:1.75 as rust-builder

WORKDIR /app
COPY rust_stt/ ./rust_stt/
WORKDIR /app/rust_stt
RUN cargo build --release

FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Rust 모듈 복사
COPY --from=rust-builder /app/rust_stt/target/release/libwhisper_stt.so /app/app/whisper_stt.so

# 앱 코드 복사
COPY app/ ./app/
COPY download_models.sh .
RUN chmod +x download_models.sh && ./download_models.sh

# 포트 노출
EXPOSE 8000

# 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**3. 환경변수 설정**
- Render Dashboard → Environment → Add Environment Variable
- `GEMINI_API_KEY`: (Gemini API 키)
- `WHISPER_MODEL_PATH`: `./rust_stt/models/ggml-base.bin`

**4. 배포**
```bash
# Render에 Git 연결 후 자동 배포
# 또는 Render CLI 사용
render deploy
```

---

## 구현 단계

### Phase 1: 기본 WebSocket 통신 구축 (1주)

**프론트엔드:**
- [ ] WebSocketService 클래스 구현
- [ ] App.tsx에서 Gemini 직접 호출 제거
- [ ] WebSocket 연결 및 메시지 송수신 로직 추가
- [ ] 로컬 테스트 환경 설정

**백엔드:**
- [ ] FastAPI 프로젝트 초기화
- [ ] WebSocket 엔드포인트 구현
- [ ] Gemini API 기본 통합 (Native Audio)
- [ ] 메시지 프로토콜 구현
- [ ] 로컬 테스트 서버 실행

**테스트:**
```bash
# 백엔드 실행
cd backend
python -m app.main

# 프론트엔드 실행
npm run dev
```

### Phase 2: Rust Whisper STT 통합 (1-2주)

**Rust 모듈:**
- [ ] Rust 프로젝트 생성 및 whisper-rs 설정
- [ ] PyO3 바인딩 구현
- [ ] Whisper 모델 다운로드 및 로드 테스트
- [ ] Python에서 Rust 모듈 호출 테스트

**백엔드:**
- [ ] WhisperService 클래스 구현
- [ ] WebSocketHandler에 Whisper 옵션 추가
- [ ] Whisper STT + Gemini Text API 통합

**프론트엔드:**
- [ ] UI에 "Use Whisper STT" 옵션 추가
- [ ] 설정 메뉴 구현

### Phase 3: 배포 및 최적화 (1주)

**프론트엔드 배포:**
- [ ] Netlify 계정 생성 및 프로젝트 연결
- [ ] 환경변수 설정
- [ ] 빌드 및 배포 테스트
- [ ] 커스텀 도메인 설정 (선택)

**백엔드 배포:**
- [ ] Render.com 계정 생성 및 프로젝트 연결
- [ ] render.yaml 또는 Dockerfile 설정
- [ ] Rust 빌드 파이프라인 설정
- [ ] Whisper 모델 다운로드 자동화
- [ ] 환경변수 및 시크릿 설정
- [ ] 배포 테스트

**최적화:**
- [ ] WebSocket 재연결 로직 강화
- [ ] 오디오 버퍼링 최적화
- [ ] 에러 핸들링 개선
- [ ] 로깅 및 모니터링 추가

### Phase 4: 테스트 및 문서화 (지속적)

- [ ] E2E 테스트 작성
- [ ] 사용자 가이드 작성
- [ ] API 문서 생성 (FastAPI 자동 생성)
- [ ] 성능 벤치마크

---

## 프롬프트 가이드

### 1. 프론트엔드 개발용 프롬프트

#### WebSocket 클라이언트 구현
```
프롬프트:
gemini-live-interpreter_v2 프로젝트에서 WebSocket 클라이언트 서비스를 구현해줘.

요구사항:
1. src/services/WebSocketService.ts 파일 생성
2. 연결, 재연결, 메시지 송수신 기능
3. 타입스크립트 타입 정의 포함
4. 에러 핸들링 및 로깅
5. 재연결 로직 (최대 5회 시도, 지수 백오프)

메시지 타입:
- init: 초기화
- audio: 오디오 데이터 전송
- interrupt: 인터럽트
- close: 연결 종료

참고: project-analysis_v2.md의 "WebSocket 메시지 프로토콜" 섹션 참조
```

#### App.tsx 리팩토링
```
프롬프트:
App.tsx를 수정하여 Gemini API 직접 호출 대신 WebSocketService를 사용하도록 변경해줘.

변경사항:
1. @google/genai import 제거
2. WebSocketService import 추가
3. connectToGemini 함수를 connectToBackend로 변경
4. WebSocket 메시지 핸들러 구현
5. 기존 오디오 처리 로직은 최대한 유지
6. 환경변수 VITE_WS_URL 사용

기존 기능 유지:
- 마이크 입력 및 시각화
- 오디오 출력 및 재생
- 전사 텍스트 표시
- UI/UX

참고: project-analysis_v2.md의 "프론트엔드 변경사항" 섹션
```

### 2. 백엔드 개발용 프롬프트

#### FastAPI 기본 구조
```
프롬프트:
FastAPI를 사용하여 실시간 음성 통역 백엔드를 구축해줘.

프로젝트 구조:
backend/
├── app/
│   ├── main.py
│   ├── websocket/
│   │   ├── handler.py
│   │   └── protocol.py
│   ├── services/
│   │   ├── gemini_service.py
│   │   └── whisper_service.py
│   └── models/
│       └── messages.py
└── requirements.txt

요구사항:
1. WebSocket 엔드포인트 (/ws) 구현
2. CORS 설정 (Netlify 도메인 허용)
3. 헬스체크 엔드포인트 (/health)
4. 환경변수로 GEMINI_API_KEY 관리
5. 비동기 처리 (asyncio)

참고: project-analysis_v2.md의 "백엔드 구조" 섹션
```

#### Gemini 서비스 통합
```
프롬프트:
Gemini Live API를 FastAPI 백엔드에 통합하는 서비스 클래스를 구현해줘.

파일: app/services/gemini_service.py

기능:
1. Gemini Live 세션 연결 및 관리
2. 실시간 오디오 입력 전송
3. 입력/출력 전사 텍스트 콜백
4. 오디오 응답 콜백
5. 턴 완료 및 인터럽트 처리
6. 비동기 메시지 수신 루프

시스템 프롬프트:
- 한↔영 자동 감지 번역
- 음성 최적화 출력
- 저지연

참고: 기존 App.tsx의 Gemini 연결 로직 및 SYSTEM_INSTRUCTION
```

### 3. Rust + Whisper 통합용 프롬프트

#### Rust 모듈 기본 구조
```
프롬프트:
OpenAI Whisper를 Rust로 구현하여 Python에서 호출할 수 있는 모듈을 만들어줘.

기술 스택:
- whisper-rs (whisper.cpp Rust 바인딩)
- PyO3 (Python FFI)

파일: rust_stt/src/lib.rs

기능:
1. Whisper 모델 로드 (GGML 포맷)
2. Float32 오디오 배열을 받아 전사
3. Python에서 호출 가능한 클래스 인터페이스
4. 에러 핸들링

사용 예:
```python
import whisper_stt
model = whisper_stt.WhisperModel("path/to/model.bin")
result = model.transcribe(audio_data)  # audio_data: List[float]
print(result["text"])
```

참고: project-analysis_v2.md의 "Rust + Whisper 통합" 섹션
```

#### Python에서 Rust 모듈 사용
```
프롬프트:
Rust로 빌드한 Whisper STT 모듈을 Python 백엔드에서 사용하는 서비스 클래스를 구현해줘.

파일: app/services/whisper_service.py

기능:
1. Rust 모듈 import 및 모델 로드
2. base64 오디오 데이터를 numpy array로 변환
3. Whisper 추론 실행
4. 전사 텍스트 반환
5. 비동기 처리 (asyncio)
6. 에러 핸들링 및 fallback

참고: project-analysis_v2.md의 "services/whisper_service.py" 섹션
```

### 4. 배포용 프롬프트

#### Netlify 배포 설정
```
프롬프트:
React + Vite 프로젝트를 Netlify에 배포하기 위한 설정 파일을 생성해줘.

파일: netlify.toml

설정 항목:
1. 빌드 명령: npm run build
2. 퍼블리시 디렉토리: dist
3. SPA 리다이렉트 설정
4. 환경변수 (VITE_WS_URL)
5. 보안 헤더

배포 환경변수 (Netlify Dashboard에서 설정):
- VITE_WS_URL: wss://your-backend.onrender.com/ws

참고: project-analysis_v2.md의 "Netlify 배포 전략" 섹션
```

#### Render.com 배포 설정
```
프롬프트:
FastAPI + Rust 백엔드를 Render.com에 배포하기 위한 설정 파일을 생성해줘.

파일: render.yaml

설정 항목:
1. Python 환경 (3.11)
2. 빌드 명령:
   - pip install
   - Rust 빌드 스크립트 실행
   - Whisper 모델 다운로드
3. 시작 명령: uvicorn
4. 환경변수:
   - GEMINI_API_KEY (시크릿)
   - WHISPER_MODEL_PATH
5. 리전 및 플랜 설정

추가 파일:
- build_rust.sh: Rust 빌드 스크립트
- download_models.sh: Whisper 모델 다운로드 스크립트

참고: project-analysis_v2.md의 "Render.com 배포 전략" 섹션
```

### 5. 통합 테스트용 프롬프트

#### E2E 테스트
```
프롬프트:
프론트엔드와 백엔드가 올바르게 통신하는지 검증하는 E2E 테스트를 작성해줘.

테스트 시나리오:
1. WebSocket 연결 성공
2. 초기화 메시지 송수신
3. 오디오 데이터 전송
4. 전사 텍스트 수신
5. 오디오 응답 수신
6. 인터럽트 처리
7. 연결 종료

도구:
- 프론트엔드: Vitest + Testing Library
- 백엔드: pytest + pytest-asyncio

참고: 실제 API 호출 대신 Mock 사용
```

### 6. 최적화용 프롬프트

#### 성능 최적화
```
프롬프트:
실시간 음성 통역 시스템의 성능을 최적화해줘.

최적화 영역:
1. WebSocket 메시지 압축 (gzip)
2. 오디오 버퍼 크기 조정 (지연 vs 품질)
3. Whisper 모델 선택 (base vs small vs medium)
4. 백엔드 비동기 처리 개선
5. 프론트엔드 오디오 재생 큐 최적화

목표:
- 엔드투엔드 지연 < 500ms
- CPU 사용률 < 50%
- 메모리 사용량 < 1GB

참고: project-analysis_v2.md 전체
```

---

## 주요 고려사항

### 1. 보안
- ✅ API 키를 백엔드 환경변수로 관리
- ✅ HTTPS/WSS 사용 (Netlify, Render 자동 제공)
- ✅ CORS 설정으로 허용된 도메인만 접근
- ⚠️ Rate Limiting 구현 권장
- ⚠️ 사용자 인증 (향후 추가 고려)

### 2. 성능
- ✅ Rust Whisper로 STT 성능 향상
- ✅ WebSocket으로 실시간 스트리밍
- ✅ 비동기 처리 (FastAPI, asyncio)
- ⚠️ 오디오 버퍼 크기 최적화 필요
- ⚠️ Whisper 모델 크기 선택 (속도 vs 정확도)

### 3. 확장성
- ✅ 프론트엔드/백엔드 독립 배포
- ✅ 각 서비스 독립 스케일링 가능
- ⚠️ 향후 Redis/Kafka로 메시지 큐 추가 고려
- ⚠️ 멀티 세션 관리 (세션 DB 필요)

### 4. 비용
- **Netlify**: 무료 플랜 (100GB 대역폭/월)
- **Render.com**: Starter 플랜 $7/월 (512MB RAM) 또는 무료 플랜
- **Gemini API**: 무료 할당량 제한, 초과 시 유료
- ⚠️ Whisper 모델 크기에 따라 메모리 요구량 증가

### 5. 제약사항
- **브라우저 호환성**: Web Audio API, WebSocket 지원 필요
- **네트워크 지연**: WebSocket RTT에 영향
- **Gemini API 제한**: Rate limit, 동시 세션 수
- **Render.com 무료 플랜**: Cold start 시간 (비활성 후 재시작 시 지연)

---

## 추가 개선 아이디어

### 단기 (1-2개월)
1. **사용자 설정 UI**
   - 언어 선택 (auto/ko/en)
   - Whisper on/off 토글
   - 음성 선택 (Zephyr, Puck, Charon)
   - 음질/속도 조절

2. **대화 기록 저장**
   - 로컬 스토리지 또는 백엔드 DB
   - 내보내기 기능 (TXT, JSON)

3. **다국어 지원**
   - 한↔영 외 추가 언어 페어
   - UI 다국어화 (i18n)

### 중기 (3-6개월)
1. **사용자 인증**
   - OAuth (Google, GitHub)
   - 사용량 추적 및 제한

2. **프리미엄 기능**
   - 더 큰 Whisper 모델 (Medium, Large)
   - 고품질 TTS 음성
   - 대화 기록 클라우드 저장

3. **모바일 앱**
   - React Native 포팅
   - iOS/Android 네이티브 기능 활용

### 장기 (6개월+)
1. **다자간 통역**
   - 여러 사용자 동시 참여
   - 실시간 통역 브로드캐스트

2. **AI 어시스턴트 통합**
   - 회의록 자동 생성
   - 요약 및 액션 아이템 추출

3. **엔터프라이즈 기능**
   - On-premise 배포 옵션
   - SSO 통합
   - 감사 로그

---

## 참고 자료

### 공식 문서
- [Gemini API - Live Connect](https://ai.google.dev/api/live-connect)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp)
- [PyO3 User Guide](https://pyo3.rs/)

### 배포 가이드
- [Netlify Deploy Guide](https://docs.netlify.com/)
- [Render.com Documentation](https://render.com/docs)

### 샘플 코드
- [기존 프로젝트 분석](./project-analysis.md)
- [FastAPI WebSocket Example](https://github.com/tiangolo/fastapi/blob/master/docs/en/docs/advanced/websockets.md)

---

## 버전 이력

| 버전 | 날짜 | 변경사항 |
|------|------|----------|
| 2.0.0 | 2024-12 | 백엔드 분리 아키텍처 초기 설계 |

---

## 라이선스 및 기여

이 프로젝트는 기존 gemini-live-interpreter를 기반으로 백엔드 분리 아키텍처로 재설계한 버전입니다.

**원본 프로젝트**: gemini-live-interpreter (Vite + React + Gemini Live API)
**재설계 버전**: gemini-live-interpreter_v2 (React + Python + Rust 아키텍처)

---

## 연락처 및 지원

질문이나 이슈가 있으시면 GitHub Issues를 이용해 주세요.

**Happy Interpreting! 🌐🎤**