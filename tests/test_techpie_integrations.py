#!/usr/bin/env python3
"""Isolated protocol/behavior tests; synthetic responses never become runtime data."""
import contextlib
import io
import json
import os
import runpy
import shlex
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error
from datetime import date, datetime
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_plan
import campus_locations
import credential_store
import eams_auth
import eams_session
import export_schedule_ics
import live_session
import launch_terminal
import query_activities
import query_deadlines
import query_exams
import query_gym
import senior
import sync_my_plan


class IsolatedTest(unittest.TestCase):
    def setUp(self):
        live_session.clear_session()
        self.addCleanup(live_session.clear_session)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.original_launch_login = launch_terminal.launch_login
        self.login_launcher = patch.object(launch_terminal, "launch_login", return_value=True)
        self.launch_mock = self.login_launcher.start()
        self.addCleanup(self.login_launcher.stop)
        self.tty = patch("sys.stdin.isatty", return_value=True)
        self.tty.start()
        self.addCleanup(self.tty.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = patch.object(credential_store, "SESSION_PATH", Path(self.temp.name) / "auth" / "session.cookie")
        self.store.start()
        self.addCleanup(self.store.stop)
        self.legacy = patch.object(credential_store, "LEGACY_COOKIE_PATH", Path(self.temp.name) / "legacy-cookie.txt")
        self.legacy.start()
        self.addCleanup(self.legacy.stop)
        self.opener = patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("unexpected direct network"))
        self.opener.start()
        self.addCleanup(self.opener.stop)
        # Any accidental real network request in a unit test is a failure.
        self.net = patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network"))
        self.net_mock = self.net.start()
        self.addCleanup(self.net.stop)

    def run_cli(self, argv):
        output, error = io.StringIO(), io.StringIO()
        code = 0
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            try:
                senior.main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, output.getvalue(), error.getvalue()


class TestCredentials(IsolatedTest):
    def test_legacy_cookie_is_migrated_without_reauthentication(self):
        credential_store.LEGACY_COOKIE_PATH.write_text("CASTGC=test-ticket")
        self.assertEqual(live_session.get_tgc(), "test-ticket")
        self.assertTrue(credential_store.SESSION_PATH.exists())
        self.assertFalse(credential_store.LEGACY_COOKIE_PATH.exists())

    def test_cookie_persists_and_environment_overrides(self):
        credential_store.save_cookie("CASTGC=test-ticket")
        self.assertEqual(live_session.get_tgc(), "test-ticket")
        if os.name != "nt":
            self.assertEqual(credential_store.SESSION_PATH.stat().st_mode & 0o777, 0o600)
            self.assertEqual(credential_store.SESSION_PATH.parent.stat().st_mode & 0o777, 0o700)
        with patch.dict(os.environ, {"CASTGC": "override"}):
            self.assertEqual(live_session.get_tgc(), "override")
        live_session.clear_session()
        self.assertEqual(live_session.get_tgc(), "test-ticket")
        credential_store.delete_cookie()
        self.assertIsNone(live_session.get_cookie())

    def test_eams_cookie_is_not_misused_as_castgc(self):
        self.assertIsNone(live_session.get_tgc("JSESSIONID=test"))
        self.assertEqual(live_session.get_tgc("JSESSIONID=x; CASTGC=ticket"), "ticket")

    def test_login_saves_only_cookie(self):
        response = contextlib.nullcontext(io.BytesIO(json.dumps({"success": True, "data": {
            "token": "test-ticket", "raw": {"tgc": "test-ticket", "name": "TEST_PRIVATE", "userId": "TEST_PRIVATE"}}}).encode()))
        with patch("urllib.request.urlopen", return_value=response):
            ok, _, _ = eams_auth.login_with_password("TEST_ACCOUNT", "TEST_PASSWORD")
        self.assertTrue(ok)
        self.assertEqual(credential_store.SESSION_PATH.read_text(), "CASTGC=test-ticket")
        self.assertEqual(len(list(Path(self.temp.name).rglob("*.*"))), 1)

    def test_login_failure_exits_nonzero(self):
        with patch.object(eams_auth, "interactive_login", return_value=None):
            code, _, _ = self.run_cli(["login"])
        self.assertEqual(code, 1)

    def test_login_only_authenticates_and_saves_cookie(self):
        responses = [
            contextlib.nullcontext(io.BytesIO(b'{"success":true,"context":{"test":"context"}}')),
            contextlib.nullcontext(io.BytesIO(b'{"success":true,"data":{"raw":{"tgc":"test-ticket"}}}')),
        ]
        with patch("builtins.input", return_value="1"), \
             patch.object(eams_auth.getpass, "getpass", side_effect=["00000000000", "000000"]), \
             patch("urllib.request.urlopen", side_effect=responses) as requests, \
             patch.object(eams_session, "fetch_plan_lightweight") as fetch, \
             patch.object(sync_my_plan, "sync_and_audit") as audit:
            code, _, _ = self.run_cli(["login"])
        self.assertEqual(code, 0)
        self.assertEqual(credential_store.load_cookie(), "CASTGC=test-ticket")
        self.assertEqual([call.args[0].full_url for call in requests.call_args_list],
                         [eams_auth.SEND_SMS_URL, eams_auth.EGATE_BIND_URL])
        fetch.assert_not_called()
        audit.assert_not_called()

    def test_login_cannot_chain_personal_queries(self):
        with patch.object(eams_auth, "interactive_login") as login:
            code, _, _ = self.run_cli(["login", "--then", "audit"])
        self.assertEqual(code, 2)
        login.assert_not_called()

    def test_missing_cookie_recommends_login_without_blocking_public_query(self):
        code, output, error = self.run_cli(["location", "信息学院"])
        self.assertEqual(code, 0)
        self.assertIn("信息学院", output)
        self.assertIn("未检测到 Cookie", error)
        self.launch_mock.assert_called_once_with(method="sms")
        self.net_mock.assert_not_called()

    def test_saved_cookie_does_not_repeat_login_recommendation(self):
        credential_store.save_cookie("CASTGC=test-ticket")
        code, _, error = self.run_cli(["location", "信息学院"])
        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.launch_mock.assert_not_called()
        self.net_mock.assert_not_called()
        self.launch_mock.assert_not_called()

    def test_auth_status_only_reports_presence_without_network_or_secrets(self):
        for present in (False, True):
            if present:
                credential_store.save_cookie("CASTGC=test-ticket")
            code, output, error = self.run_cli(["auth-status", "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output), {"cookie_present": present, "session_validity": "not_checked"})
            self.assertNotIn("test-ticket", output + error)
        self.net_mock.assert_not_called()

    def test_legacy_login_entrypoint_does_not_chain_audit(self):
        entrypoint = Path(senior.__file__).with_name("login_and_fetch_plan.py")
        with patch.object(sys, "argv", [str(entrypoint)]), patch.object(senior, "main") as cli:
            with contextlib.redirect_stderr(io.StringIO()):
                runpy.run_path(str(entrypoint), run_name="__main__")
        cli.assert_called_once_with(["login"])

    def test_native_login_launcher_does_not_chain_audit(self):
        with patch.object(launch_terminal, "launch_in_terminal", return_value=True) as launch:
            self.assertTrue(self.original_launch_login())
        argv = shlex.split(launch.call_args.args[0])
        self.assertEqual(argv[0], sys.executable)
        self.assertEqual(Path(argv[1]), Path(senior.__file__))
        self.assertEqual(argv[2:], ["login", "--method", "sms"])

    def test_chat_login_opens_terminal_without_requesting_input_or_sms(self):
        with patch("sys.stdin.isatty", return_value=False), patch.object(eams_auth, "interactive_login") as login:
            code, _, error = self.run_cli(["login"])
        self.assertEqual(code, 0)
        self.assertIn("登录终端已打开", error)
        self.launch_mock.assert_called_once_with(method="sms")
        login.assert_not_called()
        self.net_mock.assert_not_called()

    def test_missing_cookie_query_opens_only_one_terminal(self):
        code, _, _ = self.run_cli(["exams", "--json"])
        self.assertEqual(code, 1)
        self.launch_mock.assert_called_once_with(method="sms")

    def test_plain_missing_auth_status_opens_terminal(self):
        code, _, error = self.run_cli(["auth-status"])
        self.assertEqual(code, 0)
        self.assertIn("登录终端已打开", error)
        self.launch_mock.assert_called_once_with(method="sms")

    def test_failed_terminal_launch_is_reported_without_claiming_login(self):
        self.launch_mock.return_value = False
        with patch("sys.stdin.isatty", return_value=False):
            code, _, error = self.run_cli(["login"])
        self.assertEqual(code, 1)
        self.assertIn("自动打开终端失败", error)


class TestExpiredSessions(IsolatedTest):
    def test_school_http401_opens_login_terminal(self):
        credential_store.save_cookie("CASTGC=test-ticket")
        error = urllib.error.HTTPError("https://example.invalid", 401, "Unauthorized", {}, None)
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(live_session.AuthenticationRequired):
                live_session.post_json("/auth/third-party/eams", {})
        self.launch_mock.assert_called_once_with(method="sms")

    def test_explicit_expired_business_response_opens_login_terminal(self):
        response = contextlib.nullcontext(io.BytesIO(json.dumps({"success": False, "error": "会话已过期"}).encode()))
        with patch("urllib.request.urlopen", return_value=response):
            with self.assertRaises(live_session.AuthenticationRequired):
                live_session.post_json("/egate-app/history", {})
        self.launch_mock.assert_called_once_with(method="sms")

    def test_repeated_platform_auth_failures_open_one_terminal(self):
        for path in ("/auth/third-party/eams", "/auth/third-party/elearning"):
            response = contextlib.nullcontext(io.BytesIO(b'{"success":false,"code":"SESSION_EXPIRED"}'))
            with patch("urllib.request.urlopen", return_value=response):
                with self.assertRaises(live_session.AuthenticationRequired):
                    live_session.post_json(path, {})
        self.launch_mock.assert_called_once_with(method="sms")

    def test_network_and_permission_errors_do_not_prompt_login(self):
        for error in (urllib.error.URLError("SSL EOF"), TimeoutError(),
                      urllib.error.HTTPError("https://example.invalid", 403, "Forbidden", {}, None),
                      urllib.error.HTTPError("https://example.invalid", 503, "Unavailable", {}, None)):
            with patch("urllib.request.urlopen", side_effect=error):
                with self.assertRaises(live_session.LiveQueryError) as raised:
                    live_session.post_json("/schedule/semesters", {})
                self.assertNotIsInstance(raised.exception, live_session.AuthenticationRequired)
        self.launch_mock.assert_not_called()

    def test_independent_gradescope_failure_does_not_prompt_campus_login(self):
        error = urllib.error.HTTPError("https://example.invalid", 401, "Unauthorized", {}, None)
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(live_session.LiveQueryError):
                live_session.post_json("/deadlines/gradescope", {})
        self.launch_mock.assert_not_called()

    def test_direct_eams_login_redirect_opens_terminal(self):
        from email.message import Message
        response = io.BytesIO(b'<html>Login</html>')
        response.geturl = lambda: "https://ids.shanghaitech.edu.cn/authserver/login"
        response.headers = Message()
        with patch("urllib.request.OpenerDirector.open", return_value=response):
            with self.assertRaises(live_session.AuthenticationRequired):
                eams_session.fetch_eams_html("JSESSIONID=test")
        self.launch_mock.assert_called_once_with(method="sms")


class TestLiveProtocol(IsolatedTest):
    def test_successful_empty_payload_is_valid(self):
        response = contextlib.nullcontext(io.BytesIO(b'{"success":true,"data":[]}'))
        with patch("urllib.request.urlopen", return_value=response) as request:
            self.assertEqual(live_session.post_json("/test", {}), [])
        self.assertEqual(request.call_args.args[0].get_header("Cache-control"), "no-cache, no-store")

    def test_missing_data_and_business_failure_are_errors(self):
        for payload in ({"success": True}, {"success": False, "data": []}, {"success": True, "data": None}):
            response = contextlib.nullcontext(io.BytesIO(json.dumps(payload).encode()))
            with patch("urllib.request.urlopen", return_value=response):
                if "data" not in payload or not payload["success"]:
                    with self.assertRaises(live_session.LiveQueryError):
                        live_session.post_json("/test", {})
                else:
                    self.assertIsNone(live_session.post_json("/test", {}))

    def test_no_credentials_fail_before_network(self):
        for command in ("audit", "schedule", "exams", "gym", "activities", "ics"):
            with self.subTest(command=command):
                code, _, _ = self.run_cli([command, "--json"] if command not in ("ics",) else [command])
                self.assertEqual(code, 1)
        self.net_mock.assert_not_called()

    def test_removed_file_inputs_and_module_are_unavailable(self):
        for argv in (["audit", "--file", "old.json"], ["ics", "--input", "old.json"],
                     ["ics", "-o", "out.ics"], ["exams", "--ics", "out.ics"], ["elrc", "CS100"]):
            self.assertEqual(self.run_cli(argv)[0], 2)


class TestScheduleAndAudit(IsolatedTest):
    def test_profile_supports_live_english_layout_without_content_class(self):
        html = '<table><tr><td class="title">Student No：</td><td>0000000000</td>' \
               '<td class="title">Name：</td><td>TEST NAME</td></tr>' \
               '<tr><td>Grade：</td><td>2030</td><td>Major：</td><td>TEST MAJOR</td></tr></table>'
        profile = eams_session.parse_student_profile(html)
        self.assertEqual(profile["student_id"], "0000000000")
        self.assertEqual(profile["grade"], 2030)
        self.assertEqual(profile["major"], "TEST MAJOR")

    def test_profile_supports_chinese_entities_and_class_variations(self):
        html = '<table><tr><td>&#23398;&#21495;:</td><td class="content">0000000000</td></tr></table>'
        self.assertEqual(eams_session.parse_student_profile(html)["student_id"], "0000000000")
        self.assertIsNone(eams_session.parse_student_profile('<table><tr><td>Login</td></tr></table>'))

    def test_dynamic_semester_and_online_calendar_no_personal_file_io(self):
        replies = [
            {"semesters": {"2030-2031": {"秋": "live-id"}}, "defaultSemester": "live-id", "tableId": "live-table"},
            {"courses": [], "periods": [{"1": "08:00-08:45"}]},
            {"termBegin": "2030-09-02"},
        ]
        with patch.object(live_session, "derive_cookies", return_value="derived"), \
             patch.object(sync_my_plan, "derive_cookies", return_value="derived"), \
             patch.object(sync_my_plan, "require_cookie", return_value="test"), \
             patch.object(eams_session, "get_student_profile", return_value={"student_id": "TEST_ID"}), \
             patch.object(sync_my_plan, "post_json", side_effect=replies) as api, \
             patch("builtins.open", side_effect=AssertionError("personal file I/O")):
            data = sync_my_plan.fetch_live_schedule(with_calendar=True)
        self.assertEqual(data["semester_id"], "live-id")
        self.assertEqual(data["termBegin"], "2030-09-02")
        self.assertEqual(api.call_args_list[1].args[1]["table_id"], "live-table")
        self.assertEqual(api.call_args_list[1].args[1]["studentId"], "TEST_ID")
        self.assertEqual(api.call_args_list[2].args[1]["year"], "2030")

    def test_missing_semester_never_uses_hardcoded_fallback(self):
        with patch.object(sync_my_plan, "derive_cookies", return_value="derived"), \
             patch.object(sync_my_plan, "require_cookie", return_value="test"), \
             patch.object(eams_session, "get_student_profile", return_value={"student_id": "TEST_ID"}), \
             patch.object(sync_my_plan, "post_json", return_value={"semesters": {}}):
            with self.assertRaises(live_session.LiveQueryError):
                sync_my_plan.fetch_live_schedule()

    def test_audit_always_fetches_official_completion_page(self):
        record = {"completed": {}, "in_progress": {}, "header": {"grade": 2023, "major": "计算机", "compl_credits": 0},
                  "source": "EAMS", "queried_at": "test-time"}
        with patch.object(sync_my_plan, "fetch_live_plan", return_value=record) as fetch:
            code, output, _ = self.run_cli(["audit", "--json"])
        self.assertEqual(code, 0)
        fetch.assert_called_once()
        self.assertEqual(json.loads(output)["header"]["compl_credits"], 0)

    def test_unknown_cohort_does_not_default_to_2026_cs(self):
        with self.assertRaises(live_session.LiveQueryError):
            analyze_plan.resolve_curriculum_path("计算机", 2031)
        with self.assertRaises(live_session.LiveQueryError):
            analyze_plan.resolve_curriculum_path(None, None)

    def test_missing_public_curriculum_keeps_live_eams_result(self):
        record = {"completed": {}, "in_progress": {}, "header": {"grade": 2031, "major": "计算机", "compl_credits": 0},
                  "source": "EAMS", "queried_at": "test-time"}
        with patch.object(sync_my_plan, "fetch_live_plan", return_value=record):
            code, output, _ = self.run_cli(["audit", "--json"])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(output)["analysis"]["comparison_available"])

    def test_eams_html_preserves_official_credits_and_failed_course(self):
        html = '<table><tr><td>要求学分/完成学分/实修学分:</td><td>10.5&nbsp;/&nbsp;4.5&nbsp;/&nbsp;2.0</td></tr>' \
               '<tr><td>CS100</td><td>TEST COURSE</td><td>2</td><td>2</td><td>2</td><td>A</td><td>否</td></tr></table>'
        completed, in_progress, header = analyze_plan.parse_html_plan(html)
        self.assertEqual(header["compl_credits"], 4.5)
        self.assertFalse(completed)
        self.assertFalse(in_progress)

    def test_ics_uses_live_term_and_periods_only_stdout(self):
        data = {"courses": [{"name": "TEST COURSE", "weeks": "01", "times": {"1": "1"}}],
                "periods": [{"1": "08:00-08:45"}], "termBegin": "2030-09-02"}
        with patch.object(sync_my_plan, "fetch_live_schedule", return_value=data), \
             patch("builtins.open", side_effect=AssertionError("personal file I/O")):
            code, output, _ = self.run_cli(["ics"])
        self.assertEqual(code, 0)
        self.assertIn("20300902T080000", output)
        self.assertIn("BEGIN:VCALENDAR", output)


class TestExams(IsolatedTest):
    def test_success_empty_is_distinct_from_malformed_response(self):
        with patch.object(query_exams, "schedule_context", return_value=("test", "TEST_ID", "live-id", {}, ())):
            with patch.object(query_exams, "post_json", return_value={"exams": []}):
                self.assertEqual(query_exams.fetch_live_exams()["exams"], [])
            with patch.object(query_exams, "post_json", return_value={}):
                with self.assertRaises(live_session.LiveQueryError):
                    query_exams.fetch_live_exams()


class TestDeadlines(IsolatedTest):
    def test_hydro_queries_each_configured_domain(self):
        with patch.object(query_deadlines, "post_json", side_effect=[[], []]) as api:
            ok, items, _ = query_deadlines.fetch_live_hydro("test", ["domain-a", "domain-b"])
        self.assertTrue(ok)
        self.assertEqual(items, [])
        self.assertEqual(len(api.call_args_list), 2)
        self.assertTrue(api.call_args_list[1].args[1]["args"]["url"].endswith("/d/domain-b"))

    def test_hydro_partial_failure_is_incomplete(self):
        with patch.object(query_deadlines, "post_json", side_effect=[[], live_session.LiveQueryError("offline")]):
            ok, items, _ = query_deadlines.fetch_live_hydro("test", ["a", "b"])
        self.assertFalse(ok)
        self.assertEqual(items, [])

    def test_gradescope_does_not_require_cas_or_other_platforms(self):
        with patch.dict(os.environ, {"GRADESCOPE_TOKEN": "test"}), \
             patch.object(query_deadlines, "post_json", return_value=[]) as api:
            code, output, _ = self.run_cli(["deadlines", "--platform", "gradescope", "--json"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output)["complete"])
        api.assert_called_once_with("/deadlines/gradescope", {"token": "test"})

    def test_partial_failure_returns_only_live_records_and_unknown_status(self):
        with patch.object(query_deadlines, "get_cas_tgc", return_value="test"), \
             patch.object(query_deadlines, "fetch_live_blackboard", return_value=(True, [], "ok")), \
             patch.object(query_deadlines, "fetch_live_exams_deadlines", return_value=(False, [], "offline")), \
             patch("builtins.open", side_effect=AssertionError("personal cache access")):
            data, statuses = query_deadlines.sync_all_deadlines()
        self.assertFalse(data["complete"])
        self.assertEqual(data["assignments"], [])
        self.assertIn("完整待办状态未知", query_deadlines.format_deadlines_report(data, sync_status=statuses))

    def test_missing_all_credentials_exits_nonzero_including_json(self):
        code, output, _ = self.run_cli(["deadlines", "--json"])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(output)["complete"])

    def test_unix_due_timestamp_is_not_unknown(self):
        self.assertIsInstance(query_deadlines.parse_iso_datetime(1900000000), datetime)


class TestActivities(IsolatedTest):
    def test_activity_fields_from_live_response_and_no_file_writes(self):
        payload = {"rows": [{"HDMC": "TEST ACTIVITY", "HDLX_DISPLAY": "形势与政策", "HDZT_DISPLAY": "已结束"}]}
        with patch.object(query_activities, "derive_cookies", return_value="derived"), \
             patch.object(query_activities, "post_json", return_value=payload), \
             patch("builtins.open", side_effect=AssertionError("personal cache access")):
            data = query_activities.sync_activities_from_techpie(student_id="TEST_ID")
        self.assertFalse(data["activities"][0]["creditCounted"])
        self.assertIn("0 条存在", query_activities.format_activities_report(data))
        self.assertNotIn("requiredLectures", data)

    def test_live_empty_history_is_successful(self):
        with patch.object(query_activities, "derive_cookies", return_value="derived"), \
             patch.object(query_activities, "post_json", return_value={"rows": []}):
            data = query_activities.sync_activities_from_techpie(student_id="TEST_ID")
        self.assertIn("查询成功", query_activities.format_activities_report(data))

    def test_live_failure_does_not_fallback(self):
        with patch.object(query_activities, "sync_activities_from_techpie", side_effect=live_session.LiveQueryError("offline")):
            code, output, error = self.run_cli(["activities", "--json"])
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("offline", error)


class TestGym(IsolatedTest):
    def test_json_queries_live_and_never_reads_cache(self):
        with patch.object(query_gym, "sync_live_gym_data", side_effect=live_session.LiveQueryError("offline")) as fetch:
            code, output, _ = self.run_cli(["gym", "网球", "--json"])
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        fetch.assert_called_once()

    def test_cross_sport_court_has_its_own_live_state(self):
        rows = [{"sport": "tennis", "date": "2030-09-02", "timeSlot": 1, "availableCourts": [1]},
                {"sport": "pickleball", "date": "2030-09-02", "timeSlot": 1, "availableCourts": []}]
        with patch.object(query_gym, "oa_auth", return_value={}), patch.object(query_gym, "post_json", return_value=rows):
            data = query_gym.sync_live_gym_data("tennis", "2030-09-02", 1, 1)
        self.assertEqual(data["schedule"][0]["free"], ["网球场1号"])
        self.assertIn("匹克球1号场地（可打网球）", data["schedule"][0]["unavailable"])

    def test_missing_or_wrong_date_response_is_not_full_availability(self):
        for rows in ([], [{"sport": "badminton", "date": "wrong", "timeSlot": 1, "availableCourts": []}]):
            with patch.object(query_gym, "oa_auth", return_value={}), patch.object(query_gym, "post_json", return_value=rows):
                with self.assertRaises(live_session.LiveQueryError):
                    query_gym.sync_live_gym_data("badminton", "2030-09-02", 1, 1)


class TestPublicCampusTools(unittest.TestCase):
    def test_location_and_calendar_remain_available(self):
        location = campus_locations.find_location("信息学院1A-200")
        self.assertEqual(location.keyword, "信息学院")
        self.assertIn("X-APPLE-STRUCTURED-LOCATION", campus_locations.format_apple_structured_location(location))
        self.assertIn("BEGIN:VCALENDAR", export_schedule_ics.build_ics_calendar([], date(2030, 9, 2)))


if __name__ == "__main__":
    unittest.main()
