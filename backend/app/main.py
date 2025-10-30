from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.routes import router
from app.core.logging import log
from app.core.paths import get_data_path
from app.core.scheduler import start_scheduler, stop_scheduler


# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app."""
    # Startup
    log.info("app_startup")
    start_scheduler()
    yield
    # Shutdown
    log.info("app_shutdown")
    stop_scheduler()


app = FastAPI(lifespan=lifespan)

# Add rate limiter to app state
app.state.limiter = limiter


# CORS middleware - restrict to localhost in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def body_size_limit_middleware(request: Request, call_next):
    """Limits request body size to prevent DoS attacks.

    Raises:
        JSONResponse: 413 if body exceeds 2MB
    """
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 2_000_000:
        log.warning(f"body_too_large client={get_remote_address(request)} size={content_length}")
        return JSONResponse(
            {"error": "Payload too large (max 2MB)"},
            status_code=413,
        )
    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Adds security headers to all responses."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# API routes
app.include_router(router, prefix="/api")

# Serve media files
app.mount("/media", StaticFiles(directory=str(get_data_path())), name="media")


@app.get("/")
def root() -> dict:
    """Root endpoint."""
    return {
        "name": "AI Influencer Backend",
        "docs": "/docs",
        "health": "/api/healthz",
    }
