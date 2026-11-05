"""Camera registration, control, and video streaming endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from src.edge_server.cameras.manager import camera_manager
from src.edge_server.streams.manager import stream_manager
from src.edge_server.config import settings

router = APIRouter(prefix="/cameras", tags=["Cameras"])


class CameraCreateRequest(BaseModel):
    id: str = Field(..., description="Unique alphanumeric camera identifier (e.g. cam-1)")
    name: str = Field(..., description="Friendly human-readable camera name")
    rtsp_url: str = Field(..., description="RTSP stream URL (e.g. rtsp://192.168.1.110:8080/h264_pcm.sdp)")
    enabled: bool = Field(default=True, description="Whether stream ingestion is active")
    fps: int = Field(default=10, ge=1, le=30, description="Target processing frame rate")
    resolution: str = Field(default="640x480", description="Stream resolution (e.g. 640x480)")


class CameraUpdateRequest(BaseModel):
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    enabled: Optional[bool] = None
    fps: Optional[int] = Field(default=None, ge=1, le=30)
    resolution: Optional[str] = None


@router.get("", response_model=List[dict])
def list_cameras():
    """List all registered cameras with their current live status and telemetry."""
    return camera_manager.get_all_cameras()


@router.get("/{camera_id}")
def get_camera(camera_id: str):
    """Retrieve details and live status for a specific camera."""
    cam = camera_manager.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    return cam


@router.post("", status_code=status.HTTP_201_CREATED)
def register_camera(payload: CameraCreateRequest):
    """Register a new RTSP camera."""
    existing = camera_manager.get_camera(payload.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Camera with ID '{payload.id}' already exists")
    
    record = camera_manager.register_camera(
        camera_id=payload.id,
        name=payload.name,
        rtsp_url=payload.rtsp_url,
        enabled=payload.enabled,
        fps=payload.fps,
        resolution=payload.resolution
    )
    return record


@router.put("/{camera_id}")
def update_camera(camera_id: str, payload: CameraUpdateRequest):
    """Update camera configuration."""
    cam = camera_manager.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")

    name = payload.name if payload.name is not None else cam["name"]
    rtsp_url = payload.rtsp_url if payload.rtsp_url is not None else cam["rtsp_url"]
    enabled = payload.enabled if payload.enabled is not None else bool(cam.get("enabled"))
    fps = payload.fps if payload.fps is not None else cam.get("fps", settings.DEFAULT_FPS)
    resolution = payload.resolution if payload.resolution is not None else cam.get("resolution", "640x480")

    updated = camera_manager.register_camera(
        camera_id=camera_id,
        name=name,
        rtsp_url=rtsp_url,
        enabled=enabled,
        fps=fps,
        resolution=resolution
    )
    return updated


@router.delete("/{camera_id}")
def delete_camera(camera_id: str):
    """Remove a camera and terminate its stream."""
    success = camera_manager.delete_camera(camera_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    return {"message": f"Camera '{camera_id}' deleted successfully"}


@router.post("/{camera_id}/start")
def start_camera(camera_id: str):
    """Start stream worker for a camera."""
    cam = camera_manager.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    camera_manager.start_camera(camera_id)
    return {"status": "started", "camera_id": camera_id}


@router.post("/{camera_id}/stop")
def stop_camera(camera_id: str):
    """Stop stream worker for a camera."""
    cam = camera_manager.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    camera_manager.stop_camera(camera_id)
    return {"status": "stopped", "camera_id": camera_id}


@router.get("/{camera_id}/stream")
def stream_camera(camera_id: str):
    """Stream live camera feed using multipart/x-mixed-replace (MJPEG)."""
    return StreamingResponse(
        stream_manager.generate_mjpeg(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/{camera_id}/snapshot")
def camera_snapshot(camera_id: str):
    """Fetch single instant JPEG frame snapshot."""
    jpeg_bytes = stream_manager.get_latest_jpeg(camera_id)
    return Response(content=jpeg_bytes, media_type="image/jpeg")

