from __future__ import annotations

import os
import platform
import socket
import threading
import time
from dataclasses import dataclass
from datetime import datetime

import psutil


@dataclass
class NetSample:
    sent: int
    recv: int
    ts: float


class SystemMonitor:
    def __init__(self) -> None:
        io = psutil.net_io_counters()
        self._net = NetSample(io.bytes_sent, io.bytes_recv, time.monotonic())
        self._lock = threading.Lock()
        self.started_at = time.time()
        # Prime psutil CPU counters once so the first API request is meaningful.
        psutil.cpu_percent(interval=None, percpu=True)

    def snapshot(self) -> dict:
        # A short blocking sample gives a real utilization reading instead of the
        # first-call 0.0 frequently returned by interval=None.
        per_cpu = psutil.cpu_percent(interval=0.18, percpu=True)
        cpu = round(sum(per_cpu) / len(per_cpu), 1) if per_cpu else 0.0
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        now = time.monotonic()
        io = psutil.net_io_counters()

        with self._lock:
            elapsed = max(now - self._net.ts, 0.001)
            upload_bps = max(0, io.bytes_sent - self._net.sent) / elapsed
            download_bps = max(0, io.bytes_recv - self._net.recv) / elapsed
            self._net = NetSample(io.bytes_sent, io.bytes_recv, now)

        boot = datetime.fromtimestamp(psutil.boot_time()).isoformat()
        return {
            "cpu": {
                "percent": cpu,
                "physical_cores": psutil.cpu_count(logical=False) or 0,
                "logical_cores": psutil.cpu_count(logical=True) or 0,
                "per_core": [round(v, 1) for v in per_cpu],
                "frequency_mhz": round(psutil.cpu_freq().current, 0) if psutil.cpu_freq() else None,
            },
            "memory": {
                "percent": round(memory.percent, 1),
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "total_gb": round(memory.total / (1024 ** 3), 2),
            },
            "disk": {
                "percent": round(disk.percent, 1),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "total_gb": round(disk.total / (1024 ** 3), 2),
            },
            "network": {
                "upload_mbps": round(upload_bps * 8 / 1_000_000, 2),
                "download_mbps": round(download_bps * 8 / 1_000_000, 2),
                "bytes_sent": io.bytes_sent,
                "bytes_recv": io.bytes_recv,
            },
            "host": {
                "hostname": socket.gethostname(),
                "os": f"{platform.system()} {platform.release()}",
                "platform": platform.platform(),
                "boot_time": boot,
                "uptime_seconds": int(time.time() - psutil.boot_time()),
            },
        }
