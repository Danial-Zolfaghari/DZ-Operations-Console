from __future__ import annotations

import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable

from flask import abort, redirect, request, session, url_for


class SlidingWindowLimiter:
    """Small in-memory request limiter for a single-process deployment."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            q = self._events[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


@dataclass
class _FailureState:
    failures: deque[float] = field(default_factory=deque)
    lock_until: float = 0.0
    lock_level: int = 0
    last_seen: float = 0.0


class LoginBruteForceGuard:
    """Progressive login lockout keyed by both IP and IP+username.

    After `max_failures` failures within the failure window, a lock is applied.
    Each subsequent lock doubles in duration up to `max_lock_seconds`.
    A successful login clears the related state.
    """

    def __init__(self) -> None:
        self._states: dict[str, _FailureState] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _prune(state: _FailureState, now: float, window_seconds: int) -> None:
        cutoff = now - window_seconds
        while state.failures and state.failures[0] < cutoff:
            state.failures.popleft()

    def retry_after(self, keys: tuple[str, ...], window_seconds: int) -> int:
        now = time.monotonic()
        longest = 0.0
        with self._lock:
            for key in keys:
                state = self._states.get(key)
                if not state:
                    continue
                self._prune(state, now, window_seconds)
                state.last_seen = now
                if state.lock_until > now:
                    longest = max(longest, state.lock_until - now)
        return max(0, int(longest + 0.999))

    def record_failure(
        self,
        keys: tuple[str, ...],
        *,
        max_failures: int,
        window_seconds: int,
        base_lock_seconds: int,
        max_lock_seconds: int,
    ) -> int:
        now = time.monotonic()
        longest = 0.0
        with self._lock:
            for key in keys:
                state = self._states.setdefault(key, _FailureState())
                self._prune(state, now, window_seconds)
                state.failures.append(now)
                state.last_seen = now

                if len(state.failures) >= max_failures:
                    state.lock_level += 1
                    duration = min(
                        max_lock_seconds,
                        base_lock_seconds * (2 ** max(0, state.lock_level - 1)),
                    )
                    state.lock_until = max(state.lock_until, now + duration)
                    state.failures.clear()
                    longest = max(longest, duration)

            self._cleanup_locked(now, window_seconds, max_lock_seconds)
        return int(longest)

    def reset(self, keys: tuple[str, ...]) -> None:
        with self._lock:
            for key in keys:
                self._states.pop(key, None)

    def _cleanup_locked(self, now: float, window_seconds: int, max_lock_seconds: int) -> None:
        stale_after = max(window_seconds * 3, max_lock_seconds * 2, 1800)
        stale = [
            key for key, state in self._states.items()
            if state.lock_until <= now and now - state.last_seen > stale_after
        ]
        for key in stale:
            self._states.pop(key, None)


login_request_limiter = SlidingWindowLimiter()
login_bruteforce_guard = LoginBruteForceGuard()
control_request_limiter = SlidingWindowLimiter()


def client_ip() -> str:
    """Return the direct peer IP.

    Do not trust X-Forwarded-For by default. If this app is later put behind a
    trusted reverse proxy, configure ProxyFix explicitly at deployment time.
    """
    return request.remote_addr or "unknown"


def login_required(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def api_login_required(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            abort(401)
        return view(*args, **kwargs)
    return wrapped


def get_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validate_csrf() -> None:
    expected = session.get("csrf_token", "")
    supplied = request.headers.get("X-CSRF-Token", "") or request.form.get("csrf_token", "")
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        abort(403, description="CSRF validation failed")
