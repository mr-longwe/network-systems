"""Recording metadata and video playback endpoints."""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from src.edge_server.storage.database import db

router = APIRouter(prefix="/recordings", tags=["Recordings"])


@router.get("", response_model=List[dict])
def list_recordings(
    camera_id: Optional[str] = Query(None, description="Filter recordings by camera ID"),
    limit: int = Query(50, ge=1, le=200, description="Maximum recordings to return")
):
    """Retrieve recorded clips in reverse chronological order."""
    return db.get_recordings(camera_id=camera_id, limit=limit)


@router.get("/{recording_id}")
def get_recording(recording_id: str):
    """Retrieve metadata for a specific recording."""
    rec = db.get_recording(recording_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recording '{recording_id}' not found")
    return rec


@router.get("/{recording_id}/stream")
def play_recording(recording_id: str):
    """Stream recorded MP4 video directly to the browser for playback."""
    rec = db.get_recording(recording_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recording '{recording_id}' not found")

    file_path = Path(rec["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Recording video file not found on edge disk")

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=file_path.name
    )

