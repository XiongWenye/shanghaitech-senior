#!/usr/bin/env python3
"""Live xshdapp attendance history; no identity or response cache."""
import argparse
import json
import sys
from live_session import LiveQueryError, derive_cookies, post_json, queried_at


def sync_activities_from_techpie(tgc=None, student_id=None):
    from eams_session import get_student_profile
    cookies = derive_cookies("egate-app", tgc)
    # Resolve identity anew rather than reading a saved plan/profile.
    if not student_id:
        profile = get_student_profile(tgc)
        student_id = profile.get("student_id") if profile else None
    if not student_id:
        raise LiveQueryError("未能从实时 EAMS 响应确认学号，无法查询 xshdapp 流水")
    data = post_json("/egate-app/history", {"studentId": student_id, "cookies": cookies})
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list) or not all(isinstance(r, dict) for r in data["rows"]):
        raise LiveQueryError("xshdapp 响应缺少有效 rows 列表，不能当作零次签到")
    activities = []
    for row in data["rows"]:
        activities.append({"wid": row.get("WID", ""), "activityName": row.get("HDMC", ""),
                           "typeDisplay": row.get("HDLX_DISPLAY", ""),
                           "statusDisplay": row.get("HDZT_DISPLAY", ""),
                           "date": row.get("SQRQ", ""), "rcqd": row.get("RCQD"), "lcqd": row.get("LCQD"),
                           "creditCounted": bool(row.get("RCQD") or row.get("LCQD")),
                           "academicYear": row.get("XN_DISPLAY", "")})
    return {"source": "xshdapp via TechPie /egate-app/history", "updated_at": queried_at(),
            "studentId": student_id, "activities": activities}


def format_activities_report(data, filter_type=None):
    activities = data["activities"]
    if filter_type:
        keywords = ["形势与政策", "形策"] if filter_type in ("形策", "形势政策", "形策讲座", "形势与政策讲座") else [filter_type]
        activities = [a for a in activities if any(k in a.get("typeDisplay", "") or k in a.get("activityName", "") for k in keywords)]
    done = sum(bool(a.get("rcqd") or a.get("lcqd")) for a in activities)
    lines = ["## xshdapp 实时活动签到记录", f"来源：{data.get('source', 'xshdapp')} | 查询时间：{data.get('updated_at', '')}",
             f"本次匹配 {len(activities)} 条记录，其中 {done} 条存在入场或离场签到时间。",
             "毕业达标次数及各类别认定要求需以当前培养方案和学校审核为准；该流水接口未提供完整毕业要求。"]
    if not activities:
        lines.append("本次接口查询成功，匹配记录为空。")
    else:
        lines.extend(["| 活动 | 类别 | 申请日期 | 系统状态 | 入场签到 | 离场签到 |", "| :--- | :--- | :--- | :--- | :--- | :--- |"])
        for activity in sorted(activities, key=lambda a: a.get("rcqd") or a.get("date") or "", reverse=True):
            values = [activity.get(k) or "未提供" for k in ("activityName", "typeDisplay", "date", "statusDisplay", "rcqd", "lcqd")]
            lines.append("| " + " | ".join(str(v).replace("|", "\\|") for v in values) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="实时查询 xshdapp 活动签到，不保存个人流水")
    parser.add_argument("category", nargs="?")
    parser.add_argument("--type", "-t", dest="filter_type")
    parser.add_argument("--sync", action="store_true", help="兼容参数；每次均实时查询")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        data = sync_activities_from_techpie()
    except LiveQueryError as error:
        print(f"查询失败：{error}。请核对认证状态或学校官方学生活动页面。", file=sys.stderr)
        raise SystemExit(1)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_activities_report(data, args.filter_type or args.category))


if __name__ == "__main__":
    main()
