"""Persist only the authentication cookie, outside the skill and its data tree."""
import os
from pathlib import Path

SESSION_PATH = Path.home() / ".config" / "shanghaitech-senior" / "session.cookie"
LEGACY_COOKIE_PATH = Path(__file__).resolve().parents[1] / "data" / "eams_cookie.txt"


def load_cookie():
    try:
        value = SESSION_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        try:
            value = LEGACY_COOKIE_PATH.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None
        if value:
            save_cookie(value)
            LEGACY_COOKIE_PATH.unlink()
    return value or None


def save_cookie(cookie):
    SESSION_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    SESSION_PATH.parent.chmod(0o700)
    descriptor = os.open(SESSION_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        if os.name != "nt":
            os.fchmod(stream.fileno(), 0o600)
        stream.write(cookie.strip())


def delete_cookie():
    try:
        SESSION_PATH.unlink()
    except FileNotFoundError:
        pass
