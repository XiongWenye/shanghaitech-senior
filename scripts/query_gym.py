#!/usr/bin/env python3
"""Query live OA availability through the documented TechPie protocol.

Native court mapping follows TechPie lib/models/oa_gym.dart. Each time slot
is queried serially because the upstream OA tree picker is stateful.
"""
import argparse
import json
import sys
from datetime import date, datetime
from live_session import LiveQueryError, SHANGHAI, oa_auth, post_json, queried_at

SPORT_NAMES = {"badminton": "羽毛球", "pingpong": "乒乓球", "tennis": "网球", "pickleball": "匹克球"}
SPORT_ALIASES = {**{k: k for k in SPORT_NAMES}, **{v: k for k, v in SPORT_NAMES.items()},
                 "羽球": "badminton", "乒乓": "pingpong", "table_tennis": "pingpong"}
# Display label -> actual native booking sport and number. The cross-sport
# entries require their OWN live response, not an inference from tennis court 1.
COURTS = {
    "badminton": [(f"羽毛球{n}号场", "badminton", n) for n in range(1, 7)],
    "pingpong": [(f"乒乓球{n}号场", "pingpong", n) for n in range(1, 7)],
    "tennis": [(f"网球场{n}号", "tennis", n) for n in range(1, 4)] + [("匹克球1号场地（可打网球）", "pickleball", 1)],
    "pickleball": [("匹克球1号场地", "pickleball", 1), ("网球场1号（可打匹克球）", "tennis", 1)],
}


def sync_live_gym_data(sport_key, target_date, start_slot=1, end_slot=11):
    if sport_key not in COURTS:
        raise LiveQueryError("该运动项目尚无已核对的在线查询接口；请在学校 OA 场馆预约页面核对")
    try:
        date.fromisoformat(target_date)
    except ValueError:
        raise LiveQueryError("查询日期必须使用 YYYY-MM-DD 格式") from None
    if not 1 <= start_slot <= end_slot <= 11:
        raise LiveQueryError("时段必须满足 1 <= start <= end <= 11")
    auth = oa_auth()
    courts = COURTS[sport_key]
    native_sports = sorted({sport for _, sport, _ in courts})
    schedule = []
    for slot in range(start_slot, end_slot + 1):
        rows = post_json("/oa/gym/availability", {"auth": auth, "sports": native_sports,
                         "date": target_date, "startSlot": slot, "endSlot": slot})
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise LiveQueryError("OA 场地响应不是有效列表")
        native = {}
        for row in rows:
            if row.get("date") != target_date or row.get("timeSlot") != slot:
                raise LiveQueryError("OA 响应日期或时段与请求不符，无法报告余场")
            free = row.get("availableCourts")
            if not isinstance(free, list) or not all(type(n) is int for n in free):
                raise LiveQueryError("OA 场地列表格式无效")
            native[row.get("sport")] = set(free)
        if not all(sport in native for sport in native_sports):
            raise LiveQueryError("OA 未返回完整场地状态，不能推定全部已满或可用")
        schedule.append({"timeSlot": slot, "time": f"{10 + slot:02}:00~{11 + slot:02}:00",
                         "free": [label for label, sport, number in courts if number in native[sport]],
                         "unavailable": [label for label, sport, number in courts if number not in native[sport]]})
    return {"sport": sport_key, "name": SPORT_NAMES[sport_key], "date": target_date,
            "source": "学校 OA via TechPie /oa/gym/availability", "queried_at": queried_at(), "schedule": schedule}


def format_gym_report(data):
    lines = [f"## {data['name']}实时余场", f"日期：{data['date']} | 来源：{data['source']} | 查询时间：{data['queried_at']}",
             "| 时段 | 可预约场地 | 当前不可预约 |", "| :--- | :--- | :--- |"]
    for row in data["schedule"]:
        lines.append(f"| {row['time']} | {'、'.join(row['free']) or '无'} | {'、'.join(row['unavailable']) or '无'} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="OA 实时体育馆余场查询，不保存个人数据")
    parser.add_argument("sport", nargs="?", default="badminton")
    parser.add_argument("--date", "-d")
    parser.add_argument("--start-slot", type=int, default=1)
    parser.add_argument("--end-slot", type=int, default=11)
    parser.add_argument("--sync", action="store_true", help="兼容参数；每次均实时查询")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    sport = SPORT_ALIASES.get(args.sport.lower(), args.sport.lower())
    try:
        data = sync_live_gym_data(sport, args.date or datetime.now(SHANGHAI).date().isoformat(), args.start_slot, args.end_slot)
    except LiveQueryError as error:
        print(f"查询失败：{error}", file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else format_gym_report(data))


if __name__ == "__main__":
    main()
