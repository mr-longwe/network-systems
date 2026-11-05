"""System status and host telemetry endpoints."""

from fastapi import APIRouter
from src.edge_server.system_metrics import get_system_metrics

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/status")
def system_status():
    """Retrieve full system health, CPU, memory, disk, and network stats."""
    return get_system_metrics()

