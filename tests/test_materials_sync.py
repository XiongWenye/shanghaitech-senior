import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import materials_sync as sync
import query_materials as query
import build_index


def catalog_item(folder, names, **identity):
    item = {"folder_name": folder, "repo_url": "https://example.org/" + folder,
            **{category: [] for category in sync.FILE_CATEGORIES}, **identity}
    for name in names:
        item["others"].append({"name": name, "rel_path": folder + "/" + name,
                               "url": "https://example.org/" + folder + "/" + name})
    item["total_files"] = len(names)
    return item


def circuits_catalog():
    # Real upstream filenames: the 2025 PDF has no exam keywords and is in others.
    return {"courses": {
        "电路基础": catalog_item("电路基础", ["EE111 2025Spring.pdf", "1_EE111-finalexam-23Fall.pdf",
                                            "EE111 Final Cheat_Sheet.pdf"]),
        "电路基础实验": catalog_item("电路基础实验", ["Lab1_基础电路测量实验讲义.pdf"]),
    }}


def baseline():
    return {"courses": {
        "EE111": {"code": "EE111", "name_zh": "电路基础", "resources": {"itechx": {"available": True}}},
        "EE111L": {"code": "EE111L", "name_zh": "电路基础实验", "resources": {}},
    }, "inverted_index": {}}


class MaterialsSyncTests(unittest.TestCase):
    def test_legacy_catalog_separates_theory_and_lab_in_both_orders(self):
        cat = circuits_catalog()
        for ordered in (cat, {"courses": dict(reversed(list(cat["courses"].items())))}):
            index = sync.overlay_latest_materials(baseline(), ordered)
            for code, folder, count in (("EE111", "电路基础", 3), ("EE111L", "电路基础实验", 1)):
                resource = index["courses"][code]["resources"]["xiongwenye"]
                self.assertEqual(resource["folder_name"], folder)
                self.assertEqual(resource["total_files"], count)
                self.assertTrue(all(f["rel_path"].split("/")[0] == folder for f in resource["others"]))

    def test_v2_course_identity_is_consumed(self):
        cat = circuits_catalog()
        for name, code in (("电路基础", "EE111"), ("电路基础实验", "EE111L")):
            cat["courses"][name].update(course_code=code, course_type="lab" if code.endswith("L") else "theory")
        self.assertEqual(sync.group_catalog_courses(cat, {})[1], {"电路基础": "EE111", "电路基础实验": "EE111L"})

    def test_no_substring_matching_or_unmatched_folder_loss(self):
        courses = {"EE900L": {"name_zh": "电路与系统实验"}, "EE900": {"name_zh": "电路与系统"}}
        self.assertEqual(sync.resolve_catalog_course_code("电路与系统", {}, courses), "EE900")
        self.assertEqual(sync.resolve_catalog_course_code("电路", {}, courses), "电路")
        cat = {"courses": {"电路": catalog_item("电路", ["review.pdf"])}}
        self.assertIn("电路", sync.overlay_latest_materials({"courses": courses}, cat)["courses"])

    def test_lab_suffix_inference_and_existing_numeric_exceptions(self):
        courses = {"EE999": {"name_zh": "示例电路"}, "BIO1024": {"name_zh": "分子生物学实验"}}
        self.assertEqual(sync.resolve_catalog_course_code("示例电路实验", {}, courses), "EE999L")
        self.assertEqual(sync.resolve_catalog_course_code("分子生物学实验", {}, courses), "BIO1024")
        self.assertEqual(sync.resolve_catalog_course_code("未知实验", {}, courses), "未知实验")

    def test_invalid_upstream_identity_does_not_overwrite_theory(self):
        for item in ({"course_code": "EE111"}, {"course_code": "EE111L", "course_type": "theory"}):
            with self.assertRaises(ValueError):
                sync.resolve_catalog_course_code("电路基础实验", item, baseline()["courses"])

    def test_true_aliases_merge_files_and_repeat_overlay_is_idempotent(self):
        a = catalog_item("信导", ["a.pdf"], course_code="SI100B", course_type="theory")
        b = catalog_item("信息科学技术导论", ["b.pdf"], course_code="SI100B", course_type="theory")
        b["others"].append(a["others"][0])  # duplicate URLs must not inflate totals
        cat = {"courses": {"信导": a, "信息科学技术导论": b}}
        index = sync.overlay_latest_materials({"courses": {}}, cat)
        resource = index["courses"]["SI100B"]["resources"]["xiongwenye"]
        self.assertEqual(resource["total_files"], 2)
        self.assertEqual(len(resource["folder_names"]), 2)
        previous = copy.deepcopy(index)
        self.assertEqual(sync.overlay_latest_materials(index, cat), previous)

    def test_old_polluted_source_and_aliases_are_repaired(self):
        index = baseline()
        index["courses"]["EE111"]["resources"]["xiongwenye"] = {"folder_name": "电路基础实验"}
        index["courses"]["EE111"]["aliases"] = ["电路基础实验"]
        index["inverted_index"]["电路基础实验"] = ["EE111", "EE111L"]
        index = sync.overlay_latest_materials(index, circuits_catalog())
        self.assertEqual(index["inverted_index"]["电路基础实验"], ["EE111L"])
        self.assertEqual(query.resolve_course_code(index, "电路基础实验"), "EE111L")
        self.assertTrue(index["courses"]["EE111"]["resources"]["itechx"]["available"])

    def test_report_contains_2025_unclassified_file_and_correct_course(self):
        index = sync.overlay_latest_materials(baseline(), circuits_catalog())
        theory = query.format_markdown_report(index["courses"]["EE111"])
        lab = query.format_markdown_report(index["courses"]["EE111L"])
        self.assertIn("EE111 2025Spring.pdf", theory)
        self.assertNotIn("Lab1_", theory)
        self.assertIn("Lab1_", lab)
        self.assertNotIn("2025Spring", lab)
        self.assertEqual(query.resolve_course_code(index, "ee111l"), "EE111L")

    def test_ambiguous_alias_is_not_resolved_arbitrarily(self):
        index = baseline()
        index["inverted_index"]["电路"] = ["EE111", "EE111L"]
        self.assertEqual(query.resolve_course_code(index, "电路"), ["EE111", "EE111L"])
        self.assertIsNone(query.resolve_course_code(index, ""))

    def test_identity_conflict_cannot_silently_fall_back_to_old_baseline(self):
        with patch.object(sync, "get_materials_index", side_effect=ValueError("identity conflict")):
            with self.assertRaises(SystemExit), patch("sys.stderr", io.StringIO()):
                query.load_index()

    def test_biology_theory_is_not_assigned_to_an_existing_lab(self):
        old = {"courses": {"BIO1026": {"name_zh": "中级生物学实验", "resources": {
            "xiongwenye": {"folder_name": "现代生物学实验理论"}}}}}
        cat = {"courses": {"现代生物学实验理论": catalog_item("现代生物学实验理论", ["review.pdf"])}}
        index = sync.overlay_latest_materials(old, cat)
        self.assertIn("BIO1008", index["courses"])
        self.assertNotIn("BIO1026", index["courses"])

    def test_local_and_github_tree_scanners_keep_course_identity_and_posix_urls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = ["电路基础/EE111 2025Spring.pdf", "电路基础实验/Lab1.pdf"]
            for path in paths:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch()
            local = sync.catalog_from_local_repo(root)
            tree = sync.catalog_from_github_tree([{"type": "blob", "path": path} for path in paths])
            for cat in (local, tree):
                self.assertEqual(cat["courses"]["电路基础实验"]["course_code"], "EE111L")
                self.assertEqual(cat["metadata"]["total_files"], 2)
                for course in cat["courses"].values():
                    for category in sync.FILE_CATEGORIES:
                        self.assertTrue(all("%5C" not in f["url"] for f in course[category]))

    def test_cache_and_network_sync_use_the_same_identity_rules(self):
        for force in (False, True):
            with ExitStack() as stack:
                stack.enter_context(patch.object(sync, "find_local_repo_path", return_value=None))
                stack.enter_context(patch.object(sync, "is_cache_fresh", return_value=True))
                stack.enter_context(patch.object(sync, "get_cached_catalog", return_value=circuits_catalog()))
                stack.enter_context(patch.object(sync, "fetch_url", return_value=json.dumps(circuits_catalog())))
                stack.enter_context(patch.object(sync, "save_cached_catalog"))
                catalog = sync.sync_catalog(force=force)
                index = sync.overlay_latest_materials(baseline(), catalog)
                self.assertEqual(index["courses"]["EE111L"]["resources"]["xiongwenye"]["total_files"], 1)

    def test_baseline_builder_preserves_files_and_uses_the_live_resolver(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            for name in ("parse_itechx", "parse_skkk256", "parse_wutianyuan1", "parse_profetia", "parse_gkxx", "parse_rulerfuhai"):
                stack.enter_context(patch.object(build_index, name, return_value={}))
            stack.enter_context(patch.object(build_index, "ZSC_COURSES", {}))
            stack.enter_context(patch.object(build_index, "load_coursebench_db", return_value={
                "EE111": {"name": "电路基础"}, "EE111L": {"name": "电路基础实验"}}))
            stack.enter_context(patch.object(build_index, "parse_xiongwenye", return_value=circuits_catalog()["courses"]))
            output = Path(temp) / "index.json"
            stack.enter_context(patch.object(build_index, "OUTPUT_INDEX_FILE", output))
            with redirect_stdout(io.StringIO()):
                build_index.build_unified_index()
            index = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(index["courses"]["EE111"]["resources"]["xiongwenye"]["total_files"], 3)
            self.assertEqual(index["courses"]["EE111L"]["resources"]["xiongwenye"]["total_files"], 1)
            self.assertIn("2025Spring", query.format_markdown_report(index["courses"]["EE111"]))


if __name__ == "__main__":
    unittest.main()
