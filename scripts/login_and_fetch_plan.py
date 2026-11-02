#!/usr/bin/env python3
"""
Automated EAMS Plan Completion Fetcher with Intelligent Fallback Chain:
1. First: Check if local/env CASTGC session cookie exists. If valid, fetch via lightweight HTTP in < 1s (100% headless).
2. Second: If no cookie exists, automatically launch native OS terminal (macOS/Windows/Linux) running:
   `python3 scripts/senior.py login && python3 scripts/senior.py audit`
   Eliminating the need for the user to manually open a terminal.
"""

import os
import sys
import subprocess
import argparse

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from eams_session import fetch_plan_lightweight, save_cookie_cache, get_cached_cookie
import launch_terminal

DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
OUTPUT_HTML = os.path.join(DATA_DIR, "my_plan_completion.html")

def fetch_plan_or_launch_terminal(major=None, grade=None, cookie=None):
    # 1. First Priority: Lightweight HTTP fetch if credentials exist
    if fetch_plan_lightweight(cookie=cookie, output_path=OUTPUT_HTML):
        run_analysis(major=major, grade=grade)
        return True

    # 2. Second Priority: Automatically spawn native OS terminal window
    print("=" * 70)
    print("⚠️ 未检测到已保存的 EAMS 统一身份认证凭据 (CASTGC)。")
    print("🚀 老学长正在为您自动唤起原生终端窗口执行免弹窗登录...")
    print("👉 登录成功后将自动无缝执行毕业学分缺口诊断 (python3 scripts/senior.py audit)！")
    print("=" * 70)

    launched = launch_terminal.launch_login_and_audit()
    if launched:
        print("✅ 系统终端已成功弹出！请在弹出的终端窗口中输入手机号并输入收到的 6 位短信验证码。")
        return True
    else:
        print("❌ 自动唤起系统终端失败，请手动在终端运行: python3 scripts/senior.py login")
        return False

def run_analysis(major=None, grade=None):
    print("\n" + "=" * 70)
    print("🚀 数据捕获成功！正在调用培养方案智能诊断引擎进行分析...")
    print("=" * 70 + "\n")

    cmd = [sys.executable, os.path.join(SCRIPTS_DIR, "analyze_plan.py"), "--file", OUTPUT_HTML]
    if grade:
        cmd.extend(["--grade", str(grade)])
    if major:
        cmd.extend(["--major", major])
    subprocess.run(cmd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch EAMS myPlanCompl via lightweight HTTP or auto-spawned terminal login")
    parser.add_argument("--cookie", "-c", default=None, help="EAMS Cookie (CASTGC / JSESSIONID)")
    parser.add_argument("--major", default=None, help="Student's major (optional, auto-detected from EAMS)")
    parser.add_argument("--grade", type=int, default=None, help="Grade year (optional, auto-detected from EAMS)")
    args = parser.parse_args()

    fetch_plan_or_launch_terminal(major=args.major, grade=args.grade, cookie=args.cookie)
