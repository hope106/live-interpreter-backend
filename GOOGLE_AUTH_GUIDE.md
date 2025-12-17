# Google OAuth 2.0 인증 구현 가이드 - Backend

**Gemini Live Interpreter - 사용자 인증 (Backend)**

이 문서는 FastAPI 백엔드에서 Google OAuth 2.0 인증을 구현하는 가이드입니다.

---

## 📋 목차

- [시스템 개요](#시스템-개요)
- [구현 단계](#구현-단계)
- [패키지 설치](#패키지-설치)
- [환경 변수 설정](#환경-변수-설정)
- [구현 상세](#구현-상세)
- [테스트](#테스트)
- [배포](#배포)

---

## 🎯 시스템 개요

### 인증 플로우
```
1. 프론트엔드에서 /auth/google/login 호출
2. Google OAuth 2.0 로그인 URL 생성 및 리다이렉트
3. Google에서 사용자 인증 후 authorization code 발급
4. /auth/google/callback으로 리다이렉트 (code 포함)
5. authorization code로 access token 교환
6. access token으로 사용자 정보 조회 (email, name)
7. 화이트리스트에서 이메일 확인
8. 허용된 사용자인 경우 JWT 토큰 생성
9. 프론트엔드로 리다이렉트 (토큰 포함)
```

### 주요 기능
- Google OAuth 2.0 인증
- 화이트리스트 기반 접근 제어
- JWT 토큰 생성 및 검증
- WebSocket 인증 미들웨어

---

## 📦 구현 단계

### Phase 1: Google Cloud Console 설정
1. OAuth 2.0 Client ID 생성
2. Redirect URI 설정

### Phase 2: 패키지 설치
1. 필요한 Python 패키지 설치

### Phase 3: 환경 변수 설정
1. Google OAuth 2.0 설정
2. JWT 설정
3. 화이트리스트 설정

### Phase 4: 코드 구현
1. 화이트리스트 관리 모듈
2. JWT 토큰 핸들러
3. Google OAuth 핸들러
4. 인증 엔드포인트
5. WebSocket 인증

---

## 🔧 패키지 설치

**requirements.txt** (추가 의존성)
```txt
# 기존 의존성
fastapi==0.124.2
uvicorn==0.38.0
websockets==15.0.1
google-generativeai==1.55.0
pydantic==2.7.0
python-dotenv==1.2.1
httpx==0.28.1

# 인증 관련 추가 의존성
google-auth==2.38.0
google-auth-oauthlib==1.3.0
google-auth-httplib2==0.2.0
PyJWT==2.10.0
cryptography==44.0.0
python-multipart==0.0.20
```

설치:
```bash
cd live-interpreter-backend
source .venv/bin/activate
pip install google-auth google-auth-oauthlib google-auth-httplib2 PyJWT cryptography python-multipart
```

---

## ⚙️ 환경 변수 설정

**.env** (프로젝트 루트)
```bash
# 기존 환경 변수
GEMINI_API_KEY=your_gemini_api_key
HOST=localhost
PORT=8000
DEBUG=True
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Google OAuth 2.0 설정
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# JWT 설정
JWT_SECRET_KEY=your_jwt_secret_key_minimum_32_characters
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# 프론트엔드 URL (OAuth 콜백 후 리다이렉트)
FRONTEND_URL=http://localhost:5173

# 화이트리스트 설정 (방법 1: 환경 변수)
ALLOWED_EMAILS=user1@example.com,user2@gmail.com,admin@company.com

# 화이트리스트 설정 (방법 2: 파일 경로)
# WHITELIST_FILE=./allowed_users.txt
```

### JWT Secret Key 생성
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 화이트리스트 파일 생성 (옵션)
```bash
# allowed_users.txt
user1@example.com
user2@gmail.com
admin@company.com
```

---

## 💻 구현 상세

### 1. 디렉토리 구조 생성

```bash
cd app
mkdir auth
touch auth/__init__.py
touch auth/whitelist.py
touch auth/jwt_handler.py
touch auth/google_oauth.py
```

---

### 2. 화이트리스트 관리

**app/auth/__init__.py**
```python
# 빈 파일 또는 다음 내용 추가
from .whitelist import whitelist
from .jwt_handler import create_access_token, verify_access_token
from .google_oauth import get_google_login_url, exchange_code_for_token, get_user_info

__all__ = [
    "whitelist",
    "create_access_token",
    "verify_access_token",
    "get_google_login_url",
    "exchange_code_for_token",
    "get_user_info",
]
```

**app/auth/whitelist.py**
```python
from __future__ import annotations

import os
from typing import Set
from dotenv import load_dotenv

load_dotenv()


class UserWhitelist:
    """허용된 사용자 이메일 관리"""

    def __init__(self):
        self.allowed_emails: Set[str] = set()
        self._load_whitelist()

    def _load_whitelist(self) -> None:
        """환경 변수 또는 파일에서 화이트리스트 로드"""
        # 방법 1: 환경 변수에서 로드
        env_emails = os.getenv("ALLOWED_EMAILS", "")
        if env_emails:
            self.allowed_emails.update(
                email.strip().lower() for email in env_emails.split(",") if email.strip()
            )

        # 방법 2: 파일에서 로드
        whitelist_file = os.getenv("WHITELIST_FILE")
        if whitelist_file and os.path.exists(whitelist_file):
            with open(whitelist_file, "r") as f:
                file_emails = [line.strip().lower() for line in f if line.strip() and not line.startswith("#")]
                self.allowed_emails.update(file_emails)

    def is_allowed(self, email: str) -> bool:
        """이메일이 화이트리스트에 있는지 확인"""
        return email.lower() in self.allowed_emails

    def add_email(self, email: str) -> bool:
        """이메일을 화이트리스트에 추가"""
        email_lower = email.lower()
        if email_lower not in self.allowed_emails:
            self.allowed_emails.add(email_lower)
            self._save_to_file()
            return True
        return False

    def remove_email(self, email: str) -> bool:
        """이메일을 화이트리스트에서 제거"""
        email_lower = email.lower()
        if email_lower in self.allowed_emails:
            self.allowed_emails.discard(email_lower)
            self._save_to_file()
            return True
        return False

    def _save_to_file(self) -> None:
        """화이트리스트를 파일에 저장"""
        whitelist_file = os.getenv("WHITELIST_FILE")
        if whitelist_file:
            with open(whitelist_file, "w") as f:
                f.write("\n".join(sorted(self.allowed_emails)))


# 싱글톤 인스턴스
whitelist = UserWhitelist()
```

---

### 3. JWT 토큰 관리

**app/auth/jwt_handler.py**
```python
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))


def create_access_token(email: str, name: Optional[str] = None) -> str:
    """JWT 액세스 토큰 생성"""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "email": email,
        "name": name,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    encoded_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Optional[dict]:
    """JWT 액세스 토큰 검증"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # 토큰 만료
    except jwt.InvalidTokenError:
        return None  # 유효하지 않은 토큰
```

---

### 4. Google OAuth 2.0 핸들러

**app/auth/google_oauth.py**
```python
from __future__ import annotations

import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# Google OAuth 2.0 엔드포인트
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def get_google_login_url() -> str:
    """Google 로그인 URL 생성"""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    query_string = "&".join(f"{key}={value}" for key, value in params.items())
    return f"{GOOGLE_AUTH_URL}?{query_string}"


async def exchange_code_for_token(code: str) -> Optional[dict]:
    """Authorization code를 access token으로 교환"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error exchanging code for token: {e}")
            return None


async def get_user_info(access_token: str) -> Optional[dict]:
    """Access token으로 사용자 정보 조회"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None
```

---

### 5. main.py 수정

**app/main.py** (인증 엔드포인트 추가)

기존 imports에 추가:
```python
from typing import List, Optional
from fastapi import HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse

from .auth.google_oauth import get_google_login_url, exchange_code_for_token, get_user_info
from .auth.jwt_handler import create_access_token, verify_access_token
from .auth.whitelist import whitelist
```

인증 엔드포인트 추가 (health check 아래):
```python
# ============ Google OAuth 2.0 엔드포인트 ============

@app.get("/auth/google/login", tags=["auth"])
async def google_login():
    """Google 로그인 페이지로 리다이렉트"""
    login_url = get_google_login_url()
    return RedirectResponse(url=login_url)


@app.get("/auth/google/callback", tags=["auth"])
async def google_callback(code: str = Query(...)):
    """Google OAuth 2.0 콜백 처리"""
    # 1. Authorization code를 access token으로 교환
    token_data = await exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token received")

    # 2. Access token으로 사용자 정보 조회
    user_info = await get_user_info(access_token)
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info")

    email = user_info.get("email")
    name = user_info.get("name")

    # 3. 화이트리스트 확인
    if not whitelist.is_allowed(email):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Email {email} is not in the whitelist."
        )

    # 4. JWT 토큰 생성
    jwt_token = create_access_token(email=email, name=name)

    # 5. 프론트엔드로 리다이렉트 (토큰을 쿼리 파라미터로 전달)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    redirect_url = f"{frontend_url}/auth/callback?token={jwt_token}"
    return RedirectResponse(url=redirect_url)


@app.get("/auth/verify", tags=["auth"])
async def verify_token(token: str = Query(...)):
    """JWT 토큰 검증"""
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return JSONResponse(content={
        "valid": True,
        "email": payload.get("email"),
        "name": payload.get("name"),
    })
```

WebSocket 엔드포인트 수정:
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)) -> None:
    """Entry point for real-time interpreter sessions (with authentication)"""

    # 토큰 검증
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return

    payload = verify_access_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    email = payload.get("email")
    if not whitelist.is_allowed(email):
        await websocket.close(code=1008, reason="Access denied")
        return

    # 인증 성공 - WebSocket 핸들러 실행
    handler = WebSocketHandler(websocket, user_email=email)
    await handler.handle()
```

---

### 6. WebSocketHandler 수정

**app/websocket/handler.py**

클래스 생성자 수정:
```python
class WebSocketHandler:
    """Routes client WebSocket messages to the Gemini Live session."""

    def __init__(self, websocket: WebSocket, user_email: str = None):
        self.websocket = websocket
        self.session_id: str = ""
        self.user_email = user_email  # 추가
        self.gemini_service: Optional[GeminiService] = None
        self.use_whisper = False
        self.receive_task: Optional[asyncio.Task] = None
```

handle 메서드 수정 (로깅에 사용자 정보 추가):
```python
async def handle(self) -> None:
    await self.websocket.accept()
    logger.debug("WebSocket accepted from %s (user: %s)",
                self.websocket.client, self.user_email)
    # ... 나머지 코드 동일
```

---

## 🧪 테스트

### 1. Google Cloud Console 설정

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 생성 또는 선택
3. "APIs & Services" > "Credentials" 이동
4. "Create Credentials" > "OAuth 2.0 Client ID" 선택
5. Application type: "Web application"
6. Authorized redirect URIs 추가:
   ```
   http://localhost:8000/auth/google/callback
   ```
7. Client ID와 Client Secret을 `.env`에 설정

### 2. 로컬 테스트

```bash
# 가상 환경 활성화
source .venv/bin/activate

# 서버 실행
uvicorn app.main:app --reload

# 또는
python -m app.main
```

### 3. 엔드포인트 테스트

```bash
# Health check
curl http://localhost:8000/health

# 로그인 URL 확인 (브라우저에서 열기)
curl http://localhost:8000/auth/google/login

# API 문서 확인
open http://localhost:8000/docs
```

### 4. 화이트리스트 관리

환경 변수에서 직접 추가:
```bash
ALLOWED_EMAILS=user1@gmail.com,user2@example.com
```

파일로 관리:
```bash
echo "user3@example.com" >> allowed_users.txt
```

관리 스크립트 (옵션):

**scripts/manage_whitelist.py**
```python
#!/usr/bin/env python3
"""화이트리스트 관리 CLI 도구"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.auth.whitelist import whitelist


def add_user(email: str):
    if whitelist.add_email(email):
        print(f"✅ Added: {email}")
    else:
        print(f"ℹ️  Already exists: {email}")


def remove_user(email: str):
    if whitelist.remove_email(email):
        print(f"✅ Removed: {email}")
    else:
        print(f"❌ Not found: {email}")


def list_users():
    print("Allowed users:")
    for email in sorted(whitelist.allowed_emails):
        print(f"  - {email}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manage_whitelist.py [add|remove|list] [email]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        list_users()
    elif command == "add" and len(sys.argv) == 3:
        add_user(sys.argv[2])
    elif command == "remove" and len(sys.argv) == 3:
        remove_user(sys.argv[2])
    else:
        print("Invalid command")
        sys.exit(1)
```

사용:
```bash
python scripts/manage_whitelist.py list
python scripts/manage_whitelist.py add user@example.com
python scripts/manage_whitelist.py remove user@example.com
```

---

## 🚀 배포

### 프로덕션 체크리스트

- [ ] Google OAuth Redirect URI에 프로덕션 도메인 추가
  ```
  https://yourdomain.com/auth/google/callback
  ```
- [ ] `.env`에 안전한 JWT_SECRET_KEY 설정
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] CORS_ORIGINS를 프로덕션 도메인으로 제한
  ```bash
  CORS_ORIGINS=https://yourdomain.com
  ```
- [ ] DEBUG=False 설정
- [ ] HTTPS 적용 및 SSL 인증서 설정
- [ ] 화이트리스트 파일 `.gitignore`에 추가
  ```bash
  echo "allowed_users.txt" >> .gitignore
  ```
- [ ] FRONTEND_URL을 프로덕션 도메인으로 설정
  ```bash
  FRONTEND_URL=https://yourdomain.com
  ```

### 환경 변수 (프로덕션)

```bash
# .env (프로덕션)
GEMINI_API_KEY=your_production_api_key
HOST=0.0.0.0
PORT=8000
DEBUG=False

GOOGLE_CLIENT_ID=your_production_client_id
GOOGLE_CLIENT_SECRET=your_production_client_secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback

JWT_SECRET_KEY=production_secret_key_32_characters_minimum
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

FRONTEND_URL=https://yourdomain.com
CORS_ORIGINS=https://yourdomain.com

ALLOWED_EMAILS=admin@company.com
# 또는
WHITELIST_FILE=/path/to/allowed_users.txt
```

---

## 📁 파일 구조

```
live-interpreter-backend/
├── app/
│   ├── auth/                        # 인증 모듈 (신규)
│   │   ├── __init__.py
│   │   ├── whitelist.py
│   │   ├── jwt_handler.py
│   │   └── google_oauth.py
│   ├── main.py                      # 인증 엔드포인트 추가
│   ├── websocket/
│   │   └── handler.py               # user_email 파라미터 추가
│   └── ...
├── scripts/
│   └── manage_whitelist.py          # 화이트리스트 관리 도구 (옵션)
├── .env                             # 환경 변수
├── requirements.txt                 # 의존성 추가
└── allowed_users.txt                # 화이트리스트 파일 (옵션)
```

---

## 🔧 트러블슈팅

### Q1. "GOOGLE_CLIENT_ID not set" 에러
**A**: `.env` 파일에 Google OAuth 설정이 올바른지 확인
```bash
cat .env | grep GOOGLE
```

### Q2. "Access denied" 에러
**A**: 로그인하려는 이메일이 화이트리스트에 있는지 확인
```bash
python scripts/manage_whitelist.py list
```

### Q3. JWT 토큰 검증 실패
**A**:
- JWT_SECRET_KEY가 일치하는지 확인
- 토큰이 만료되지 않았는지 확인 (JWT_EXPIRATION_HOURS)

### Q4. Google OAuth 콜백 실패
**A**:
- Google Cloud Console에서 Redirect URI 확인
- GOOGLE_REDIRECT_URI 환경 변수 확인
- 로그에서 에러 메시지 확인

---

## 🔐 보안 고려사항

### 1. JWT Secret Key
```bash
# 안전한 키 생성
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 환경 변수로 관리 (절대 코드에 하드코딩 금지)
JWT_SECRET_KEY=generated_secret_key
```

### 2. HTTPS 필수
- 프로덕션에서는 반드시 HTTPS 사용
- Google OAuth는 HTTPS 필수 (localhost 제외)

### 3. CORS 설정
```python
# 프로덕션에서는 정확한 도메인만 허용
CORS_ORIGINS=https://yourdomain.com
```

### 4. Rate Limiting
- 인증 엔드포인트에 Rate Limiting 추가 권장
- slowapi 등의 라이브러리 사용 고려

### 5. 로깅
- 민감한 정보(토큰, 비밀번호) 로깅 금지
- 로그인 시도 및 실패 기록

---

**Last Updated**: 2025-12-17
**Version**: 1.0.0
