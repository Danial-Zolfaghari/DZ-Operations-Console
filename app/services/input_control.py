from __future__ import annotations

import threading


class InputControlService:
    """Apply mouse and keyboard input to the active Windows desktop session.

    PyAutoGUI is imported lazily so the rest of the web UI can still start and
    report a useful capability error if desktop input is unavailable.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

    @staticmethod
    def _pyautogui():
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.02
        return pyautogui

    def probe(self) -> dict:
        try:
            pyautogui = self._pyautogui()
            width, height = pyautogui.size()
            pyautogui.position()
            if width < 1 or height < 1:
                raise RuntimeError("Desktop dimensions are unavailable")
            return {
                "mouse": True,
                "keyboard": True,
                "message": "Desktop input control is available.",
            }
        except Exception as exc:
            return {
                "mouse": False,
                "keyboard": False,
                "message": (
                    "Desktop input control is unavailable in this session. "
                    "Run DZ Control inside an interactive Windows desktop session "
                    "and allow it to send mouse and keyboard input."
                ),
                "detail": str(exc)[:240],
            }

    def mouse_move(self, x: float, y: float) -> None:
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError("Invalid pointer coordinates")
        with self._lock:
            pyautogui = self._pyautogui()
            width, height = pyautogui.size()
            pyautogui.moveTo(
                round(x * (width - 1)),
                round(y * (height - 1)),
                duration=0.025,
                _pause=False,
            )

    def mouse_click(self, x: float, y: float, button_id: int) -> None:
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError("Invalid pointer coordinates")
        if button_id not in (0, 1, 2):
            raise ValueError("Invalid mouse button")
        with self._lock:
            pyautogui = self._pyautogui()
            width, height = pyautogui.size()
            button = {0: "left", 1: "middle", 2: "right"}[button_id]
            pyautogui.click(
                round(x * (width - 1)),
                round(y * (height - 1)),
                button=button,
                _pause=False,
            )

    def key_press(self, key: str, *, ctrl: bool = False, shift: bool = False, alt: bool = False) -> None:
        key = str(key or "")[:32]
        if not key:
            raise ValueError("Empty key")

        special = {
            " ": "space",
            "Enter": "enter",
            "Backspace": "backspace",
            "Delete": "delete",
            "Tab": "tab",
            "Escape": "esc",
            "ArrowUp": "up",
            "ArrowDown": "down",
            "ArrowLeft": "left",
            "ArrowRight": "right",
            "Home": "home",
            "End": "end",
            "PageUp": "pageup",
            "PageDown": "pagedown",
            "Insert": "insert",
        }
        normalized = special.get(key, key.lower())
        supported = (
            len(normalized) == 1
            or normalized in special.values()
            or (normalized.startswith("f") and normalized[1:].isdigit())
        )
        if not supported:
            raise ValueError("Unsupported key")

        modifiers = []
        if ctrl:
            modifiers.append("ctrl")
        if shift:
            modifiers.append("shift")
        if alt:
            modifiers.append("alt")

        with self._lock:
            pyautogui = self._pyautogui()
            if modifiers:
                pyautogui.hotkey(*modifiers, normalized, _pause=False)
            else:
                pyautogui.press(normalized, _pause=False)
