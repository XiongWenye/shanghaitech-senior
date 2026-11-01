import os
import glob
import subprocess
from concurrent.futures import ProcessPoolExecutor

OCR_TOOL = "scripts/ocr_pdf"
INPUT_DIR = "培养方案"
OUTPUT_DIR = "data/ocr_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

MAPPING = {
    "2026级本科信息与计算科学专业培养方案.pdf": "2026_ICS.json",
    "2026级本科化学专业培养方案.pdf": "2026_CHEM.json",
    "2026级本科工业设计专业培养方案.pdf": "2026_ID.json",
    "2026级本科数学与应用数学专业培养方案.pdf": "2026_MATH.json",
    "2026级本科材料科学与工程专业培养方案.pdf": "2026_MSE.json",
    "2026级本科物理学专业培养方案.pdf": "2026_PHYS.json",
    "2026级本科生物医学工程专业培养方案.pdf": "2026_BME.json",
    "2026级本科生物技术专业培养方案.pdf": "2026_BIOTECH.json",
    "2026级本科生物科学专业培养方案.pdf": "2026_BIOSCI.json",
    "2026级本科电子信息工程专业培养方案.pdf": "2026_EE.json",
    "2026级本科计算机科学与技术专业培养方案.pdf": "2026_CS.json",
    "2026级本科计算机科学与技术专业（人工智能荣誉班）培养方案.pdf": "2026_CS_AI.json",
}

def run_ocr(item):
    pdf_name, json_name = item
    pdf_path = os.path.join(INPUT_DIR, pdf_name)
    json_path = os.path.join(OUTPUT_DIR, json_name)
    if os.path.exists(json_path) and os.path.getsize(json_path) > 1000:
        print(f"Skipping {pdf_name}, already exists ({json_path})")
        return (pdf_name, True)
    print(f"Starting OCR: {pdf_name} -> {json_path}")
    res = subprocess.run([OCR_TOOL, pdf_path, json_path], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Finished OCR: {pdf_name}")
        return (pdf_name, True)
    else:
        print(f"Failed OCR: {pdf_name}: {res.stderr}")
        return (pdf_name, False)

if __name__ == "__main__":
    items = list(MAPPING.items())
    with ProcessPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run_ocr, items))
    print("All OCR jobs completed:", results)
