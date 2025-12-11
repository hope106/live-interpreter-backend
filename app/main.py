import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .websocket.handler import WebSocketHandler

load_dotenv()


def _allowed_origins() -> List[str]:
    env_origins = os.getenv("CORS_ORIGINS")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    # Defaults cover local dev plus placeholder Netlify host.
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://your-netlify-app.netlify.app",
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Entry point for real-time interpreter sessions."""
    handler = WebSocketHandler(websocket)
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
