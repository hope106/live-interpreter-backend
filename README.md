# 🎙️ Gemini Live Interpreter Backend

**실시간 양방향 음성 통역 시스템** - Google Gemini 2.5 Flash Native Audio 기반

FastAPI + WebSocket 서버로 클라이언트와 Gemini Live API 사이의 **지능형 브로커** 역할을 수행합니다.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.124.2-green.svg)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-orange.svg)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 목차

- [주요 기능](#주요-기능)
- [시스템 아키텍처](#시스템-아키텍처)
- [기술 스택](#기술-스택)
- [빠른 시작](#빠른-시작)
- [환경 변수 설정](#환경-변수-설정)
- [API 문서](#api-문서)
- [프로젝트 구조](#프로젝트-구조)
- [개발 가이드](#개발-가이드)
- [문제 해결](#문제-해결)

---

## ✨ 주요 기능

### 🎯 핵심 기능
- **실시간 양방향 통역**: 한국어 ⇄ 영어 동시통역
- **음성 스트리밍**: WebSocket 기반 저지연 오디오 전송
- **VAD (Voice Activity Detection)**: 무음 구간 필터링으로 성능 최적화
- **실시간 Transcription**: 입력/출력 음성의 실시간 텍스트 변환
- **턴 기반 대화 관리**: 자연스러운 대화 흐름 제어

### 🚀 기술적 강점
- **비동기 I/O**: asyncio 기반 고성능 동시 처리
- **타입 안전**: Pydantic을 통한 강력한 메시지 검증
- **모듈화 설계**: 계층화된 아키텍처로 유지보수 용이
- **상세한 로깅**: 디버깅 및 모니터링 지원

---

## 🏗️ 시스템 아키텍처

```
┌──────────────────────────────────┐
│   Client (Browser/React App)    │
│        WebSocket 연결             │
└──────────────────────────────────┘
              ↓ ↑
┌──────────────────────────────────┐
│     FastAPI WebSocket Layer      │
│      (app/main.py)               │
└──────────────────────────────────┘
              ↓ ↑
┌──────────────────────────────────┐
│    WebSocketHandler Layer        │
│  (app/websocket/handler.py)      │
│  - 메시지 라우팅                  │
│  - 세션 관리                      │
└──────────────────────────────────┘
              ↓ ↑
┌──────────────────────────────────┐
│     GeminiService Layer          │
│  (app/services/gemini_service.py)│
│  - Gemini Live API 통신          │
│  - VAD 필터링                     │
│  - 오디오/텍스트 처리             │
└──────────────────────────────────┘
              ↓ ↑
┌──────────────────────────────────┐
│    Google Gemini Live API        │
│  gemini-2.5-flash-native-audio   │
└──────────────────────────────────┘
```

**상세 아키텍처 문서**: [ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md)

---

## 🛠️ 기술 스택

| 카테고리 | 기술 | 버전 |
|---------|------|------|
| **웹 프레임워크** | FastAPI | 0.124.2 |
| **ASGI 서버** | Uvicorn | 0.38.0 |
| **WebSocket** | websockets | 15.0.1 |
| **AI 모델** | Google GenAI SDK | 1.55.0 |
| **데이터 검증** | Pydantic | 2.7.0 |
| **환경 설정** | python-dotenv | 1.2.1 |
| **HTTP 클라이언트** | httpx | 0.28.1 |

### AI 모델 정보
```python
MODEL: gemini-2.5-flash-native-audio-preview-09-2025
- 음성 입력 → 음성 출력 (End-to-End)
- 실시간 transcription 지원
- 24kHz 고품질 오디오 출력
```

---

## 🚀 빠른 시작

### 1. 사전 요구사항

- Python 3.11 이상
- Gemini API Key ([발급 받기](https://aistudio.google.com/app/apikey))

### 2. 설치 및 실행

```bash
# 1. 저장소 클론 (또는 프로젝트 디렉토리 이동)
cd live-interpreter-backend

# 2. 가상 환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일에 GEMINI_API_KEY 설정

# 5. 서버 실행
uvicorn app.main:app --reload

# ✅ 서버가 http://localhost:8000 에서 실행됩니다
```

### 3. 서버 확인

```bash
# Health Check
curl http://localhost:8000/health
# {"status":"ok"}

# API 문서 확인
open http://localhost:8000/docs
```

---

## ⚙️ 환경 변수 설정

`.env` 파일 구성 예시:

```bash
# Gemini API 설정 (필수)
GEMINI_API_KEY=your_gemini_api_key_here

# 서버 설정
HOST=localhost
PORT=8000
DEBUG=True

# CORS 설정
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173

# 로깅 설정
LOG_LEVEL=DEBUG
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# VAD (Voice Activity Detection) 설정
VAD_THRESHOLD=500          # 0으로 설정 시 VAD 비활성화
VAD_HANGOVER_FRAMES=15     # 무음 허용 프레임 (15 ≈ 300ms)

# WebSocket 설정
WS_PING_INTERVAL=10
WS_PING_TIMEOUT=5
```

### 환경 변수 상세

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `GEMINI_API_KEY` | Gemini API 인증 키 | - | ✅ |
| `HOST` | 서버 호스트 주소 | `localhost` | ❌ |
| `PORT` | 서버 포트 번호 | `8000` | ❌ |
| `DEBUG` | 디버그 모드 (자동 리로드) | `True` | ❌ |
| `CORS_ORIGINS` | CORS 허용 오리진 (쉼표 구분) | `http://localhost:3000` | ❌ |
| `LOG_LEVEL` | 로그 레벨 (DEBUG/INFO/WARNING/ERROR) | `DEBUG` | ❌ |
| `VAD_THRESHOLD` | VAD 에너지 임계값 (0=비활성화) | `500` | ❌ |
| `VAD_HANGOVER_FRAMES` | VAD Hangover 프레임 수 | `15` | ❌ |

---

## 📡 API 문서

### HTTP 엔드포인트

#### `GET /health`
서버 상태 확인 (헬스체크)

**응답**:
```json
{
  "status": "ok"
}
```

### WebSocket 엔드포인트

#### `WS /ws`
실시간 통역 세션 WebSocket

---

## 📨 WebSocket 메시지 프로토콜

### 클라이언트 → 서버 메시지

#### 1. InitMessage (세션 초기화)
```json
{
  "type": "init",
  "config": {
    "language": "auto",      // "auto" | "ko" | "en"
    "useWhisper": false,     // Whisper STT 사용 여부
    "sampleRate": 16000      // 샘플레이트 (Hz)
  }
}
```

#### 2. AudioMessage (오디오 청크 전송)
```json
{
  "type": "audio",
  "data": "base64_encoded_pcm_audio",
  "timestamp": 1702345678900
}
```

#### 3. InterruptMessage (AI 응답 중단)
```json
{
  "type": "interrupt"
}
```

#### 4. CloseMessage (세션 종료)
```json
{
  "type": "close"
}
```

### 서버 → 클라이언트 메시지

#### 1. ConnectedMessage (연결 완료)
```json
{
  "type": "connected",
  "sessionId": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 2. TranscriptionMessage (음성 인식 결과)
```json
{
  "type": "input_transcription",  // or "output_transcription"
  "text": "안녕하세요",
  "isFinal": false,
  "language": "ko"  // 최종 결과일 때만 포함
}
```

#### 3. AudioResponseMessage (AI 음성 응답)
```json
{
  "type": "audio_response",
  "data": "base64_encoded_pcm_audio",
  "sampleRate": 24000
}
```

#### 4. TurnCompleteMessage (턴 완료)
```json
{
  "type": "turn_complete",
  "inputText": "안녕하세요",
  "outputText": "Hello"
}
```

#### 5. SpeechStateMessage (음성 상태)
```json
{
  "type": "speech_state",
  "state": "speaking",  // "speaking" | "silent" | "processing"
  "timestamp": 1702345678900
}
```

#### 6. ErrorMessage (에러)
```json
{
  "type": "error",
  "message": "Session not initialized",
  "code": "NOT_READY"  // Optional
}
```

**상세 프로토콜 문서**: [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md)

---

## 📂 프로젝트 구조

```
live-interpreter-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 애플리케이션 진입점
│   ├── websocket/
│   │   ├── __init__.py
│   │   ├── handler.py             # WebSocket 핸들러
│   │   └── protocol.py            # 메시지 파싱 유틸리티
│   ├── services/
│   │   ├── __init__.py
│   │   └── gemini_service.py      # Gemini API 통합
│   ├── models/
│   │   ├── __init__.py
│   │   └── messages.py            # Pydantic 메시지 모델
│   └── utils/
│       ├── __init__.py
│       └── logging.py             # 로깅 설정
├── .env                           # 환경 변수 (gitignore)
├── .env.example                   # 환경 변수 템플릿
├── requirements.txt               # Python 의존성
├── README.md                      # 이 문서
├── ARCHITECTURE_ANALYSIS.md       # 아키텍처 상세 분석
└── WEBSOCKET_PROTOCOL.md          # WebSocket 프로토콜 명세
```

---

## 👨‍💻 개발 가이드

### 로컬 개발 환경 설정

```bash
# 가상 환경 활성화
source .venv/bin/activate

# 개발 모드로 실행 (자동 리로드)
uvicorn app.main:app --reload --log-level debug

# 또는 Python으로 직접 실행
python -m app.main
```

### 코드 스타일

이 프로젝트는 다음 코딩 스타일을 따릅니다:

- **타입 힌트**: 모든 함수에 타입 어노테이션 사용
- **Docstring**: 주요 클래스/함수에 설명 추가
- **비동기 우선**: I/O 작업은 async/await 사용
- **Pydantic 검증**: 메시지는 Pydantic 모델로 검증

### 테스트

```bash
# 테스트 실행 (향후 추가 예정)
pytest tests/
```

---

## 🔧 문제 해결

### 자주 묻는 질문 (FAQ)

#### Q1. `GEMINI_API_KEY not set` 에러
**A**: `.env` 파일에 올바른 API 키를 설정했는지 확인하세요.

```bash
# .env 파일 확인
cat .env | grep GEMINI_API_KEY
```

#### Q2. WebSocket 연결이 끊김
**A**: CORS 설정과 클라이언트 오리진을 확인하세요.

```bash
# CORS_ORIGINS에 클라이언트 주소 추가
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

#### Q3. SSL 인증서 에러 (프로덕션)
**A**: 개발 환경에서는 SSL 검증을 비활성화했습니다. **프로덕션에서는 반드시 제거**하세요.

```python
# app/services/gemini_service.py:23-29 제거 필요
```

#### Q4. VAD가 너무 민감/둔감함
**A**: `.env`에서 `VAD_THRESHOLD` 값을 조정하세요.

```bash
# 더 민감하게 (낮은 소리도 감지)
VAD_THRESHOLD=300

# 덜 민감하게 (큰 소리만 감지)
VAD_THRESHOLD=700

# VAD 비활성화
VAD_THRESHOLD=0
```

### 디버깅 팁

```bash
# 1. 로그 레벨을 DEBUG로 설정
LOG_LEVEL=DEBUG

# 2. 서버 로그 확인
tail -f logs/app.log  # 로그 파일이 있는 경우

# 3. WebSocket 메시지 디버깅
# 브라우저 개발자 도구 > Network > WS 탭 확인
```

---

## 🔐 보안 고려사항

### ⚠️ 프로덕션 배포 전 체크리스트

- [ ] SSL 인증서 검증 복구 (`gemini_service.py:23-29` 제거)
- [ ] `.env` 파일을 `.gitignore`에 추가
- [ ] `CORS_ORIGINS`를 프로덕션 도메인으로 제한
- [ ] `DEBUG=False` 설정
- [ ] Rate Limiting 추가
- [ ] 인증/인가 시스템 구현
- [ ] API 키를 환경 변수 또는 비밀 관리 시스템으로 관리

---

## 📚 추가 문서

- [ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md) - 상세 아키텍처 및 코드 분석
- [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md) - WebSocket 프로토콜 명세
- [SPEECH_STATE_IMPLEMENTATION.md](SPEECH_STATE_IMPLEMENTATION.md) - 음성 상태 구현
- [FRONTEND_IMPLEMENTATION_GUIDE.md](FRONTEND_IMPLEMENTATION_GUIDE.md) - 프론트엔드 연동 가이드

---

## 🤝 기여하기

이슈 제보 및 Pull Request를 환영합니다!

---

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

---

## 📞 문의

프로젝트 관련 문의사항은 Issues를 통해 남겨주세요.

---

**Last Updated**: 2025-12-12
**Version**: 1.0.0
