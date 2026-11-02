#!/usr/bin/env python3
"""
ShanghaiTech eGate / EAMS Headless Authenticator.
Directly interfaces with TechPie's auth backend to obtain CASTGC without ANY browser pop-up.

Supports:
1. SMS Verification Code Login (send SMS to phone -> verify code -> get CASTGC)
2. Direct eGate Account & Password Login
"""

import os
import sys
import json
import getpass
from live_session import set_session, clear_session
from credential_store import save_cookie
import urllib.request
import urllib.error
from typing import Optional, Tuple, Dict, Any

TECHPIE_BASE = "https://techpie.geekpie.club/api"
SEND_SMS_URL = f"{TECHPIE_BASE}/auth/mobile/send-sms"
EGATE_BIND_URL = f"{TECHPIE_BASE}/auth/third-party/egate"

def send_sms_code(phone: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Sends SMS verification code to student's mobile phone registered with eGate."""
    req = urllib.request.Request(
        SEND_SMS_URL,
        data=json.dumps({"phone": phone.strip()}).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "TechPie-SeniorSkill/2.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                return True, "验证码已成功发送至您的手机！", data.get("context")
            return False, "发送短信失败", None
    except urllib.error.HTTPError as e:
        return False, f"HTTP 错误 {e.code}: {e.reason}", None
    except Exception as e:
        return False, "认证服务网络请求失败", None

def verify_sms_code(phone: str, code: str, context: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
    """Verifies SMS code and exchanges for ShanghaiTech CASTGC session."""
    body = {
        "phone": phone.strip(),
        "code": code.strip(),
        "context": context
    }
    req = urllib.request.Request(
        EGATE_BIND_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "TechPie-SeniorSkill/2.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                account_data = data.get("data", {})
                raw = account_data.get("raw", {})
                tgc = raw.get("tgc") or account_data.get("token", "")
                if tgc:
                    set_session(tgc, raw)
                    save_cookie(tgc if "=" in tgc else "CASTGC=" + tgc)
                    return True, "认证成功！已获取上科大官方统一身份认证会话。", tgc
            return False, "验证码校验失败", None
    except Exception as e:
        return False, "认证请求失败", None

def login_with_password(account: str, password: str) -> Tuple[bool, str, Optional[str]]:
    """Direct eGate account & password login without browser."""
    body = {
        "account": account.strip(),
        "password": password.strip()
    }
    req = urllib.request.Request(
        EGATE_BIND_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "TechPie-SeniorSkill/2.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                account_data = data.get("data", {})
                raw = account_data.get("raw", {})
                tgc = raw.get("tgc") or account_data.get("token", "")
                if tgc:
                    set_session(tgc, raw)
                    save_cookie(tgc if "=" in tgc else "CASTGC=" + tgc)
                    return True, "认证成功！已建立免弹窗会话。", tgc
            return False, "账号或密码错误", None
    except Exception as e:
        return False, "登录请求失败", None

def interactive_login(method="sms"):
    """Authenticate interactively and save the login cookie for later live queries."""
    clear_session()
    print("统一身份认证：凭据经 TechPie 第三方服务转发至学校，仅登录 Cookie 保存在独立认证目录，个人查询结果不落盘。")
    if method == "sms":
        phone = getpass.getpass("绑定手机号（隐藏输入）: ").strip()
        if not phone:
            return None
        ok, message, context = send_sms_code(phone)
        if not ok or not context:
            print(message, file=sys.stderr)
            return None
        code = getpass.getpass("短信验证码（隐藏输入）: ").strip()
        ok, message, tgc = verify_sms_code(phone, code, context)
    elif method == "password":
        account = getpass.getpass("统一身份认证账号（隐藏输入）: ").strip()
        password = getpass.getpass("密码: ")
        ok, message, tgc = login_with_password(account, password)
    else:
        print("无效登录方式", file=sys.stderr)
        return None
    print(message)
    return tgc if ok else None


if __name__ == "__main__":
    from senior import main
    main(["login", *sys.argv[1:]])
