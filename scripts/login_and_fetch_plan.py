#!/usr/bin/env python3
"""
Automated EAMS Plan Completion Fetcher using Playwright with System Chrome.
1. Pops up a real Chrome window on user's screen.
2. Directs user to https://eams.shanghaitech.edu.cn/eams/myPlanCompl.action
3. Waits for user to log in via ShanghaiTech SSO.
4. Once the plan completion table is loaded, automatically extracts HTML and table data.
5. Saves to data/my_plan_completion.html and runs analyze_plan.py!
"""

import os
import sys
import time
import subprocess
import argparse

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
OUTPUT_HTML = os.path.join(DATA_DIR, "my_plan_completion.html")
OUTPUT_JSON = os.path.join(DATA_DIR, "my_plan_completion.json")

def fetch_plan_with_browser(major=None, grade=None, timeout_sec=180):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[!] Playwright not installed. Run via: uv run --with playwright python3 scripts/login_and_fetch_plan.py")
        sys.exit(1)

    url = "https://eams.shanghaitech.edu.cn/eams/myPlanCompl.action"
    print("=" * 70)
    print("🌐 正在使用系统默认 Chrome 浏览器打开 EAMS 培养计划完成情况页面...")
    print(f"👉 目标地址: {url}")
    print("=" * 70)
    print("💡 请在弹出的浏览器窗口中输入上海科技大学统一身份认证的账号与密码进行登录。")
    print("   登录成功后，系统将自动捕获您的计划完成情况与真实学籍信息，并自动关闭浏览器。")
    print("=" * 70)

    with sync_playwright() as p:
        # Launch real system Chrome window
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(viewport=None)
        page = context.new_page()

        try:
            page.goto(url, wait_until="commit", timeout=30000)
        except Exception as e:
            print(f"[*] 导航中: {e}")

        # Wait for user to login and land on myPlanCompl table
        print(f"⏳ 等待登录中（最长等待 {timeout_sec} 秒）...")
        start_time = time.time()
        captured = False

        while time.time() - start_time < timeout_sec:
            current_url = page.url
            # Check if we are on myPlanCompl and table exists
            if "myPlanCompl" in current_url:
                try:
                    # Check if table with courses is present
                    has_table = page.evaluate("""() => {
                        const tables = document.querySelectorAll('table');
                        for (let t of tables) {
                            if (t.innerText.includes('课程代码') || t.innerText.includes('课程名称')) {
                                return true;
                            }
                        }
                        return false;
                    }""")
                    if has_table:
                        print("\n🎉 检测到已进入培养计划完成情况页面，正在提取数据...")
                        # Wait 1 sec for any dynamic contents
                        page.wait_for_timeout(1000)
                        html_content = page.content()
                        
                        # Save HTML
                        with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
                            f.write(html_content)
                        print(f"✅ 已成功保存页面到: {OUTPUT_HTML}")
                        
                        captured = True
                        break
                except Exception:
                    pass
            time.sleep(1.5)

        browser.close()

    if not captured:
        print("\n❌ 等待超时或未进入培养计划完成情况页面。")
        sys.exit(1)

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
    parser = argparse.ArgumentParser(description="Fetch EAMS myPlanCompl via user login in browser")
    parser.add_argument("--major", default=None, help="Student's major (optional, auto-detected from EAMS)")
    parser.add_argument("--grade", type=int, default=None, help="Grade year (optional, auto-detected from EAMS)")
    parser.add_argument("--timeout", type=int, default=180, help="Max wait seconds for login (default: 180)")
    args = parser.parse_args()

    fetch_plan_with_browser(major=args.major, grade=args.grade, timeout_sec=args.timeout)
