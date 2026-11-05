"""Event querying endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from src.edge_server.storage.database import db

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", response_model=List[dict])
def list_events(
    camera_id: Optional[str] = Query(None, description="Filter events by camera ID"),
    limit: int = Query(50, ge=1, le=200, description="Maximum events to return")
):
    """Retrieve motion and system events in reverse chronological order."""
    return db.get_events(camera_id=camera_id, limit=limit)


@router.get("/{event_id}")
def get_event(event_id: str):
    """Retrieve details for a specific event."""
    event = db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")
    return event

