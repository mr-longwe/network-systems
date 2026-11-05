"""Health check and application heartbeat endpoint."""

import time
from datetime import datetime, timezone
from fastapi import APIRouter
from src.edge_server.config import settings
from src.edge_server.system_metrics import START_TIME, get_system_metrics
from src.edge_server.cameras.manager import camera_manager

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def get_health():
    """Health check endpoint indicating service operational readiness."""
    cameras = camera_manager.get_all_cameras()
    online_count = sum(1 for c in cameras if c.get("status") == "online")

    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "cameras_total": len(cameras),
        "cameras_online": online_count
    }

