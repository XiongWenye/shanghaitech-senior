#!/usr/bin/env python3
"""Fetch official EAMS pages in memory. Only the login cookie persists; no personal snapshots."""
import argparse
import http.cookiejar
import re
import sys
import urllib.error
import urllib.request
from typing import Optional, Dict, Any
from live_session import get_cookie, require_cookie, LiveQueryError, authentication_required

EAMS_BASE_URL = "https://eams.shanghaitech.edu.cn"
MY_PLAN_URL = f"{EAMS_BASE_URL}/eams/myPlanCompl.action"
STD_DETAIL_URL = f"{EAMS_BASE_URL}/eams/stdDetail.action"


def fetch_eams_html(cookie, url=MY_PLAN_URL, timeout=20):
    raw = require_cookie(cookie)
    if "=" not in raw:
        raw = "CASTGC=" + raw
    jar = http.cookiejar.CookieJar()
    for part in raw.split(";"):
        if "=" not in part:
            continue
        name, value = part.strip().split("=", 1)
        domain = "ids.shanghaitech.edu.cn" if name == "CASTGC" else "eams.shanghaitech.edu.cn"
        jar.set_cookie(http.cookiejar.Cookie(0, name, value, None, False, domain, False,
                                            False, "/", True, True, None, True, None, None, {}))
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache, no-store", "Pragma": "no-cache"})
    try:
        with opener.open(req, timeout=timeout) as response:
            final_url = response.geturl()
            content = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        if any(x in final_url.lower() for x in ("login", "authserver")) or "统一身份认证" in content and "培养计划" not in content:
            authentication_required("EAMS 会话失效：返回登录页面")
        if "myPlanCompl" in url and ("<table" not in content.lower() or "课程代码" not in content):
            return False, "EAMS 未返回有效计划完成表格", url
        return True, content, final_url
    except urllib.error.HTTPError as error:
        if error.code == 401:
            authentication_required("EAMS 会话失效（HTTP 401）")
        return False, f"EAMS HTTP {error.code}", url
    except (OSError, ValueError):
        return False, "EAMS 网络连接失败或响应无效", url


def fetch_plan_lightweight(cookie=None):
    ok, content, _ = fetch_eams_html(require_cookie(cookie))
    if not ok:
        raise LiveQueryError(content)
    return content


def parse_student_profile(html):
    """Read actual adjacent label/value cells in either EAMS interface language."""
    from analyze_plan import SimpleTableParser
    parser = SimpleTableParser()
    parser.feed(html)
    aliases = {
        "student_id": ("学号", "Student No", "Student No.", "Student Number", "Student ID"),
        "name": ("姓名", "Name"), "grade": ("年级", "Grade"),
        "major": ("专业", "专业/专业方向", "Major"),
        "dept": ("院系", "学院", "College", "Department"),
    }
    def normalize(label):
        return re.sub(r"[\s:：]+", "", label).casefold()
    lookup = {normalize(label): key for key, labels in aliases.items() for label in labels}
    profile = {}
    for row in parser.rows:
        for index, label in enumerate(row[:-1]):
            key = lookup.get(normalize(label))
            if key:
                value = " ".join(row[index + 1].split())
                if key == "grade":
                    if re.fullmatch(r"[0-9]{4}", value):
                        profile[key] = int(value)
                elif value:
                    profile[key] = value
    return profile if profile.get("student_id") else None


def get_student_profile(cookie: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Resolve the authenticated identity from a fresh official EAMS page."""
    active_cookie = cookie or get_cookie()
    if not active_cookie:
        return None
    for url in (STD_DETAIL_URL, MY_PLAN_URL):
        ok, html, _ = fetch_eams_html(active_cookie, url)
        if ok:
            profile = parse_student_profile(html)
            if profile:
                return profile
    return None

def main():
    parser = argparse.ArgumentParser(description="实时 EAMS 会话检查，仅内存处理")
    parser.add_argument("--check", action="store_true", help="检查会话，不保存响应")
    args = parser.parse_args()
    try:
        fetch_plan_lightweight()
    except LiveQueryError as error:
        print(f"查询失败：{error}", file=sys.stderr)
        raise SystemExit(1)
    print("EAMS 实时会话有效；未保存个人数据。")


if __name__ == "__main__":
    main()
