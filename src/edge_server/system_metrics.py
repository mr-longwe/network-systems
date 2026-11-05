"""System hardware and resource utilization metrics using psutil."""

import time
import os
import psutil
from typing import Dict, Any
from src.edge_server.config import settings

START_TIME = time.time()
_last_net_io = None
_last_net_time = None


def get_system_metrics() -> Dict[str, Any]:
    """Gather live CPU, memory, disk, network, and process metrics."""
    global _last_net_io, _last_net_time

    # CPU Utilization
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_count = psutil.cpu_count(logical=True)

    # Virtual Memory
    vm = psutil.virtual_memory()
    memory_metrics = {
        "total_mb": round(vm.total / (1024 * 1024), 1),
        "available_mb": round(vm.available / (1024 * 1024), 1),
        "used_mb": round(vm.used / (1024 * 1024), 1),
        "percent": vm.percent
    }

    # Disk Space (Path where recordings/data are stored)
    disk_path = settings.DATA_DIR.resolve()
    # On Windows, drive anchor like C:\
    drive_anchor = disk_path.anchor or str(disk_path)
    du = psutil.disk_usage(drive_anchor)
    disk_metrics = {
        "drive": drive_anchor,
        "total_gb": round(du.total / (1024 ** 3), 2),
        "free_gb": round(du.free / (1024 ** 3), 2),
        "used_gb": round(du.used / (1024 ** 3), 2),
        "percent": du.percent
    }

    # Network I/O Rate
    net_io = psutil.net_io_counters()
    now = time.time()
    rx_rate_kbps = 0.0
    tx_rate_kbps = 0.0

    if _last_net_io is not None and _last_net_time is not None:
        dt = max(now - _last_net_time, 0.001)
        rx_rate_kbps = round(((net_io.bytes_recv - _last_net_io.bytes_recv) * 8) / (dt * 1000), 1)
        tx_rate_kbps = round(((net_io.bytes_sent - _last_net_io.bytes_sent) * 8) / (dt * 1000), 1)

    _last_net_io = net_io
    _last_net_time = now

    network_metrics = {
        "bytes_sent_mb": round(net_io.bytes_sent / (1024 * 1024), 2),
        "bytes_recv_mb": round(net_io.bytes_recv / (1024 * 1024), 2),
        "rx_kbps": rx_rate_kbps,
        "tx_kbps": tx_rate_kbps
    }

    # Application Process Stats
    proc = psutil.Process(os.getpid())
    proc_mem = round(proc.memory_info().rss / (1024 * 1024), 1)
    uptime_seconds = round(now - START_TIME, 1)

    return {
        "status": "healthy",
        "uptime_seconds": uptime_seconds,
        "cpu": {
            "percent": cpu_percent,
            "cores": cpu_count
        },
        "memory": memory_metrics,
        "disk": disk_metrics,
        "network": network_metrics,
        "process": {
            "pid": os.getpid(),
            "memory_mb": proc_mem,
            "threads": proc.num_threads()
        }
    }

