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
import argparse
import urllib.request
import urllib.error
from typing import Optional, Tuple, Dict, Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
COOKIE_CACHE_PATH = os.path.join(DATA_DIR, "eams_cookie.txt")

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
            return False, data.get("error", "发送短信失败"), None
    except urllib.error.HTTPError as e:
        return False, f"HTTP 错误 {e.code}: {e.reason}", None
    except Exception as e:
        return False, f"网络请求失败: {str(e)}", None

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
                    # Save to cookie cache
                    save_tgc(tgc)
                    return True, "认证成功！已获取上科大官方统一身份认证会话。", tgc
            return False, data.get("error", "验证码校验失败"), None
    except Exception as e:
        return False, f"认证请求异常: {str(e)}", None

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
                    save_tgc(tgc)
                    return True, "认证成功！已建立免弹窗会话。", tgc
            return False, data.get("error", "账号或密码错误"), None
    except Exception as e:
        return False, f"登录失败: {str(e)}", None

def save_tgc(tgc: str):
    cookie_val = tgc if tgc.startswith("CASTGC=") else f"CASTGC={tgc}"
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(COOKIE_CACHE_PATH, "w", encoding="utf-8") as f:
        f.write(cookie_val)

def interactive_login():
    print("=" * 65)
    print("🔑 上海科技大学统一身份认证 (彻底免弹窗命令行登录)")
    print("=" * 65)
    print("1. 手机短信验证码登录 (推荐，无需输入密码，官方短信秒达)")
    print("2. 统一身份认证学号密码登录")
    choice = input("请选择登录方式 [1/2, 默认 1]: ").strip() or "1"

    if choice == "1":
        phone = input("请输入您在上科大绑定的手机号: ").strip()
        if not phone:
            print("❌ 手机号不能为空")
            return
        print(f"⏳ 正在向 {phone} 请求发送官方短信验证码...")
        ok, msg, ctx = send_sms_code(phone)
        if not ok or not ctx:
            print(f"❌ {msg}")
            return
        print(f"✅ {msg}")
        code = input("请输入收到的 6 位短信验证码: ").strip()
        print("⏳ 正在核验并换取免弹窗凭据...")
        v_ok, v_msg, tgc = verify_sms_code(phone, code, ctx)
        if v_ok:
            print(f"🎉 {v_msg}")
            print(f"📁 凭证已存入: {COOKIE_CACHE_PATH}")
            try:
                import eams_session
                print("⚡ 正在自动拉取最新的 EAMS 培养计划完成情况...")
                eams_session.fetch_plan_lightweight(cookie=tgc)
            except Exception:
                pass
            print("👉 登录成功，即将自动启动毕业学分缺口诊断！\n")
        else:
            print(f"❌ {v_msg}")
    else:
        account = input("请输入学号 / 统一身份认证账号: ").strip()
        import getpass
        password = getpass.getpass("请输入统一身份认证密码: ").strip()
        print("⏳ 正在通过官方安全通道核验登录...")
        v_ok, v_msg, tgc = login_with_password(account, password)
        if v_ok:
            print(f"🎉 {v_msg}")
            print(f"📁 凭证已存入: {COOKIE_CACHE_PATH}")
            try:
                import eams_session
                print("⚡ 正在自动拉取最新的 EAMS 培养计划完成情况...")
                eams_session.fetch_plan_lightweight(cookie=tgc)
            except Exception:
                pass
            print("👉 登录成功，即将自动启动毕业学分缺口诊断！\n")
        else:
            print(f"❌ {v_msg}")

if __name__ == "__main__":
    interactive_login()
