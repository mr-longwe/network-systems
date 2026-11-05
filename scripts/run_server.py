"""Entry point script to run the Edge Server application with Uvicorn."""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from src.edge_server.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.APP_NAME} on http://{settings.EDGE_HOST}:{settings.EDGE_PORT}")
    print(f"Local machine dashboard access: http://localhost:{settings.EDGE_PORT}")
    print(f"LAN / WLAN mobile access:       http://192.168.1.161:{settings.EDGE_PORT}")
    uvicorn.run(
        "src.edge_server.main:app",
        host=settings.EDGE_HOST,
        port=settings.EDGE_PORT,
        reload=settings.EDGE_DEBUG,
        log_level="info"
    )
