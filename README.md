# Gemini Live Interpreter Backend (Phase 1)

FastAPI + WebSocket 서버로 클라이언트와 Gemini Live API 사이의 브로커 역할을 수행합니다.

## 로컬 실행

### 1. 환경 설정

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 필요한 값들을 설정하세요:

```bash
cp .env.example .env
```

`.env` 파일에서 다음 값을 설정:
- `GEMINI_API_KEY`: Gemini API 키 ([여기서 발급](https://aistudio.google.com/app/apikey))
- 기타 필요한 설정값들

### 3. 서버 실행

```bash
uvicorn app.main:app --reload
```

### 환경변수

| 변수 | 설명 | 기본값 |
| --- | --- | --- |
| `GEMINI_API_KEY` | Gemini Live API 키 (필수) | - |
| `HOST` | 서버 호스트 | localhost |
| `PORT` | 서버 포트 | 8000 |
| `DEBUG` | 디버그 모드 | True |
| `CORS_ORIGINS` | CORS 허용 도메인 (`,`로 구분) | http://localhost:3000,http://127.0.0.1:3000 |
| `LOG_LEVEL` | 로그 레벨 | INFO |

## 엔드포인트

| 경로 | 설명 |
| --- | --- |
| `GET /health` | 헬스체크 |
| `WS /ws` | 실시간 통역 WebSocket |

WebSocket 프로토콜은 `project-analysis_v2.md`의 메시지 명세를 따릅니다.
