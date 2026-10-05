from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional

ALLOWED_ACTIONS = {"shutdown", "restart", "sleep", "lock"}


@dataclass
class ScheduledTask:
    id: str
    action: str
    execute_at: float
    created_at: float
    cancelled: bool = False
    completed: bool = False

    def as_dict(self) -> dict:
        data = asdict(self)
        data["execute_at_iso"] = datetime.fromtimestamp(self.execute_at).isoformat()
        return data


class PowerScheduler:
    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTask] = {}
        self._events: dict[str, threading.Event] = {}
        self._lock = threading.RLock()

    def schedule(self, action: str, *, delay_seconds: Optional[int] = None, at_time: Optional[str] = None) -> ScheduledTask:
        if action not in ALLOWED_ACTIONS:
            raise ValueError("Unsupported action")
        execute_at = self._resolve_execute_at(delay_seconds, at_time)
        if execute_at - time.time() > 7 * 24 * 3600:
            raise ValueError("Schedule cannot exceed 7 days")
        task = ScheduledTask(str(uuid.uuid4()), action, execute_at, time.time())
        cancel_event = threading.Event()
        with self._lock:
            self._tasks[task.id] = task
            self._events[task.id] = cancel_event
        threading.Thread(target=self._worker, args=(task.id,), daemon=True, name=f"power-{task.id[:8]}").start()
        return task

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            event = self._events.get(task_id)
            if not task or task.completed or task.cancelled or not event:
                return False
            task.cancelled = True
            event.set()
            return True

    def list_tasks(self) -> list[dict]:
        with self._lock:
            return [t.as_dict() for t in sorted(self._tasks.values(), key=lambda item: item.execute_at, reverse=True)[:20]]

    def _resolve_execute_at(self, delay_seconds: Optional[int], at_time: Optional[str]) -> float:
        now = datetime.now()
        if at_time:
            target_time = datetime.strptime(at_time, "%H:%M").time()
            target = datetime.combine(now.date(), target_time)
            if target <= now:
                target += timedelta(days=1)
            return target.timestamp()
        if delay_seconds is None:
            raise ValueError("Missing delay")
        delay_seconds = int(delay_seconds)
        if delay_seconds < 1:
            raise ValueError("Delay must be at least 1 second")
        return time.time() + delay_seconds

    def _worker(self, task_id: str) -> None:
        with self._lock:
            task = self._tasks[task_id]
            event = self._events[task_id]
        wait_for = max(0, task.execute_at - time.time())
        if event.wait(wait_for):
            return
        try:
            self._execute(task.action)
            with self._lock:
                task.completed = True
        finally:
            with self._lock:
                self._events.pop(task_id, None)

    @staticmethod
    def _execute(action: str) -> None:
        if os.name != "nt":
            raise RuntimeError("Power actions are implemented for Windows only")
        commands = {
            "shutdown": ["shutdown", "/s", "/t", "0"],
            "restart": ["shutdown", "/r", "/t", "0"],
            "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
        }
        subprocess.Popen(commands[action], shell=False, close_fds=True)
