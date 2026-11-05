"""FastAPI Main Application and Edge Server Entrypoint."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.edge_server.config import settings
from src.edge_server.cameras.manager import camera_manager
from src.edge_server.recording.manager import recording_manager
from src.edge_server.api.v1 import health, system, cameras, events, recordings

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("edge_server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager handling startup and graceful shutdown."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    settings.ensure_directories()
    
    # Initialize configured cameras from database
    camera_manager.initialize_cameras()
    logger.info("Edge server subsystems initialized successfully")
    
    yield
    
    logger.info("Initiating graceful edge server shutdown...")
    # Stop all streams
    for cam in camera_manager.get_all_cameras():
        camera_manager.stop_camera(cam["id"])
    
    # Stop any active recording sessions
    active_recs = list(recording_manager.active_sessions.keys())
    for cam_id in active_recs:
        recording_manager.stop_recording(cam_id)
        
    logger.info("All stream and recording workers terminated cleanly")


# Create FastAPI instance
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local Edge Video Monitoring System with RTSP ingestion and motion recording.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(cameras.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(recordings.router, prefix="/api/v1")

# Mount Static Files & Templates
BASE_PATH = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_PATH / "web" / "static"
TEMPLATES_DIR = BASE_PATH / "web" / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    """Serve the single-page industrial-minimalist monitoring dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": settings.APP_NAME, "version": settings.APP_VERSION}
    )
