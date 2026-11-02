#!/usr/bin/env python3
"""
Cross-Platform Terminal Launcher for ShanghaiTech Senior Skill.
Automatically spawns a native terminal window to execute interactive commands
(e.g., login, SMS verification, audit) across macOS, Windows, and Linux.
"""

import os
import sys
import platform
import shutil
import subprocess

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))

def launch_in_terminal(command_str: str, cwd: str = PROJECT_DIR) -> bool:
    """
    Spawns an interactive native terminal window running command_str.
    Returns True if launched successfully.
    """
    sys_name = platform.system().lower()

    if sys_name == "darwin":  # macOS
        # AppleScript command
        escaped_cmd = command_str.replace('\\', '\\\\').replace('"', '\\"')
        script = f'''
        tell application "Terminal"
            activate
            do script "cd \\"{cwd}\\" && {escaped_cmd}"
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", script], check=True)
            return True
        except Exception as e:
            print(f"⚠️ macOS 唤起 Terminal.app 失败: {e}", file=sys.stderr)
            return False

    elif sys_name == "windows":
        # Windows: start cmd /k or powershell
        try:
            full_cmd = f'cd /d "{cwd}" && {command_str}'
            subprocess.Popen(f'start cmd /k "{full_cmd}"', shell=True)
            return True
        except Exception as e:
            print(f"⚠️ Windows 唤起 cmd.exe 失败: {e}", file=sys.stderr)
            return False

    else:  # Linux
        # Detect common Linux terminal emulators
        terminals = [
            ("x-terminal-emulator", lambda c: ["x-terminal-emulator", "-e", f"bash -c \"cd '{cwd}' && {c}; exec bash\""]),
            ("gnome-terminal", lambda c: ["gnome-terminal", "--", "bash", "-c", f"cd '{cwd}' && {c}; exec bash"]),
            ("konsole", lambda c: ["konsole", "-e", f"bash -c \"cd '{cwd}' && {c}; exec bash\""]),
            ("xfce4-terminal", lambda c: ["xfce4-terminal", "-e", f"bash -c \"cd '{cwd}' && {c}; exec bash\""]),
            ("xterm", lambda c: ["xterm", "-e", f"bash -c \"cd '{cwd}' && {c}; exec bash\""]),
        ]
        for term_bin, cmd_builder in terminals:
            if shutil.which(term_bin):
                try:
                    subprocess.Popen(cmd_builder(command_str))
                    return True
                except Exception:
                    continue
        print("⚠️ Linux 未检测到受支持的图形终端仿真器 (gnome-terminal/konsole/xterm)", file=sys.stderr)
        return False

def launch_login_and_audit(cwd: str = PROJECT_DIR) -> bool:
    """Convenience launcher: run login first, then automatically run audit."""
    cmd = "python3 scripts/senior.py login && python3 scripts/senior.py audit"
    return launch_in_terminal(cmd, cwd=cwd)

if __name__ == "__main__":
    cmd_to_run = sys.argv[1] if len(sys.argv) > 1 else "python3 scripts/senior.py login && python3 scripts/senior.py audit"
    print(f"🚀 正在跨平台唤起原生终端窗口执行: {cmd_to_run}")
    ok = launch_in_terminal(cmd_to_run)
    if ok:
        print("✅ 原生终端窗口已成功唤起！")
    else:
        print("❌ 原生终端唤起失败。")
