"""Shared authentication and uncached requests for personal campus queries.

Protocol reference: HeZeBang/TechPie-flutter, lib/services/{session,
schedule_service,assignment_service,egate_app_service,oa_gym_service}.dart.
Only the login cookie may persist via credential_store; personal responses stay in memory.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from credential_store import load_cookie

TECHPIE_BASE = "https://techpie.geekpie.club/api"
SHANGHAI = timezone(timedelta(hours=8))
_cookie = None
_auth_context = {}
_login_prompt = None


class LiveQueryError(RuntimeError):
    pass


class AuthenticationRequired(LiveQueryError):
    pass


def reset_login_prompt():
    global _login_prompt
    _login_prompt = None


def request_login(reason, method="sms"):
    """Open one login terminal per CLI invocation, including aggregated queries."""
    global _login_prompt
    if _login_prompt is None:
        from launch_terminal import launch_login, login_command
        print(f"{reason}，正在打开登录终端…", file=sys.stderr)
        opened = launch_login(method=method)
        if opened:
            fields = "手机号和验证码" if method == "sms" else "账号和密码"
            message = f"登录终端已打开，请输入{fields}；登录完成后再执行所需查询。"
        else:
            message = f"自动打开终端失败；可在本机终端运行：{login_command(method)}"
        _login_prompt = (opened, message)
        print(message, file=sys.stderr)
    return _login_prompt[0]


def authentication_required(reason):
    request_login(reason)
    raise AuthenticationRequired(f"{reason}。{_login_prompt[1]}")


def _uses_campus_cookie(path):
    return path.startswith(("/schedule/", "/egate-app/", "/oa/")) or path in (
        "/auth/third-party/eams", "/auth/third-party/egate-app", "/auth/third-party/elearning", "/deadlines/blackboard")


def _expired_response(result):
    if not isinstance(result, dict):
        return False
    code = str(result.get("code") or result.get("errorCode") or "").upper()
    if code in ("401", "UNAUTHORIZED", "AUTH_EXPIRED", "SESSION_EXPIRED", "INVALID_TGC"):
        return True
    error = result.get("error")
    if not isinstance(error, str):
        return False
    # Only explicit authentication failures trigger login, never arbitrary server errors.
    return bool(re.search(r"未登录|(?:会话|登录态|登录|凭据|CASTGC|TGC|Cookie)[^。\n]{0,12}(?:过期|失效)|"
                          r"unauthorized|not authenticated|session expired|invalid (?:cookie|tgc)|tgc expired",
                          error, re.I))


def queried_at():
    return datetime.now(SHANGHAI).isoformat(timespec="seconds")


def set_session(cookie, context=None):
    global _cookie, _auth_context
    _cookie = cookie
    _auth_context = dict(context or {})


def clear_session():
    global _cookie, _auth_context
    _cookie = None
    _auth_context = {}
    reset_login_prompt()


def get_cookie(cookie=None):
    raw = cookie or _cookie or os.environ.get("EAMS_COOKIE") or os.environ.get("SHANGHAITECH_CASTGC") or os.environ.get("CASTGC") or load_cookie()
    return raw.strip() if raw and raw.strip() else None


def get_tgc(cookie=None):
    raw = get_cookie(cookie)
    if not raw:
        return None
    for part in raw.split(";"):
        if part.strip().startswith("CASTGC="):
            return part.strip().split("=", 1)[1] or None
    return raw if "=" not in raw else None


def require_cookie(cookie=None):
    value = get_cookie(cookie)
    if not value:
        authentication_required("未检测到 Cookie")
    return value


def post_json(path, payload):
    """Send one fresh request; reject failures and missing data, including HTTP 200 errors."""
    req = urllib.request.Request(
        TECHPIE_BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "TechPie-SeniorSkill/3.0",
                 "Cache-Control": "no-cache, no-store", "Pragma": "no-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 401 and _uses_campus_cookie(path):
            authentication_required(f"{path}: 学校会话已失效（HTTP 401）")
        raise LiveQueryError(f"{path}: HTTP {error.code}，认证或服务请求失败") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise LiveQueryError(f"{path}: 网络连接失败或超时") from None
    except (ValueError, UnicodeError):
        raise LiveQueryError(f"{path}: 服务返回非 JSON 响应") from None
    # Do not echo arbitrary server bodies: they can contain credentials or personal data.
    if not isinstance(result, dict) or result.get("success") is not True or "data" not in result:
        if _uses_campus_cookie(path) and _expired_response(result):
            authentication_required(f"{path}: 服务确认学校会话已失效")
        raise LiveQueryError(f"{path}: 接口未确认查询成功或缺少 data；请核对登录态及服务状态")
    return result["data"]


def derive_cookies(service, cookie=None):
    raw = require_cookie(cookie)
    tgc = get_tgc(raw)
    if not tgc:
        if service == "eams":
            return raw
        authentication_required(f"{service}: 缺少 CASTGC 凭据")
    data = post_json(f"/auth/third-party/{service}", {"tgc": tgc})
    token = data.get("token") if isinstance(data, dict) else None
    if not isinstance(token, str) or not token.strip():
        raise LiveQueryError(f"{service}: 未返回有效派生会话")
    return token


def oa_auth():
    tgc = get_tgc()
    if not tgc:
        authentication_required("OA: 缺少 CASTGC 凭据")
    return {"tgc": tgc, "cookies": _auth_context.get("cookies") or f"CASTGC={tgc}",
            **{key: _auth_context.get(key) or os.environ.get("CPDAILY_" + key.upper(), "")
               for key in ("sessionToken", "userId", "tenantId")}}
