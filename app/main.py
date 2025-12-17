import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse

from .websocket.handler import WebSocketHandler
from .auth.google_oauth import get_google_login_url, exchange_code_for_token, get_user_info
from .auth.jwt_handler import create_access_token, verify_access_token
from .auth.whitelist import whitelist

load_dotenv(override=True)


def _allowed_origins() -> List[str]:
    env_origins = os.getenv("CORS_ORIGINS")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    # Defaults cover local dev plus placeholder Netlify host.
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://graceful-semifreddo-4456f6.netlify.app",
    ]


app = FastAPI(title="Gemini Live Interpreter Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Simple readiness endpoint for monitors."""
    return {"status": "ok"}


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


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug
    )
