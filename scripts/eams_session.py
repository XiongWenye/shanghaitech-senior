#!/usr/bin/env python3
"""
Lightweight ShanghaiTech EAMS Session Manager & HTML Plan Fetcher.
Adapted from TechPie-flutter's SessionTree & EAMS session derivation.

Enables:
- Zero-browser / pop-up-free HTTP fetching of EAMS myPlanCompl.action & stdDetail.action.
- Automatic cookie jar handling and CAS single-sign-on redirect following.
- Multi-source session cookie auto-detection (CLI flag, env var, local token cache).
- Seamless fallback to interactive browser if session is absent or expired.
"""

import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.error
import http.cookiejar
from typing import Optional, Tuple, Dict, Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
DEFAULT_HTML_PATH = os.path.join(DATA_DIR, "my_plan_completion.html")
COOKIE_CACHE_PATH = os.path.join(DATA_DIR, "eams_cookie.txt")

EAMS_BASE_URL = "https://eams.shanghaitech.edu.cn"
MY_PLAN_URL = f"{EAMS_BASE_URL}/eams/myPlanCompl.action"
STD_DETAIL_URL = f"{EAMS_BASE_URL}/eams/stdDetail.action"

def get_cached_cookie() -> Optional[str]:
    """Retrieve cookie from environment, local data file, or user home directory."""
    # 1. Environment variable
    env_cookie = os.environ.get("EAMS_COOKIE") or os.environ.get("SHANGHAITECH_CASTGC") or os.environ.get("CASTGC")
    if env_cookie and env_cookie.strip():
        return env_cookie.strip()

    # 2. Local data directory cache
    if os.path.exists(COOKIE_CACHE_PATH):
        try:
            with open(COOKIE_CACHE_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass

    # 3. User home config directory (~/.shanghaitech/session.json)
    home_session = os.path.expanduser("~/.shanghaitech/session.json")
    if os.path.exists(home_session):
        try:
            with open(home_session, "r", encoding="utf-8") as f:
                data = json.load(f)
                cookie = data.get("cookie") or data.get("tgc") or data.get("CASTGC")
                if cookie:
                    return cookie.strip()
        except Exception:
            pass

    return None

def save_cookie_cache(cookie: str):
    """Save cookie to local cache file for subsequent lightweight runs."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(COOKIE_CACHE_PATH, "w", encoding="utf-8") as f:
            f.write(cookie.strip())
    except Exception:
        pass

def fetch_eams_html(cookie: str, url: str = MY_PLAN_URL, timeout: int = 20) -> Tuple[bool, str, str]:
    """
    Fetch an EAMS page using standard urllib with CookieJar.
    Returns (success, content_or_error, redirected_url).
    """
    cookie_str = cookie.strip()
    if not ("=" in cookie_str):
        # Bare token assumed to be CASTGC
        cookie_str = f"CASTGC={cookie_str}"

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler()
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Cookie": cookie_str,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": EAMS_BASE_URL,
        }
    )

    try:
        with opener.open(req, timeout=timeout) as resp:
            final_url = resp.geturl()
            charset = resp.headers.get_content_charset() or "utf-8"
            html = resp.read().decode(charset, errors="replace")

            # Validate if we got redirected to login page
            if "login.action" in final_url or "cas/login" in final_url or "统一身份认证" in html and "培养计划" not in html:
                return False, "会话已过期或未授权 (检测到跳转至 CAS 登录页)", final_url

            if "myPlanCompl" in url and "课程代码" not in html and "培养计划" not in html:
                return False, "页面未返回有效的培养计划表格数据", final_url

            return True, html, final_url

    except urllib.error.HTTPError as e:
        return False, f"HTTP 错误 {e.code}: {e.reason}", url
    except Exception as e:
        return False, f"网络请求异常: {str(e)}", url

def fetch_plan_lightweight(cookie: Optional[str] = None, output_path: str = DEFAULT_HTML_PATH) -> bool:
    """
    Attempts lightweight HTTP fetch first. If unsuccessful or no cookie,
    returns False so caller can fall back to browser-based login.
    """
    active_cookie = cookie or get_cached_cookie()
    if not active_cookie:
        return False

    print("⚡ 正在通过轻量级 HTTP 会话直接拉取 EAMS 培养计划完成情况...")
    success, result, final_url = fetch_eams_html(active_cookie, MY_PLAN_URL)
    
    if success:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
        save_cookie_cache(active_cookie)
        print(f"🎉 成功免弹窗拉取培养计划！已保存至: {output_path}")
        return True
    else:
        print(f"⚠️ 轻量会话未能直接获取数据: {result}")
        return False

def get_student_profile(cookie: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Dynamically retrieve authenticated student's profile (student_id, name, major, grade, dept)
    via real-time EAMS network response without ANY local hardcoded mock data.
    """
    active_cookie = cookie or get_cached_cookie()
    if not active_cookie:
        return None

    ok, html, _ = fetch_eams_html(active_cookie, MY_PLAN_URL)
    if not ok:
        ok, html, _ = fetch_eams_html(active_cookie, STD_DETAIL_URL)
    if not ok:
        return None

    profile: Dict[str, Any] = {}

    m_sid = re.search(r'学号:.*?<td[^>]*class=\"content\"[^>]*>(.*?)</td>', html, re.S)
    if m_sid:
        profile["student_id"] = re.sub(r'&nbsp;|\s+', ' ', m_sid.group(1)).strip()
    else:
        m_sid2 = re.search(r'学号[：:]\s*([0-9]{8,12})', html)
        if m_sid2:
            profile["student_id"] = m_sid2.group(1).strip()

    m_name = re.search(r'姓名:.*?<td[^>]*class=\"content\"[^>]*>(.*?)</td>', html, re.S)
    if m_name:
        profile["name"] = re.sub(r'&nbsp;|\s+', ' ', m_name.group(1)).strip()

    m_grade = re.search(r'年级:.*?<td[^>]*class=\"content\"[^>]*>([0-9]{4})', html, re.S)
    if m_grade:
        profile["grade"] = int(m_grade.group(1))

    m_major = re.search(r'专业(?:/专业方向)?:.*?<td[^>]*class=\"content\"[^>]*>(.*?)</td>', html, re.S)
    if m_major:
        profile["major"] = re.sub(r'&nbsp;|\s+', ' ', m_major.group(1)).strip()

    m_dept = re.search(r'院系:.*?<td[^>]*class=\"content\"[^>]*>(.*?)</td>', html, re.S)
    if m_dept:
        profile["dept"] = re.sub(r'&nbsp;|\s+', ' ', m_dept.group(1)).strip()

    return profile if profile.get("student_id") else None

def main():
    parser = argparse.ArgumentParser(description="EAMS 轻量级免弹窗会话数据抓取工具")
    parser.add_argument("--cookie", "-c", type=str, help="EAMS 会话 Cookie (如 'JSESSIONID=...' 或 'CASTGC=...')")
    parser.add_argument("--output", "-o", type=str, default=DEFAULT_HTML_PATH, help="HTML 输出路径")
    parser.add_argument("--check", action="store_true", help="仅验证当前会话有效性")

    args = parser.parse_args()

    cookie = args.cookie or get_cached_cookie()
    if not cookie:
        print("❌ 未检测到可用的 EAMS 会话 Cookie。")
        print("💡 您可以通过以下方式提供会话凭据：")
        print("   1. 命令行参数: python3 scripts/eams_session.py --cookie 'CASTGC=...'")
        print("   2. 环境变量: export EAMS_COOKIE='CASTGC=...'")
        print("   3. 写入文件: 将 Cookie 存入 data/eams_cookie.txt")
        print("👉 或运行 `python3 scripts/login_and_fetch_plan.py` 使用浏览器一次性扫码/密码登录。")
        sys.exit(1)

    if args.check:
        print("🔍 正在探活当前 EAMS 会话...")
        ok, msg, url = fetch_eams_html(cookie, STD_DETAIL_URL)
        if ok:
            print(f"✅ 会话有效！已成功连通 EAMS 个人信息页面。")
        else:
            print(f"❌ 会话无效: {msg}")
        return

    ok = fetch_plan_lightweight(cookie=cookie, output_path=args.output)
    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
