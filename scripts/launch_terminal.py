#!/usr/bin/env python3
"""Open a native terminal with the authentication command already entered."""
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent


def login_command(method="sms"):
    argv = [sys.executable, str(SCRIPTS_DIR / "senior.py"), "login", "--method", method]
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def launch_in_terminal(command_str, cwd=PROJECT_DIR):
    system = platform.system().lower()
    try:
        if system == "darwin":
            command = f"cd {shlex.quote(str(cwd))} && {command_str}"
            # LaunchServices opens a prefilled terminal without Apple Events permission.
            # This temporary helper contains code only, and deletes itself before login.
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="shanghaitech-login-",
                                             suffix=".command", delete=False) as stream:
                script_path = Path(stream.name)
                stream.write('#!/bin/bash\nrm -f -- "$0"\n' + command + '\n')
            script_path.chmod(0o700)
            try:
                subprocess.run(["open", "-a", "Terminal", str(script_path)], check=True,
                               capture_output=True, text=True, timeout=15)
            except (OSError, subprocess.SubprocessError):
                script_path.unlink(missing_ok=True)
                raise
            return True
        if system == "windows":
            # startfile uses the Windows shell to create an interactive cmd window.
            subprocess.Popen(["cmd.exe", "/k", command_str], cwd=str(cwd),
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
            return True
        command = f"cd {shlex.quote(str(cwd))} && {command_str}; exec bash"
        for binary in ("x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal", "xterm"):
            if not shutil.which(binary):
                continue
            if binary == "gnome-terminal":
                argv = [binary, "--", "bash", "-c", command]
            elif binary == "xfce4-terminal":
                argv = [binary, "--command", shlex.join(["bash", "-c", command])]
            else:
                argv = [binary, "-e", "bash", "-c", command]
            subprocess.Popen(argv)
            return True
    except (OSError, subprocess.SubprocessError):
        return False
    return False


def launch_login(cwd=PROJECT_DIR, method="sms"):
    """The new terminal runs only login; no subsequent personal query."""
    return launch_in_terminal(login_command(method), cwd=cwd)


if __name__ == "__main__":
    launched = launch_login()
    print("登录终端已打开，请填写手机号和验证码。" if launched else "无法打开登录终端。", file=sys.stderr)
    raise SystemExit(0 if launched else 1)
