from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.logging import log
from app.core.scheduler import start_scheduler, stop_scheduler


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

# API routes
app.include_router(router, prefix="/api")

# Serve media files
app.mount("/media", StaticFiles(directory="app/data"), name="media")


@app.get("/")
def root() -> dict:
    """Root endpoint."""
    return {
        "name": "AI Influencer Backend",
        "docs": "/docs",
        "health": "/api/healthz",
    }
