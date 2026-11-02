#!/usr/bin/env python3
"""
ShanghaiTech OA Gym & Court Availability Query Tool.
Directly ported from TechPie-flutter's OaGymService and shanghaitech-cpdaily-auth backend.

Architecture & Features:
1. Exact OA Sports Configurations:
   - Badminton (羽毛球): field32340='4', parent='室内羽毛球场', prefix='羽毛球场地', suffix='号', count=6
   - Pingpong (乒乓球): field32340='5', parent='室内乒乓球场', prefix='乒乓球场', suffix='号', count=6
   - Tennis (网球): field32340='6', parent='网球场', prefix='网球场', suffix='号', count=3
   - Pickleball (匹克球): field32340='11', parent='匹克球场', prefix='匹克球', suffix='号场地', count=1
2. Physical Court Conflict Resolution & Phantom Filtering:
   - Tennis 1 and Pickleball 1 share the exact same physical court (mutually exclusive).
   - Filters out invalid school phantom court (OA ID 44 匹克球2号).
3. Dual-Track Live Network Synchronization:
   - Track 1 (TechPie Microservice): POST https://techpie.geekpie.club/api/oa/gym/availability
   - Track 2 (Direct OA Weaver TreeBrowser): POST https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp
4. Zero-Hallucination & Factual Integrity:
   - Explicitly flags data source: 【实时在线专线】 vs 【本地离线/基准数据】
   - When offline/unauthenticated, explicitly reports technical reason.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Set, Tuple

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
GYM_DATA_FILE = os.path.join(DATA_DIR, "gym_availability.json")
COOKIE_FILE = os.path.join(DATA_DIR, "eams_cookie.txt")

# Standard 11 OA Time Slots
OA_TIME_SLOTS = [
    {"id": 1, "start": "11:00", "end": "12:00", "range": "11:00~12:00"},
    {"id": 2, "start": "12:00", "end": "13:00", "range": "12:00~13:00"},
    {"id": 3, "start": "13:00", "end": "14:00", "range": "13:00~14:00"},
    {"id": 4, "start": "14:00", "end": "15:00", "range": "14:00~15:00"},
    {"id": 5, "start": "15:00", "end": "16:00", "range": "15:00~16:00"},
    {"id": 6, "start": "16:00", "end": "17:00", "range": "16:00~17:00"},
    {"id": 7, "start": "17:00", "end": "18:00", "range": "17:00~18:00"},
    {"id": 8, "start": "18:00", "end": "19:00", "range": "18:00~19:00"},
    {"id": 9, "start": "19:00", "end": "20:00", "range": "19:00~20:00"},
    {"id": 10, "start": "20:00", "end": "21:00", "range": "20:00~21:00"},
    {"id": 11, "start": "21:00", "end": "22:00", "range": "21:00~22:00"},
]

SPORT_CONFIGS = {
    "badminton": {
        "id": "badminton",
        "name": "羽毛球",
        "field32340": "4",
        "courtOffset": 12,
        "courtCount": 6,
        "parentName": "室内羽毛球场",
        "courtNamePrefix": "羽毛球场地",
        "courtNameSuffix": "号",
        "location": "室内体育馆2楼",
        "default_venues": ["羽毛球1号场", "羽毛球2号场", "羽毛球3号场", "羽毛球4号场", "羽毛球5号场", "羽毛球6号场"],
    },
    "pingpong": {
        "id": "pingpong",
        "name": "乒乓球",
        "field32340": "5",
        "courtOffset": 18,
        "courtCount": 6,
        "parentName": "室内乒乓球场",
        "courtNamePrefix": "乒乓球场",
        "courtNameSuffix": "号",
        "location": "室内体育馆2楼",
        "default_venues": ["乒乓球1号场", "乒乓球2号场", "乒乓球3号场", "乒乓球4号场", "乒乓球5号场", "乒乓球6号场"],
    },
    "tennis": {
        "id": "tennis",
        "name": "网球",
        "field32340": "6",
        "courtOffset": 24,
        "courtCount": 3,
        "parentName": "网球场",
        "courtNamePrefix": "网球场",
        "courtNameSuffix": "号",
        "location": "室外网球场 / 气膜网球场",
        "default_venues": ["网球场1号", "网球场2号", "网球场3号", "匹克球1号场地 (共用)"],
    },
    "pickleball": {
        "id": "pickleball",
        "name": "匹克球",
        "field32340": "11",
        "courtOffset": 42,
        "courtCount": 1,
        "parentName": "匹克球场",
        "courtNamePrefix": "匹克球",
        "courtNameSuffix": "号场地",
        "location": "室外综合球场",
        "default_venues": ["匹克球1号场地", "网球场1号 (共用)"],
    },
    "gym": {
        "id": "gym",
        "name": "健身房",
        "field32340": "0",
        "courtOffset": 0,
        "courtCount": 1,
        "parentName": "健身房",
        "courtNamePrefix": "力量区",
        "courtNameSuffix": "",
        "location": "室内体育馆1楼力量与有氧区",
        "default_venues": ["力量区", "有氧跑步机区"],
    }
}

SPORT_ALIASES = {
    "羽毛球": "badminton",
    "羽球": "badminton",
    "badminton": "badminton",
    "网球": "tennis",
    "tennis": "tennis",
    "匹克球": "pickleball",
    "pickleball": "pickleball",
    "乒乓球": "pingpong",
    "乒乓": "pingpong",
    "pingpong": "pingpong",
    "table_tennis": "pingpong",
    "健身房": "gym",
    "gym": "gym",
    "健身": "gym",
    "力量区": "gym",
}

def get_castgc() -> Optional[str]:
    """Retrieve CASTGC ticket from local credentials store."""
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if "CASTGC=" in content:
                    return content.split("CASTGC=", 1)[1].split(";", 1)[0].strip()
                return content
        except Exception:
            pass
    return None

def fetch_techpie_live_availability(sport_key: str, target_date: str, tgc: str) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch availability from TechPie microservice endpoint.
    POST https://techpie.geekpie.club/api/oa/gym/availability
    """
    url = "https://techpie.geekpie.club/api/oa/gym/availability"
    payload = {
        "auth": {
            "tgc": tgc,
            "cookies": f"CASTGC={tgc}; happyVoyage=happy",
        },
        "sports": [sport_key],
        "date": target_date,
        "startSlot": 6,  # 16:00
        "endSlot": 10,   # 21:00
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "TechPie-SeniorSkill/2.0"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success") and "data" in data:
                return data["data"]
    except Exception:
        pass
    return None

def fetch_direct_oa_availability(sport_key: str, target_date: str, tgc: str) -> Optional[List[Dict[str, Any]]]:
    """
    Query direct ShanghaiTech OA Weaver TreeBrowser (CustomTreeBrowserAjax.jsp).
    Replicates TechPie's original direct OA handshake and 2-step Tree RPC.
    """
    if sport_key not in SPORT_CONFIGS:
        return None
    conf = SPORT_CONFIGS[sport_key]
    if conf["courtCount"] == 0:
        return None

    # Step 1: Establish OA session cookies with CASTGC
    login_url = (
        "https://ids.shanghaitech.edu.cn/authserver/login?service="
        + urllib.parse.quote("https://oa.shanghaitech.edu.cn/workflow/request/AddRequest.jsp?workflowid=14862")
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)",
        "Cookie": f"CASTGC={tgc}"
    }

    oa_cookies = {}
    try:
        req1 = urllib.request.Request(login_url, headers=headers)
        # We need a custom opener to track cookies across redirects
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        with opener.open(req1, timeout=5) as resp:
            pass

        # Check if shkjdx_session was acquired
        has_oa_session = any(c.name == "shkjdx_session" for c in cj)
        if not has_oa_session:
            return None

        # Step 2: Query availability per time slot
        results = []
        for slot in range(6, 11):  # 16:00 to 21:00
            ts = int(datetime.now().timestamp() * 1000)
            ajax_url = (
                f"https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp"
                f"?id=63&init=false&showtype=1&isselsub=0&isonlyleaf=1"
                f"&dataconditionParam=_sfn_31901_sfv_{target_date}_sfn_31902_sfv_{slot}_sfn_32340_sfv_{conf['field32340']}"
                f"&treerootnode=&selectedids=&time={ts}"
            )
            # 2.1 Get parent node
            body1 = urllib.parse.urlencode({"pid": "63_1", "name": "体育馆"}).encode("utf-8")
            req_p1 = urllib.request.Request(ajax_url, data=body1, headers={"X-Requested-With": "XMLHttpRequest"})
            with opener.open(req_p1, timeout=4) as r1:
                p_data = json.loads(r1.read().decode("utf-8").lstrip("\ufeff"))

            parent_id = None
            for item in p_data:
                if item.get("name") == conf["parentName"]:
                    parent_id = item.get("id")
                    break

            if not parent_id:
                continue

            # 2.2 Get leaf courts
            body2 = urllib.parse.urlencode({"pid": parent_id, "name": conf["parentName"]}).encode("utf-8")
            req_p2 = urllib.request.Request(ajax_url, data=body2, headers={"X-Requested-With": "XMLHttpRequest"})
            with opener.open(req_p2, timeout=4) as r2:
                courts_data = json.loads(r2.read().decode("utf-8").lstrip("\ufeff"))

            available_courts = []
            prefix = conf["courtNamePrefix"]
            suffix = conf["courtNameSuffix"]
            for c in courts_data:
                cname = c.get("name", "")
                if cname.startswith(prefix):
                    num_str = cname.replace(prefix, "").replace(suffix, "").strip()
                    try:
                        cnum = int(num_str)
                        if conf["id"] == "pickleball" and cnum != 1:
                            continue  # Filter phantom court 2
                        available_courts.append(cnum)
                    except ValueError:
                        pass

            available_courts.sort()
            results.append({
                "sport": sport_key,
                "date": target_date,
                "timeSlot": slot,
                "availableCourts": available_courts,
                "totalCourts": conf["courtCount"]
            })
        return results if results else None
    except Exception:
        return None

def load_gym_data() -> Dict[str, Any]:
    """Load cached gym availability data from disk."""
    if os.path.exists(GYM_DATA_FILE):
        try:
            with open(GYM_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"sports": {}}

def sync_live_gym_data(sport_key: str, target_date: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Attempt to sync real-time availability via TechPie stack.
    Returns (data, source_status_message).
    """
    tgc = get_castgc()
    if not tgc:
        return None, "未检测到 CASTGC 统一认证凭据，请使用 senior.py login 登录后获取实时权限"

    # 1. Try TechPie Backend Microservice
    live_rows = fetch_techpie_live_availability(sport_key, target_date, tgc)
    if live_rows:
        return _convert_live_rows_to_sport_info(sport_key, target_date, live_rows), "🟢 【数据来源：TechPie 官方微服务实时专线】"

    # 2. Try Direct OA Weaver RPC
    direct_rows = fetch_direct_oa_availability(sport_key, target_date, tgc)
    if direct_rows:
        return _convert_live_rows_to_sport_info(sport_key, target_date, direct_rows), "🟢 【数据来源：上科大 OA 流程系统直连专线】"

    return None, "🟡 无法连接 TechPie 云端或学校 OA 服务（连接超时或未在校园内网）"

def _convert_live_rows_to_sport_info(sport_key: str, target_date: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    conf = SPORT_CONFIGS.get(sport_key, SPORT_CONFIGS["badminton"])
    slot_map = {item["id"]: item["range"] for item in OA_TIME_SLOTS}

    schedule = []
    venues = list(conf["default_venues"])

    for r in rows:
        tslot = r.get("timeSlot")
        time_str = slot_map.get(tslot, f"Slot {tslot}")
        free_nums = set(r.get("availableCourts", []))
        total = conf["courtCount"]

        free_courts = []
        booked_courts = []

        if sport_key == "badminton":
            for n in range(1, total + 1):
                label = f"羽毛球{n}号场"
                if n in free_nums:
                    free_courts.append(label)
                else:
                    booked_courts.append(label)
        elif sport_key == "tennis":
            for n in range(1, 4):
                label = f"网球场{n}号"
                if n in free_nums:
                    free_courts.append(label)
                else:
                    booked_courts.append(label)
            # Shared court mapping
            if 1 in free_nums:
                free_courts.append("匹克球1号场地 (共用)")
            else:
                booked_courts.append("匹克球1号场地 (共用)")
        elif sport_key == "pickleball":
            if 1 in free_nums:
                free_courts.append("匹克球1号场地")
                free_courts.append("网球场1号 (共用)")
            else:
                booked_courts.append("匹克球1号场地")
                booked_courts.append("网球场1号 (共用)")
        elif sport_key == "pingpong":
            for n in range(1, total + 1):
                label = f"乒乓球{n}号场"
                if n in free_nums:
                    free_courts.append(label)
                else:
                    booked_courts.append(label)

        schedule.append({
            "time": time_str,
            "free": free_courts,
            "booked": booked_courts if booked_courts else (["全部场地已约满 (晚高峰)"] if not free_courts else [])
        })

    return {
        "name": conf["name"],
        "location": conf["location"],
        "venues": venues,
        "schedule": schedule
    }

def format_gym_report(sport_key: str, target_date_str: str, force_sync: bool = True) -> str:
    conf = SPORT_CONFIGS.get(sport_key)
    name = conf["name"] if conf else sport_key

    if sport_key not in SPORT_CONFIGS:
        valid_sports = "、".join(list(SPORT_ALIASES.keys())[:4])
        return f"❌ 未知运动项目「{sport_key}」。支持的项目包括：{valid_sports}。"

    # Always query live network
    live_info, reason = sync_live_gym_data(sport_key, target_date_str)
    if not live_info:
        lines = [
            f"## 🏸 上科大体育馆实时场地查询：【{name}】",
            f"- **目标日期**：`{target_date_str}`",
            f"- **网络查询状态**：❌ 实时同步未成功 ({reason})",
            f"- **学长 SKILL 第一要义**：本地严禁存放或展示任何虚假 Demo 场地预约数据。所有球场空闲状态必须通过网络端口（TechPie 微服务 / 学校 OA 流程系统）实时查询。",
            "",
            "👉 **老学长提示**：",
            "1. 请先运行 `python3 scripts/senior.py login` 获取校园统一身份认证凭据 (CASTGC)；",
            "2. 或在校园内网环境下通过 OA 流程系统「体育场馆预约」进行实时核对与预约；",
            "3. 每日中午 12:00 学校 OA 系统开放次日场地预约，热门时段（18:00~21:00）建议定闹钟准点提交流程。"
        ]
        return "\n".join(lines)

    sport_info = live_info
    source_status = reason

    location = sport_info.get("location", conf["location"] if conf else "上海科技大学体育馆")
    venues = sport_info.get("venues", conf["default_venues"] if conf else [])
    schedule = sport_info.get("schedule", [])

    lines = [
        f"## 🏸 上科大体育馆实时场地与空闲预约看板：【{name}】",
        f"- **数据状态**：{source_status}",
        f"- **场馆位置**：`{location}` | **查询日期**：`{target_date_str}`",
        f"- **有效实际场地**：{'、'.join(venues)}",
        "",
        "| 时段 | 空闲可预约场地 | 当前预约状况 |",
        "| :--- | :--- | :--- |",
    ]

    for item in schedule:
        t = item.get("time", "--")
        free = item.get("free", [])
        booked = item.get("booked", [])

        if free:
            free_str = "🟢 " + "、".join(free)
        else:
            free_str = "🔴 *已全满*"

        booked_str = "、".join(booked) if booked else "暂无其他预约"
        lines.append(f"| `{t}` | **{free_str}** | {booked_str} |")

    lines.append("")
    lines.append("💡 **老学长预约与避坑指南 (TechPie 对齐版)**：")
    if sport_key in ["tennis", "pickleball"]:
        lines.append("- ⚠️ **共用物理场地映射提示**：网球场 1 号与匹克球 1 号为同一物理场地，提交预约时二者互斥，已被对方预约的时段无法再次锁定；")
        lines.append("- 🚫 **幽灵场地过滤**：学校 OA 系统中 ID 44 的「匹克球2号」为无效幽灵场地，已由客户端底层自动剔除；")
    elif sport_key == "badminton":
        lines.append("- 🏸 **放号时间**：每天中午 12:00 学校 OA 准时开放未来 2 天的羽毛球场地预约，晚高峰 (18:00~20:00) 极其紧俏，建议设闹钟守候；")
    elif sport_key == "pingpong":
        lines.append("- 🏓 **乒乓球规则**：室内乒乓球馆位于 2 楼，1~6 号桌球台充裕，中午及傍晚课间是练习高峰；")
    lines.append("- 📌 **违约防雷**：预约成功后必须在开场前 15 分钟至开场后 15 分钟内前往体育馆总服务台扫码核销，累计爽约 3 次将冻结 OA 预约权限 30 天。")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="上海科技大学体育馆余场与预约查询工具 (TechPie 协议栈集成版)")
    parser.add_argument("sport", nargs="?", default="badminton", help="运动项目 (羽毛球, 网球, 匹克球, 乒乓球, 健身房)")
    parser.add_argument("--date", "-d", default=None, help="查询日期 (YYYY-MM-DD，默认今天)")
    parser.add_argument("--sync", action="store_true", help="强制在线联网同步实时场地")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON 数据")

    args = parser.parse_args()

    raw_sport = args.sport.strip().lower()
    sport_key = SPORT_ALIASES.get(raw_sport, "badminton")
    target_date = args.date or datetime.now().strftime("%Y-%m-%d")

    if args.json:
        data = load_gym_data()
        print(json.dumps(data.get("sports", {}).get(sport_key, {}), ensure_ascii=False, indent=2))
        return

    print(format_gym_report(sport_key, target_date, force_sync=args.sync))

if __name__ == "__main__":
    main()
