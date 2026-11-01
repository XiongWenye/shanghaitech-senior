#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Decoupled Materials Synchronizer for ShanghaiTech Course Database
Allows shanghaitech-senior skill to dynamically fetch and cache the latest
course materials from XiongWenye/shanghaitech-course-database without requiring
skill updates or code changes whenever new course materials are added.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import re
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
CACHE_CATALOG_FILE = CACHE_DIR / "xiongwenye_catalog.json"
CACHE_META_FILE = CACHE_DIR / "sync_metadata.json"
BASE_INDEX_FILE = DATA_DIR / "materials_index.json"

REPO_OWNER = "XiongWenye"
REPO_NAME = "shanghaitech-course-database"
RAW_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/catalog.json"
CDN_URL = f"https://cdn.jsdelivr.net/gh/{REPO_OWNER}/{REPO_NAME}@main/catalog.json"
TREES_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/main?recursive=1"

# Cache TTL: 24 hours (86400s)
DEFAULT_TTL = 86400

# Mapping from Chinese Course Name to Course Code
ZH_TO_CODE = {
    "计算机编程": "CS100",
    "算法与数据结构": "CS101",
    "计算机体系结构": "CS110",
    "离散数学": "SI120",
    "计算机图形学": "CS171",
    "信号与系统": "EE150",
    "概率论与数理统计": "SI140A",
    "计算机视觉": "CS172",
    "人工智能I": "CS181",
    "机器学习引论": "CS182",
    "通信原理": "EE140",
    "控制原理": "EE160",
    "信息科学技术导论": "SI100B",
    "信息科学与技术导论": "SI100B",
    "思想道德与法治": "GESS1028",
    "思修": "GESS1028",
    "数学分析I": "GEMA1009",
    "数学分析II": "GEMA1010",
    "高等数学I": "GEMA1001",
    "高等数学II": "GEMA1003",
    "线性代数I": "MATH1112",
    "普通物理I": "PHYS1181",
    "普通物理II": "PHYS1183",
    "普通物理I实验": "PHYS1111",
    "普通化学I": "CHEM1103",
    "普通化学II": "CHEM1111",
    "有机化学基础": "CHEM1322",
    "有机化学基础实验": "CHEM1340",
    "生物化学I": "BIO1003",
    "生物化学II": "BIO1004",
    "生物化学I实验": "BIO1021",
    "生物化学II实验": "BIO1022",
    "分子生物学": "BIO1006",
    "分子生物学实验": "BIO1024",
    "细胞生物学": "BIO1005",
    "细胞生物学实验": "BIO1023",
    "遗传学": "BIO1007",
    "癌症生物学": "BIO1068",
    "神经科学导论": "BIO1102",
    "分子细胞神经科学": "BIO2053",
    "果蝇生物学": "BIO1223",
    "现代生命科学导论B": "BIO1002",
    "现代生命科学导论C": "BIO1011",
    "现代生物学实验理论": "BIO1026",
    "生命科学导论A": "BIO1012",
    "生命科学导论B": "BIO1013",
    "生命科学与人类文明": "SL1012",
    "半导体器件基础": "EE120",
    "量子力学I": "PHYS1521",
    "量子力学II": "PHYS1531",
    "广义相对论与宇宙学": "PHYS2517",
    "世界文明通论": "GEHA1003",
    "中华文明通论": "GEHA1050",
    "经济学导论": "ECON1001",
    "军事理论": "CLEC1003",
    "中外歌剧赏析": "CLGE1007",
    "唐宋文学精华": "GEHA1001",
    "蛋白质设计科学与技术": "BIO1031",
    "电路基础实验": "EE111",
    "计算科学与工程": "MATH1113",
    "面向信息科学的概率论与数理统计": "SI140",
    "设计思维": "ARTS1001",
}


def find_local_repo_path():
    """Detect local clone if available in environment or sibling directory."""
    env_path = os.environ.get("SHANGHAITECH_DATABASE_DIR")
    if env_path and Path(env_path).is_dir():
        return Path(env_path)

    # Check sibling directory
    sibling = BASE_DIR.parent / "shanghaitech-course-database"
    if sibling.is_dir() and (sibling / ".git").exists():
        return sibling

    return None


def is_exam_file(path: str) -> bool:
    fl = path.lower()
    clean_fl = re.sub(r'examples?', '', fl)
    if any(k in clean_fl for k in ['final', 'midterm', '期末', '期中', '试卷', '考试', '真题', 'cheatsheet', 'cheat sheet', 'cheat_sheet', '速查', 'quiz', '小测', '测验']):
        return True
    if re.search(r'[\W_]exam[\W_.]', clean_fl) or clean_fl.endswith(('exam.pdf', 'exam.docx', 'exam.md')):
        return True
    return False


def is_solution_file(path: str) -> bool:
    fl = path.lower()
    if any(k in fl for k in ['solution', 'solutions', 'answer', 'answers', '答案', '解析', '评分标准']):
        return True
    if re.search(r'[\W_](sol|ans|key)[\W_.]', fl):
        return True
    if fl.endswith(('_sol.pdf', '-sol.pdf', '_ans.pdf', '-ans.pdf', '_key.pdf', '-key.pdf', '_sol.docx', '-sol.docx')):
        return True
    return False


def catalog_from_local_repo(repo_dir: Path) -> dict:
    """Build catalog from local directory."""
    base_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/tree/main"
    blob_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/main"
    excluded_dirs = {".git", ".github", "scripts", ".idea", ".vscode", "__pycache__"}
    excluded_files = {".DS_Store", "catalog.json", "README.md", ".gitignore", "LICENSE"}

    courses = {}
    total_files = 0
    total_exams = 0
    total_solutions = 0

    for entry in sorted(os.listdir(repo_dir)):
        entry_path = repo_dir / entry
        if not entry_path.is_dir() or entry in excluded_dirs or entry.startswith('.'):
            continue

        course_name = entry
        encoded_name = urllib.parse.quote(course_name)
        course_data = {
            "folder_name": course_name,
            "repo_url": f"{base_url}/{encoded_name}",
            "exams": [],
            "solutions": [],
            "slides_notes": [],
            "labs": [],
            "others": [],
            "total_files": 0
        }

        for root, dirs, files in os.walk(entry_path):
            if ".git" in root:
                continue
            for f in sorted(files):
                if f in excluded_files or f.startswith('.'):
                    continue
                abs_f = os.path.join(root, f)
                rel_f = os.path.relpath(abs_f, repo_dir)
                encoded_rel = urllib.parse.quote(rel_f)
                file_info = {
                    "name": f,
                    "rel_path": rel_f,
                    "url": f"{blob_url}/{encoded_rel}"
                }
                course_data["total_files"] += 1
                total_files += 1

                fl = f.lower()
                if is_exam_file(rel_f):
                    if is_solution_file(rel_f):
                        course_data["solutions"].append(file_info)
                        total_solutions += 1
                    else:
                        course_data["exams"].append(file_info)
                        total_exams += 1
                elif is_solution_file(rel_f):
                    course_data["solutions"].append(file_info)
                    total_solutions += 1
                elif any(k in fl for k in ["实验", "lab"]):
                    course_data["labs"].append(file_info)
                elif any(k in fl for k in ["讲义", "课件", "ppt", "slide", "第", "章", "note", "笔记", "mp4"]):
                    course_data["slides_notes"].append(file_info)
                else:
                    course_data["others"].append(file_info)

        courses[course_name] = course_data

    return {
        "metadata": {
            "source": f"local:{repo_dir}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_courses": len(courses),
            "total_files": total_files,
            "total_exams": total_exams,
            "total_solutions": total_solutions
        },
        "courses": courses
    }


def catalog_from_github_tree(tree_data: list) -> dict:
    """Build catalog from GitHub API tree response."""
    base_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/tree/main"
    blob_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/main"
    excluded_dirs = {".git", ".github", "scripts", ".idea", ".vscode", "__pycache__"}
    excluded_files = {".DS_Store", "catalog.json", "README.md", ".gitignore", "LICENSE"}

    courses = {}
    total_files = 0
    total_exams = 0
    total_solutions = 0

    for item in tree_data:
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        parts = path.split("/")
        if len(parts) < 2:
            continue
        course_name = parts[0]
        if course_name in excluded_dirs or course_name.startswith('.'):
            continue

        filename = parts[-1]
        if filename in excluded_files or filename.startswith('.'):
            continue

        if course_name not in courses:
            encoded_name = urllib.parse.quote(course_name)
            courses[course_name] = {
                "folder_name": course_name,
                "repo_url": f"{base_url}/{encoded_name}",
                "exams": [],
                "solutions": [],
                "slides_notes": [],
                "labs": [],
                "others": [],
                "total_files": 0
            }

        encoded_rel = urllib.parse.quote(path)
        file_info = {
            "name": filename,
            "rel_path": path,
            "url": f"{blob_url}/{encoded_rel}"
        }

        course_item = courses[course_name]
        course_item["total_files"] += 1
        total_files += 1

        fl = filename.lower()
        if is_exam_file(path):
            if is_solution_file(path):
                course_item["solutions"].append(file_info)
                total_solutions += 1
            else:
                course_item["exams"].append(file_info)
                total_exams += 1
        elif is_solution_file(path):
            course_item["solutions"].append(file_info)
            total_solutions += 1
        elif any(k in fl for k in ["实验", "lab"]):
            course_item["labs"].append(file_info)
        elif any(k in fl for k in ["讲义", "课件", "ppt", "slide", "第", "章", "note", "笔记", "mp4"]):
            course_item["slides_notes"].append(file_info)
        else:
            course_item["others"].append(file_info)

    return {
        "metadata": {
            "source": "github_api_tree",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_courses": len(courses),
            "total_files": total_files,
            "total_exams": total_exams,
            "total_solutions": total_solutions
        },
        "courses": courses
    }


def fetch_url(url: str, timeout: int = 5) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ShanghaiTechSenior-Skill/2.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def get_cached_catalog():
    if not CACHE_CATALOG_FILE.exists():
        return None
    try:
        with open(CACHE_CATALOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_cached_catalog(catalog: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    meta = {
        "last_sync_timestamp": time.time(),
        "last_sync_time": datetime.now(timezone.utc).isoformat(),
        "source": catalog.get("metadata", {}).get("source", "remote")
    }
    with open(CACHE_META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def is_cache_fresh(ttl: int = DEFAULT_TTL) -> bool:
    if not CACHE_CATALOG_FILE.exists() or not CACHE_META_FILE.exists():
        return False
    try:
        with open(CACHE_META_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
        last_sync = meta.get("last_sync_timestamp", 0)
        return (time.time() - last_sync) < ttl
    except Exception:
        return False


def sync_catalog(force: bool = False, verbose: bool = False) -> dict:
    """
    Fetch latest catalog with multiple fallbacks:
    1. Local repo (if found)
    2. Cached catalog (if fresh and not force)
    3. Remote Raw GitHub catalog.json
    4. Remote jsDelivr CDN catalog.json
    5. Remote GitHub Git Trees API
    6. Cached catalog (stale fallback)
    """
    # 1. Local repo auto-detection
    local_path = find_local_repo_path()
    if local_path and not force:
        # If catalog.json exists locally in repo, load it directly
        local_catalog_file = local_path / "catalog.json"
        if local_catalog_file.exists():
            try:
                with open(local_catalog_file, "r", encoding="utf-8") as f:
                    cat = json.load(f)
                    if verbose:
                        print(f"📁 Loaded upstream catalog from local repo ({local_path})")
                    save_cached_catalog(cat)
                    return cat
            except Exception:
                pass
        # Build from local directory
        cat = catalog_from_local_repo(local_path)
        if verbose:
            print(f"📁 Scanned upstream catalog from local repo ({local_path})")
        save_cached_catalog(cat)
        return cat

    # 2. Fresh cache check
    if not force and is_cache_fresh():
        cached = get_cached_catalog()
        if cached:
            if verbose:
                print("⚡ Using fresh local cache for course database")
            return cached

    # 3. Try Remote Raw GitHub
    if verbose:
        print("🌐 Syncing latest course database from GitHub...")
    for url, name in [(RAW_URL, "GitHub Raw"), (CDN_URL, "jsDelivr CDN")]:
        try:
            content = fetch_url(url, timeout=4)
            cat = json.loads(content)
            if "courses" in cat:
                cat["metadata"] = cat.get("metadata", {})
                cat["metadata"]["source"] = name
                save_cached_catalog(cat)
                if verbose:
                    print(f"✅ Synced {len(cat['courses'])} courses successfully from {name}")
                return cat
        except Exception as e:
            if verbose:
                print(f"⚠️ {name} sync failed ({e}), trying fallback...")

    # 4. Try GitHub Git Trees API
    try:
        content = fetch_url(TREES_API_URL, timeout=5)
        api_resp = json.loads(content)
        tree = api_resp.get("tree", [])
        if tree:
            cat = catalog_from_github_tree(tree)
            save_cached_catalog(cat)
            if verbose:
                print(f"✅ Generated catalog from GitHub Trees API ({len(cat['courses'])} courses)")
            return cat
    except Exception as e:
        if verbose:
            print(f"⚠️ GitHub Trees API sync failed: {e}")

    # 5. Stale cache fallback
    cached = get_cached_catalog()
    if cached:
        if verbose:
            print("ℹ️ Using existing local cached catalog (offline mode)")
        return cached

    # 6. Local repo fallback as last resort
    if local_path:
        cat = catalog_from_local_repo(local_path)
        save_cached_catalog(cat)
        return cat

    return {}


def overlay_latest_materials(base_index: dict, catalog: dict) -> dict:
    """
    Overlays dynamic XiongWenye catalog onto the unified materials_index.
    Ensures that any new/updated course in shanghaitech-course-database
    is instantly visible and searchable without updating the skill code.
    """
    if not catalog or "courses" not in catalog:
        return base_index

    courses = base_index.get("courses", {})
    inverted = base_index.get("inverted_index", {})

    xw_courses = catalog["courses"]

    for folder_name, xw_item in xw_courses.items():
        # Match to canonical course code
        target_code = None

        # 1. Direct code map
        if folder_name in ZH_TO_CODE:
            target_code = ZH_TO_CODE[folder_name]

        # 2. Match existing course by code or Chinese name
        if not target_code:
            for code, info in courses.items():
                if info.get("name_zh") == folder_name or folder_name in info.get("name_zh", ""):
                    target_code = code
                    break
                if code.lower() == folder_name.lower():
                    target_code = code
                    break

        # 3. If still not matched, use folder_name as its own code
        if not target_code:
            target_code = folder_name

        # Ensure course entry exists
        if target_code not in courses:
            courses[target_code] = {
                "code": target_code,
                "name_zh": folder_name,
                "name_en": "",
                "institute": "上海科技大学",
                "credit": 0.0,
                "cb_scores": {},
                "resources": {}
            }

        # Inject or update XiongWenye resources
        courses[target_code]["resources"]["xiongwenye"] = {
            "available": True,
            "folder_name": folder_name,
            "repo_url": xw_item.get("repo_url", ""),
            "exams": xw_item.get("exams", []),
            "solutions": xw_item.get("solutions", []),
            "slides_notes": xw_item.get("slides_notes", []),
            "labs": xw_item.get("labs", []),
            "others": xw_item.get("others", []),
            "total_files": xw_item.get("total_files", 0)
        }

        # Update inverted index
        aliases = [
            folder_name.lower(),
            target_code.lower(),
        ]
        if folder_name in ZH_TO_CODE:
            aliases.append(ZH_TO_CODE[folder_name].lower())

        for alias in aliases:
            if alias not in inverted:
                inverted[alias] = []
            if target_code not in inverted[alias]:
                inverted[alias].append(target_code)

    base_index["courses"] = courses
    base_index["inverted_index"] = inverted
    return base_index


def get_materials_index(force_refresh: bool = False, verbose: bool = False) -> dict:
    """
    Main entry point for retrieving the live unified materials index.
    Combines the baseline materials_index.json with real-time overlay from
    the dynamically synced shanghaitech-course-database catalog.
    """
    if not BASE_INDEX_FILE.exists():
        raise FileNotFoundError(f"Baseline index missing: {BASE_INDEX_FILE}")

    with open(BASE_INDEX_FILE, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    catalog = sync_catalog(force=force_refresh, verbose=verbose)
    if catalog:
        index_data = overlay_latest_materials(index_data, catalog)

    return index_data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Synchronize ShanghaiTech Course Database")
    parser.add_argument("--force", "-f", action="store_true", help="Force refresh remote catalog")
    parser.add_argument("--status", "-s", action="store_true", help="Show sync status")
    args = parser.parse_args()

    if args.status:
        is_fresh = is_cache_fresh()
        meta = {}
        if CACHE_META_FILE.exists():
            with open(CACHE_META_FILE, "r", encoding="utf-8") as f:
                meta = json.load(f)
        print(f"📊 Course Database Sync Status:")
        print(f"   Cache Fresh: {'✅ Yes' if is_fresh else '❌ Expired/Missing'}")
        print(f"   Last Sync: {meta.get('last_sync_time', 'Never')}")
        print(f"   Source: {meta.get('source', 'None')}")
        cat = get_cached_catalog()
        if cat:
            print(f"   Courses Indexed: {cat.get('metadata', {}).get('total_courses', 0)}")
            print(f"   Total Files: {cat.get('metadata', {}).get('total_files', 0)}")
            print(f"   Exams: {cat.get('metadata', {}).get('total_exams', 0)}")
        sys.exit(0)

    print("🚀 Synchronizing ShanghaiTech Course Database...")
    res = sync_catalog(force=args.force, verbose=True)
    meta = res.get("metadata", {})
    print(f"\n🎉 Sync completed! {meta.get('total_courses', 0)} courses and {meta.get('total_files', 0)} files available.")
