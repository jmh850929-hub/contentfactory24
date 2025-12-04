"""
AS_autosync_v3_6.py
AutoSync 3.6 - 패치 확장 모드 (Scheduler 기능 파일까지 생성)

역할:
- v3.1에서 만든 command_plan_v3_1.json 을 읽고
- 각 intent를 v3.6 패치 엔진에 전달하여
  - v3.5 패치 + Scheduler 기능 파일 생성까지 수행
- 상태(state)와 리포트(report)를 남긴다.
"""

from __future__ import annotations

import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from AS_watcher_v1_5 import load_rules, build_snapshot
from AS_patch_engine_v3_6 import process_intent, safe_print


BASE_DIR = Path(__file__).resolve().parent
RULE_FILE = BASE_DIR / "AS_sync_rules_v1_5.json"

STATE_FILE = BASE_DIR / "AS_state_v3_6.json"
REPORT_FILE = BASE_DIR / "AS_report_v3_6.json"

COMMAND_PLAN = BASE_DIR / "generated" / "AS_command_plan_v3_1.json"


def load_json(path: Path, default):
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compute_snapshot_hash(files: Dict[str, float]) -> str:
    items = [f"{p}:{m}" for p, m in sorted(files.items())]
    data = "\n".join(items).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def main():
    start_ts = time.time()
    safe_print("AutoSync v3.6 (Patch-Extended Mode) started.")

    # 1) 규칙 로드 + snapshot (이제는 단순 상태 기록용)
    if not RULE_FILE.exists():
        safe_print("ERROR: AS_sync_rules_v1_5.json not found.")
        return

    rules = load_rules(RULE_FILE)

    snapshot: Dict[str, float] = {}
    for rel in rules.get("watch_paths", []):
        root = (BASE_DIR / rel).resolve()
        if not root.exists():
            continue
        snap = build_snapshot(root, rules)
        prefix = root.name
        for p, m in snap.items():
            snapshot[f"{prefix}/{p}"] = m

    # 2) command plan 로드
    plan = load_json(COMMAND_PLAN, default={"intents": []})
    intents = plan.get("intents", [])

    patches: List[str] = []
    generated_files: List[str] = []

    for intent in intents:
        result = process_intent(intent)
        patches.extend(result.get("patches", []))
        generated_files.extend(result.get("generated", []))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3) state 저장
    state = {
        "version": "3.6",
        "last_run": now,
        "snapshot_hash": compute_snapshot_hash(snapshot),
        "file_count": len(snapshot),
        "intent_count": len(intents),
        "patches": patches,
        "generated_files": generated_files,
    }
    save_json(STATE_FILE, state)

    # 4) report 저장
    report = {
        "version": "3.6",
        "generated_at": now,
        "summary": {
            "intent_count": len(intents),
            "patch_count": len(patches),
            "generated_count": len(generated_files),
            "duration": round(time.time() - start_ts, 3),
        },
        "patches": patches,
        "generated_files": generated_files,
    }
    save_json(REPORT_FILE, report)

    safe_print(f"Intents   : {len(intents)}")
    safe_print(f"Patches   : {len(patches)}")
    safe_print(f"Generated : {len(generated_files)}")
    safe_print("AutoSync v3.6 finished.")


if __name__ == "__main__":
    main()
