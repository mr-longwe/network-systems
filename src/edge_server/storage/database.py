"""SQLite Database manager for camera, event, and recording metadata."""

import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from src.edge_server.config import settings

logger = logging.getLogger("edge_server.storage")


class DatabaseManager:
    """Manages SQLite connection pooling and metadata schemas."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Context manager for SQLite connections with row dict factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize SQLite database tables and indexes."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Cameras Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cameras (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    rtsp_url TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'offline',
                    resolution TEXT DEFAULT '640x480',
                    fps INTEGER DEFAULT 10,
                    last_seen TEXT,
                    created_at TEXT NOT NULL
                );
            """)

            # Events Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    camera_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    details TEXT,
                    FOREIGN KEY (camera_id) REFERENCES cameras (id) ON DELETE CASCADE
                );
            """)

            # Recordings Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recordings (
                    id TEXT PRIMARY KEY,
                    camera_id TEXT NOT NULL,
                    event_id TEXT,
                    file_path TEXT NOT NULL,
                    file_size_bytes INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0.0,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL DEFAULT 'recording',
                    FOREIGN KEY (camera_id) REFERENCES cameras (id) ON DELETE CASCADE,
                    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE SET NULL
                );
            """)

            # Indexes for efficient query filtering
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_camera ON events(camera_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_time DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recordings_camera ON recordings(camera_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recordings_start ON recordings(start_time DESC);")
            
            logger.info(f"Database initialized at {self.db_path}")

    # Camera Queries
    def get_all_cameras(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM cameras ORDER BY created_at ASC;").fetchall()
            return [dict(r) for r in rows]

    def get_camera(self, camera_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM cameras WHERE id = ?;", (camera_id,)).fetchone()
            return dict(row) if row else None

    def upsert_camera(self, camera_data: Dict[str, Any]) -> Dict[str, Any]:
        with self.get_connection() as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                INSERT INTO cameras (id, name, rtsp_url, enabled, status, resolution, fps, last_seen, created_at)
                VALUES (:id, :name, :rtsp_url, :enabled, :status, :resolution, :fps, :last_seen, :created_at)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    rtsp_url = excluded.rtsp_url,
                    enabled = excluded.enabled,
                    status = excluded.status,
                    resolution = excluded.resolution,
                    fps = excluded.fps,
                    last_seen = excluded.last_seen;
            """, {
                "id": camera_data["id"],
                "name": camera_data["name"],
                "rtsp_url": camera_data["rtsp_url"],
                "enabled": int(camera_data.get("enabled", True)),
                "status": camera_data.get("status", "offline"),
                "resolution": camera_data.get("resolution", "640x480"),
                "fps": camera_data.get("fps", 10),
                "last_seen": camera_data.get("last_seen"),
                "created_at": camera_data.get("created_at", now),
            })
        return self.get_camera(camera_data["id"])

    def update_camera_status(self, camera_id: str, status: str, last_seen: Optional[str] = None) -> None:
        with self.get_connection() as conn:
            if last_seen is None:
                last_seen = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE cameras SET status = ?, last_seen = ? WHERE id = ?;",
                (status, last_seen, camera_id)
            )

    def delete_camera(self, camera_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM cameras WHERE id = ?;", (camera_id,))
            return cursor.rowcount > 0

    # Event Queries
    def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO events (id, camera_id, event_type, start_time, end_time, status, details)
                VALUES (:id, :camera_id, :event_type, :start_time, :end_time, :status, :details);
            """, event_data)
        return self.get_event(event_data["id"])

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM events WHERE id = ?;", (event_id,)).fetchone()
            return dict(row) if row else None

    def update_event_status(self, event_id: str, status: str, end_time: Optional[str] = None) -> None:
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE events SET status = ?, end_time = ? WHERE id = ?;",
                (status, end_time, event_id)
            )

    def get_events(self, camera_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if camera_id:
                rows = conn.execute(
                    "SELECT * FROM events WHERE camera_id = ? ORDER BY start_time DESC LIMIT ?;",
                    (camera_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM events ORDER BY start_time DESC LIMIT ?;",
                    (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    # Recording Queries
    def create_recording(self, recording_data: Dict[str, Any]) -> Dict[str, Any]:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO recordings (id, camera_id, event_id, file_path, file_size_bytes, duration_seconds, start_time, end_time, status)
                VALUES (:id, :camera_id, :event_id, :file_path, :file_size_bytes, :duration_seconds, :start_time, :end_time, :status);
            """, recording_data)
        return self.get_recording(recording_data["id"])

    def get_recording(self, recording_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM recordings WHERE id = ?;", (recording_id,)).fetchone()
            return dict(row) if row else None

    def update_recording(self, recording_id: str, **kwargs) -> None:
        with self.get_connection() as conn:
            fields = []
            values = []
            for k, v in kwargs.items():
                fields.append(f"{k} = ?")
                values.append(v)
            values.append(recording_id)
            query = f"UPDATE recordings SET {', '.join(fields)} WHERE id = ?;"
            conn.execute(query, tuple(values))

    def get_recordings(self, camera_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if camera_id:
                rows = conn.execute(
                    "SELECT * FROM recordings WHERE camera_id = ? ORDER BY start_time DESC LIMIT ?;",
                    (camera_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM recordings ORDER BY start_time DESC LIMIT ?;",
                    (limit,)
                ).fetchall()
            return [dict(r) for r in rows]


db = DatabaseManager()

