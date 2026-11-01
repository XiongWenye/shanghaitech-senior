import os
import json

CURRICULUM_DIR = "data/curriculums"

# Standard known sequences per major
STANDARD_SEQUENCES = {
    "2026_CS_SIST": {
        "1": ["MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "MATH1112", "GEMA1001", "GEMA1009", "SI100B", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["CS100", "SI120", "GEMA1003", "GEMA1010", "CHEM1103", "BIO1002", "BIO1011", "GEHA1132", "GEHA1150", "GEHA1302", "ECON1014", "CLPE1002"],
        "3": ["CLGE1007", "GEHA1046", "GEHA1087"],
        "4": ["CS101", "PHYS1181", "PHYS1111", "SI140A", "EE111", "EE111L", "GESS1018", "GEHA1123", "GEHA1152"],
        "5": ["CS110", "CS130", "CS181", "EE150", "EE150L", "MT1023", "ARTS1422", "ARTS1102"],
        "6": ["CS110P"],
        "7": ["CS171", "CS182", "CS120", "CS150A", "SI152", "GESS1027", "ENTR1006", "SEMI1016"],
        "8": ["CS172", "CS280", "CS131", "CS132", "CS121", "CS240"]
    },
    "2026_CS_AI_SIST": {
        "1": ["CS101A", "MATH1112", "GEMA1001", "GEMA1009", "MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["CS140A", "SI120", "CS181", "GEMA1003", "GEMA1010", "CHEM1103", "BIO1002", "GEHA1132", "GEHA1150", "GEHA1302", "ECON1014", "CLPE1002"],
        "3": ["CLGE1007"],
        "4": ["CS110A", "CS182", "PHYS1181", "PHYS1111", "SI140A", "EE111", "EE111L", "GESS1018", "GEHA1123"],
        "5": ["CS130", "CS280", "SI152", "SI191C", "EE150", "EE150L", "MT1023", "ARTS1422"],
        "6": ["SI191C"],
        "7": ["CS272", "CS284", "CS288", "SI252", "GESS1027", "ENTR1006"],
        "8": ["CS286", "CS289", "CS274A", "SI253"]
    },
    "2026_EE_SIST": {
        "1": ["MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "MATH1112", "GEMA1001", "GEMA1009", "SI100B", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["CS100", "EE111", "EE111L", "GEMA1003", "GEMA1010", "PHYS1181", "PHYS1111", "GEHA1132", "GEHA1150", "GEHA1302", "CLPE1002"],
        "3": ["CLGE1007"],
        "4": ["EE150", "EE150L", "CS101", "PHYS1183", "PHYS1113", "SI140A", "GESS1018", "GEHA1123"],
        "5": ["EE120", "EE130", "EE140", "MT1023", "ARTS1422"],
        "7": ["EE160", "EE170", "GESS1027"]
    },
    "2026_MATH_IMS": {
        "1": ["MATH1112", "GEMA1009", "CS100", "MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["MATH1122", "GEMA1010", "PHYS1181", "PHYS1111", "GEHA1132", "GEHA1150", "GEHA1302", "CLPE1002"],
        "4": ["MATH1211", "MATH1131", "MATH1212", "PHYS1183", "PHYS1113", "GESS1018", "GEHA1123"],
        "5": ["MATH1223", "MATH1123", "MATH1224", "MT1023"],
        "7": ["MATH1323", "GESS1027"]
    },
    "2026_ICS_IMS": {
        "1": ["MATH1112", "GEMA1009", "SI100B", "MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["CS100", "SI120", "MATH1122", "GEMA1010", "PHYS1181", "PHYS1111", "GEHA1132", "GEHA1150", "GEHA1302", "CLPE1002"],
        "4": ["CS101", "SI140A", "SI152", "GESS1018", "GEHA1123"],
        "5": ["CS181", "CS182", "SI211", "MT1023"],
        "7": ["CS150A", "SI251", "GESS1027"]
    },
    "2026_PHYS_SPST": {
        "1": ["MATH1112", "GEMA1009", "PHYS1181", "PHYS1111", "SI100B", "MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["GEMA1010", "PHYS1183", "PHYS1113", "CHEM1103", "CHEM1100", "MSE1112", "GEHA1132", "GEHA1150", "GEHA1302", "CLPE1002"],
        "4": ["MATH1213", "PHYS1302", "PHYS1371", "GESS1018", "GEHA1123"],
        "5": ["PHYS1313", "PHYS1314", "PHYS1521", "MT1023"],
        "7": ["PHYS1531", "PHYS1503", "PHYS1512", "PHYS1707", "GESS1027"]
    },
    "2026_CHEM_SPST": {
        "1": ["CHEM1103", "CHEM1100", "MATH1112", "GEMA1001", "GEMA1009", "PHYS1181", "PHYS1111", "MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["CHEM1111", "CHEM1110", "PHYS1183", "PHYS1113", "GEMA1003", "GEMA1010", "MSE1112", "GEHA1132", "GEHA1150", "GEHA1302", "CLPE1002"],
        "4": ["CHEM1300", "CHEM1311", "CHEM1321", "GESS1018", "GEHA1123"],
        "5": ["CHEM1401", "CHEM1411", "MT1023"],
        "7": ["GESS1027"]
    },
    "2026_MSE_SPST": {
        "1": ["MSE1112", "MATH1112", "GEMA1001", "GEMA1009", "PHYS1181", "PHYS1111", "SI100B", "MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["CHEM1103", "CHEM1100", "PHYS1183", "PHYS1113", "GEMA1003", "GEMA1010", "GEHA1132", "GEHA1150", "GEHA1302", "CLPE1002"],
        "4": ["MSE1311", "MSE1321", "GESS1018", "GEHA1123"],
        "5": ["MSE1325", "MSE1501", "MT1023"],
        "7": ["MSE1503", "MSE1701", "GESS1027"]
    },
    "2026_BIOSCI_SLST": {
        "1": ["CHEM1103", "CHEM1100", "PHYS1181", "PHYS1111", "GEMA1001", "GEMA1009", "MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["CHEM1111", "CHEM1110", "MATH1112", "GEMA1003", "GEMA1010", "BIO1028", "GEHA1132", "GEHA1150", "GEHA1302", "CLPE1002"],
        "4": ["BIO1003", "BIO1021", "BIO1005", "BIO1023", "GESS1018", "GEHA1123"],
        "5": ["BIO1004", "BIO1022", "BIO1006", "BIO1024", "BIO1007", "BIO1025", "MT1023"],
        "7": ["BIO1027", "GESS1027"]
    },
    "2026_BIOTECH_SLST": {
        "1": ["CHEM1103", "CHEM1100", "PHYS1181", "PHYS1111", "SI100B", "MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["CHEM1322", "CHEM1340", "MATH1112", "BIO1028", "GEHA1132", "GEHA1150", "GEHA1302", "CLPE1002"],
        "4": ["BT1001", "BT1023", "BIO1003", "BIO1021", "GESS1018", "GEHA1123"],
        "5": ["BT1002", "BIO1004", "BIO1022", "MT1023"],
        "7": ["BIO1027", "GESS1027"]
    },
    "2026_BME_BME": {
        "1": ["BME1101", "MATH1112", "GEMA1001", "GEMA1009", "SI100B", "MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["PHYS1181", "PHYS1111", "CHEM1103", "CHEM1100", "BIO1015", "GEMA1003", "GEMA1010", "GEHA1132", "GEHA1150", "GEHA1302", "CLPE1002"],
        "4": ["BME1104", "BME1109", "BME1110", "BME1302", "GESS1018", "GEHA1123"],
        "5": ["BME1309", "BME1310", "MT1023"],
        "7": ["GESS1027"]
    },
    "2026_ID_SCA": {
        "1": ["SMRT1101", "SMRT1139", "MT1024", "GESS1028", "CPRA1006", "CLEC1003", "CLPS1003", "GEHA1165", "GEHA1173", "CLPE1001"],
        "2": ["SMRT1142", "ENT1127", "SMRT1140", "GEHA1132", "GEHA1150", "GEHA1302", "CLPE1002"],
        "4": ["SMRT1131", "SMRT1141", "SMRT1108", "GESS1018", "GEHA1123"],
        "5": ["SMRT1306", "SMRT1135", "MT1023"],
        "7": ["SMRT1130", "SMRT1136", "GESS1027"]
    }
}

for fname in os.listdir(CURRICULUM_DIR):
    if not fname.endswith(".json") or not fname.startswith("2026_"):
        continue
    fpath = os.path.join(CURRICULUM_DIR, fname)
    with open(fpath, "r", encoding="utf-8") as fp:
        cur = json.load(fp)

    cur_id = cur["curriculum_id"]
    course_lookup = {c["code"]: c for c in cur["all_courses"]}
    
    # Enrich semester roadmap
    seq = STANDARD_SEQUENCES.get(cur_id, {})
    roadmap = cur.get("semester_roadmap", {})
    
    for sem_str, codes in seq.items():
        existing_codes = {c["code"] for c in roadmap.get(sem_str, [])}
        for code in codes:
            if code not in existing_codes:
                c_obj = course_lookup.get(code)
                if c_obj:
                    roadmap.setdefault(sem_str, []).append({
                        "code": c_obj["code"],
                        "name": c_obj["name"],
                        "credit": c_obj["credit"],
                        "is_compulsory": c_obj["is_compulsory"],
                        "module": c_obj["module"],
                        "coursebench": c_obj.get("coursebench")
                    })
                    if int(sem_str) not in c_obj["semesters"]:
                        c_obj["semesters"].append(int(sem_str))
                        c_obj["semesters"].sort()

    cur["semester_roadmap"] = roadmap
    with open(fpath, "w", encoding="utf-8") as fp:
        json.dump(cur, fp, ensure_ascii=False, indent=2)
    print(f"Enriched {fname} with standard semester sequence!")

print("All roadmaps successfully enriched!")
