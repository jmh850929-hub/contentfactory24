"""
AS_autosync_v3_5.py
AutoSync 3.5 - 명령 기반 코드 생성/부분 자동 수정 (안전 모드)

역할:
1) 스냅샷 생성
2) AutoSync 3.1 command intent 로드
3) intent 기반 제한적 코드 생성 + 패치
4) 모든 패치 백업 (patches/)
5) state/report 저장
"""

import time, json, hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from AS_watcher_v1_5 import build_snapshot, load_rules
from AS_patch_engine_v3_5 import process_intent, safe_print, PATCH_DIR


BASE_DIR = Path(__file__).resolve().parent
RULE_FILE = BASE_DIR / "AS_sync_rules_v1_5.json"

STATE_FILE = BASE_DIR / "AS_state_v3_5.json"
REPORT_FILE = BASE_DIR / "AS_report_v3_5.json"

COMMAND_PLAN = BASE_DIR / "generated" / "AS_command_plan_v3_1.json"


def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except:
        return default
    return default


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compute_snapshot_hash(files: Dict[str, float]):
    items = [f"{p}:{m}" for p, m in sorted(files.items())]
    data = "\n".join(items).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def main():
    start = time.time()
    safe_print("AutoSync v3.5 (Code Patch Mode) started.")

    # 1) 규칙 로드
    rules = load_rules(RULE_FILE)

    # 2) snapshot
    snapshot = {}
    for rel in rules.get("watch_paths", []):
        root = (BASE_DIR / rel).resolve()
        if not root.exists():
            continue
        snap = build_snapshot(root, rules)
        prefix = root.name
        for p, m in snap.items():
            snapshot[f"{prefix}/{p}"] = m

    # 3) command plan 로드
    plan = load_json(COMMAND_PLAN, default={"intents": []})
    intents = plan.get("intents", [])

    patches = []
    generated_files = []

    for intent in intents:
        result = process_intent(intent)
        patches.extend(result.get("patches", []))
        generated_files.extend(result.get("generated", []))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 4) 상태 저장
    state = {
        "version": "3.5",
        "last_run": now,
        "snapshot_hash": compute_snapshot_hash(snapshot),
        "intent_count": len(intents),
        "patches": patches,
        "generated_files": generated_files,
        "patch_dir": str(PATCH_DIR),
    }
    save_json(STATE_FILE, state)

    # 5) 리포트 저장
    report = {
        "version": "3.5",
        "generated_at": now,
        "summary": {
            "intent_count": len(intents),
            "patches": len(patches),
            "generated": len(generated_files),
        },
        "patches": patches,
        "generated_files": generated_files,
    }
    save_json(REPORT_FILE, report)

    safe_print(f"Intents   : {len(intents)}")
    safe_print(f"Patches   : {len(patches)}")
    safe_print(f"Generated : {len(generated_files)}")
    safe_print("AutoSync v3.5 finished.")


if __name__ == "__main__":
    main()
