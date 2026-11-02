#!/usr/bin/env python3
"""
Unit tests for TechPie-integrated campus service tools in senior-skill.
"""

import os
import sys
import unittest
import json
from datetime import date, datetime

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import campus_locations
import export_schedule_ics
import query_elrc
import eams_session
import query_exams
import query_deadlines
import query_gym
import query_activities
import sync_my_plan
import analyze_plan

class TestCampusLocations(unittest.TestCase):
    def test_find_location_keywords(self):
        sist = campus_locations.find_location("信息学院1A-200")
        self.assertIsNotNone(sist)
        self.assertEqual(sist.keyword, "信息学院")
        self.assertAlmostEqual(sist.latitude, 31.18043, places=4)

        sem = campus_locations.find_location("创管学院大楼")
        self.assertIsNotNone(sem)
        self.assertEqual(sem.keyword, "创管学院")

        jc = campus_locations.find_location("公共教学中心204")
        self.assertIsNotNone(jc)
        self.assertEqual(jc.keyword, "教学中心")

    def test_find_location_aliases(self):
        loc = campus_locations.find_location("SIST 1B-101")
        self.assertIsNotNone(loc)
        self.assertEqual(loc.keyword, "信息学院")

        gym = campus_locations.find_location("网球场2号")
        self.assertIsNotNone(gym)
        self.assertEqual(gym.keyword, "体育馆")

    def test_format_apple_structured_location(self):
        loc = campus_locations.find_location("信息学院")
        apple_geo = campus_locations.format_apple_structured_location(loc)
        self.assertIn("X-APPLE-STRUCTURED-LOCATION", apple_geo)
        self.assertIn("31.18043,121.5907", apple_geo)
        self.assertIn("中科路1号", apple_geo)

class TestExportScheduleIcs(unittest.TestCase):
    def test_build_ics_calendar(self):
        courses = [
            {
                "name": "计算机编程 (CS100)",
                "classroom": "信息学院1A-200",
                "teachers": "周平强",
                "weeks": "01100000000000000000",
                "times": {"1": [1, 2]}
            }
        ]
        term_begin = date(2026, 9, 7)  # Monday
        ics_text = export_schedule_ics.build_ics_calendar(
            courses=courses,
            term_begin=term_begin,
            calendar_name="测试课表"
        )
        self.assertIn("BEGIN:VCALENDAR", ics_text)
        self.assertIn("X-WR-CALNAME:测试课表", ics_text)
        self.assertIn("SUMMARY:计算机编程 (CS100)", ics_text)
        self.assertIn("GEO:31.18043;121.5907", ics_text)
        self.assertIn("END:VCALENDAR", ics_text)

class TestQueryElrc(unittest.TestCase):
    def test_search_elrc_courses(self):
        results = query_elrc.search_elrc_courses("CS100")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["courseNo"], "CS100")

    def test_search_synonyms(self):
        results = query_elrc.search_elrc_courses("高数")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["courseNo"], "GEMA1001")

        results_sys = query_elrc.search_elrc_courses("计系")
        self.assertTrue(len(results_sys) > 0)
        self.assertEqual(results_sys[0]["courseNo"], "CS110")

    def test_format_elrc_report(self):
        results = query_elrc.search_elrc_courses("CS110")
        report = query_elrc.format_elrc_report(results[0])
        self.assertIn("ELRC 官方课堂录播", report)
        self.assertIn("计算机系统基础 (CS110)", report)
        self.assertIn("https://elrc.shanghaitech.edu.cn", report)

class TestQueryExams(unittest.TestCase):
    def test_format_exams_report(self):
        data = {
            "examBatchName": "2025-2026学年春季学期期末考试",
            "exams": [
                {
                    "courseCode": "CS130.01",
                    "courseName": "操作系统I",
                    "examType": "期末考试",
                    "examDate": "2026-06-22",
                    "examTimeRange": "09:00~11:00",
                    "examPlace": "信息学院1A-200",
                    "examStatus": "正常",
                    "seat": "第 03 列 05 号"
                }
            ]
        }
        report = query_exams.format_exams_report(data)
        self.assertIn("操作系统I", report)
        self.assertIn("第 03 列 05 号", report)
        self.assertIn("📍 信息学院1A-200", report)

class TestQueryDeadlines(unittest.TestCase):
    def test_urgency_badge(self):
        now = datetime(2026, 11, 2, 12, 0, 0)
        due_overdue = datetime(2026, 11, 1, 12, 0, 0)
        due_soon = datetime(2026, 11, 2, 18, 0, 0)
        due_later = datetime(2026, 11, 10, 12, 0, 0)

        self.assertIn("已提交", query_deadlines.get_urgency_badge(due_overdue, now, True))
        self.assertIn("已逾期", query_deadlines.get_urgency_badge(due_overdue, now, False))
        self.assertIn("仅剩", query_deadlines.get_urgency_badge(due_soon, now, False))
        self.assertIn("天后", query_deadlines.get_urgency_badge(due_later, now, False))

    def test_format_deadlines_report(self):
        data = {
            "assignments": [
                {
                    "id": "bb-1",
                    "platform": "blackboard",
                    "title": "Lab 1",
                    "course": "CS100",
                    "due": "2026-11-05T20:00:00",
                    "status": "Pending"
                }
            ]
        }
        report = query_deadlines.format_deadlines_report(data)
        self.assertIn("Lab 1", report)
        self.assertIn("Blackboard", report)

    def test_format_deadlines_report_with_sync_status(self):
        data = {
            "assignments": []
        }
        sync_status = {
            "blackboard": (True, "在线同步成功（实时待办：0 项）"),
            "exam": (True, "在线核查考务成功（期中考试批次：0 门排考）"),
            "gradescope": (False, "未配置 Gradescope 独立 Token"),
            "hydro": (False, "未配置 Hydro OJ 独立 Token"),
        }
        report = query_deadlines.format_deadlines_report(data, sync_status=sync_status)
        self.assertIn("跨平台真实联网查询状态", report)
        self.assertIn("Blackboard", report)
        self.assertIn("EAMS 考试", report)
        self.assertIn("暂无待处理作业", report)

class TestQueryGym(unittest.TestCase):
    def test_unauthenticated_refuses_demo(self):
        report = query_gym.format_gym_report("tennis", "2026-11-02")
        self.assertIn("网球", report)
        self.assertIn("学长 SKILL 第一要义", report)
        self.assertIn("严禁存放或展示任何虚假 Demo 场地预约数据", report)
        self.assertIn("senior.py login", report)

    def test_convert_live_rows_to_sport_info(self):
        rows = [
            {"timeSlot": 6, "availableCourts": [1, 2]}
        ]
        info = query_gym._convert_live_rows_to_sport_info("tennis", "2026-11-02", rows)
        self.assertEqual(info["name"], "网球")
        self.assertTrue(len(info["schedule"]) > 0)
        self.assertIn("网球场1号", info["schedule"][0]["free"])
        self.assertIn("网球场2号", info["schedule"][0]["free"])
        self.assertIn("网球场3号", info["schedule"][0]["booked"])
        self.assertIn("匹克球1号场地 (共用)", info["schedule"][0]["free"])

class TestQueryActivities(unittest.TestCase):
    def test_format_activities_report(self):
        data = {
            "studentId": "2023533001",
            "requiredLectures": 8,
            "activities": [
                {
                    "activityName": "讲座一",
                    "typeDisplay": "科技讲座",
                    "statusDisplay": "已打卡",
                    "creditCounted": True
                }
            ]
        }
        report = query_activities.format_activities_report(data)
        self.assertIn("本科毕业讲座达标进度", report)
        self.assertIn("1 / 8", report)
        self.assertIn("尚缺 **7** 次", report)

    def test_filter_activities_xingce(self):
        data = {
            "studentId": "2023533001",
            "requiredLectures": 8,
            "activities": [
                {
                    "activityName": "前沿科技讲座",
                    "typeDisplay": "科技讲座",
                    "statusDisplay": "已打卡",
                    "creditCounted": True
                },
                {
                    "activityName": "形势与政策大讲堂",
                    "typeDisplay": "形势与政策",
                    "statusDisplay": "已打卡",
                    "creditCounted": True
                }
            ]
        }
        report = query_activities.format_activities_report(data, filter_type="形策")
        self.assertIn("形势与政策 (形策讲座)", report)
        self.assertIn("形势与政策大讲堂", report)
        self.assertNotIn("前沿科技讲座", report)
        self.assertIn("累计已核销打卡**：**1**", report)

    def test_empty_activities_refuses_fabrication(self):
        data = {"activities": []}
        report = query_activities.format_activities_report(data)
        self.assertIn("打条记录查询未果" if "打条" in report else "打卡记录查询未果", report)
        self.assertIn("事实诚信铁律", report)
        self.assertIn("TechPie App", report)

class TestSyncMyPlanAndAudit(unittest.TestCase):
    def test_extract_course_code(self):
        code1 = sync_my_plan.extract_course_code("Introduction to World Civilizations(GEHA1003.01)")
        self.assertEqual(code1, "GEHA1003")

        code2 = sync_my_plan.extract_course_code("Introduction to Current Life Science (Class C)(BIO1011.02)")
        self.assertEqual(code2, "BIO1011")

        code3 = sync_my_plan.extract_course_code("CS100", "CS100.01")
        self.assertEqual(code3, "CS100")

    def test_parse_json_plan_completion(self):
        sample_json = json.dumps({
            "student_id": "2023533999",
            "major": "计算机",
            "grade": 2023,
            "completed": [{"code": "CS100", "name": "计算机编程", "credit": 4.0}],
            "in_progress": [{"code": "CS110", "name": "计算机系统基础", "credit": 4.0}]
        })
        comp, in_prog, header = analyze_plan.parse_text_or_json_plan(sample_json)
        self.assertIn("CS100", comp)
        self.assertIn("CS110", in_prog)
        self.assertEqual(header.get("grade"), 2023)
        self.assertEqual(header.get("major"), "计算机")

if __name__ == "__main__":
    unittest.main()
