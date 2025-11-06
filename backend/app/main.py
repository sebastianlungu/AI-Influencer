from __future__ import annotations

import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.routes import router
from app.core.config import settings
from app.core.logging import log
from app.core.paths import get_data_path, PROJECT_ROOT
from app.core.scheduler import start_scheduler, stop_scheduler


# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app."""
    # Startup
    log.info("app_startup")

    # Verify ffmpeg and ffprobe are available (required for video/audio processing)
    _check_ffmpeg_presence()

    start_scheduler()
    yield
    # Shutdown
    log.info("app_shutdown")
    stop_scheduler()


def _check_ffmpeg_presence() -> None:
    """Verify ffmpeg and ffprobe are installed and accessible.

    Raises:
        RuntimeError: If ffmpeg or ffprobe is missing
    """
    # Check ffmpeg
    try:
        subprocess.run(
            [settings.ffmpeg_path, "-version"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        log.info(f"STARTUP_CHECK ffmpeg found at {settings.ffmpeg_path}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise RuntimeError(
            f"STARTUP_FAILED: ffmpeg not found at '{settings.ffmpeg_path}'. "
            f"Install ffmpeg or set FFMPEG_PATH in .env. Error: {e}"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"STARTUP_FAILED: ffmpeg check timeout at '{settings.ffmpeg_path}'"
        )

    # Check ffprobe
    try:
        subprocess.run(
            [settings.ffprobe_path, "-version"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        log.info(f"STARTUP_CHECK ffprobe found at {settings.ffprobe_path}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise RuntimeError(
            f"STARTUP_FAILED: ffprobe not found at '{settings.ffprobe_path}'. "
            f"Install ffmpeg (includes ffprobe) or set FFPROBE_PATH in .env. Error: {e}"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"STARTUP_FAILED: ffprobe check timeout at '{settings.ffprobe_path}'"
        )


app = FastAPI(lifespan=lifespan)

# Add rate limiter to app state
app.state.limiter = limiter


# CORS middleware - restrict to localhost in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # Frontend dev server
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


# Serve app directory files via endpoint (must be BEFORE router/mounts to take precedence)
@app.get("/app/{full_path:path}")
async def serve_app_files(full_path: str):
    """Serve files from backend/app/ directory."""
    backend_app_dir = Path(__file__).resolve().parent
    file_path = backend_app_dir / full_path

    # Security check: ensure path is within backend/app/
    try:
        file_path = file_path.resolve()
        backend_app_dir = backend_app_dir.resolve()
        if not str(file_path).startswith(str(backend_app_dir)):
            return JSONResponse({"error": "Invalid path"}, status_code=403)
    except Exception:
        return JSONResponse({"error": "Invalid path"}, status_code=403)

    if not file_path.exists() or not file_path.is_file():
        return JSONResponse({"error": "Not found"}, status_code=404)

    return FileResponse(file_path)


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


@app.get("/debug/image-path")
def debug_image_path() -> dict:
    """Debug endpoint to check image path resolution."""
    from pathlib import Path
    import os

    backend_app = Path(__file__).resolve().parent
    image_rel_path = "data/generated/images/9311562dfcf5d60a.png"
    image_full_path = backend_app / image_rel_path

    return {
        "backend_app_dir": str(backend_app),
        "image_rel_path": image_rel_path,
        "image_full_path": str(image_full_path),
        "file_exists": image_full_path.exists(),
        "file_size": image_full_path.stat().st_size if image_full_path.exists() else None,
        "is_file": image_full_path.is_file() if image_full_path.exists() else None,
    }
