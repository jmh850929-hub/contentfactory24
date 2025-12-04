"""
AS_autosync_v4_0.py
AutoSync 4.0 - Full Autonomous Patch Engine

역할:
- command_plan_v3_1.json 의 intent 전체를 순회
- patch_engine_v4_0.full_patch()로 처리
- safe / warn / block 기반 결과 저장
- final state/report 생성
"""

from __future__ import annotations

import json, time, hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from AS_patch_engine_v4_0 import full_patch, safe_print


BASE = Path(__file__).resolve().parent
PLAN = BASE / "generated" / "AS_command_plan_v3_1.json"
STATE = BASE / "AS_state_v4_0.json"
REPORT = BASE / "AS_report_v4_0.json"


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


def save_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compute_hash():
    h = hashlib.sha256(str(time.time()).encode()).hexdigest()
    return h[:16]


def main():
    safe_print("AutoSync v4.0 started.")

    plan = load_json(PLAN, default={"intents": []})
    intents: List[Dict[str, Any]] = plan.get("intents", [])

    applied = []
    blocked = []
    skipped = []

    for intent in intents:
        result = full_patch(intent)
        status = result.get("status")

        if status == "APPLIED":
            applied.append(result)
        elif status == "BLOCK":
            blocked.append(result)
        else:
            skipped.append(result)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    state = {
        "version": "4.0",
        "last_run": now,
        "hash": compute_hash(),
        "applied_count": len(applied),
        "blocked_count": len(blocked),
        "skipped_count": len(skipped),
        "applied": applied,
        "blocked": blocked,
        "skipped": skipped,
    }
    save_json(STATE, state)

    report = {
        "version": "4.0",
        "generated_at": now,
        "summary": {
            "applied": len(applied),
            "blocked": len(blocked),
            "skipped": len(skipped),
        },
        "details": {
            "applied": applied,
            "blocked": blocked,
            "skipped": skipped,
        }
    }
    save_json(REPORT, report)

    safe_print(f"Applied patches : {len(applied)}")
    safe_print(f"Blocked patches : {len(blocked)}")
    safe_print(f"Skipped patches : {len(skipped)}")
    safe_print("AutoSync v4.0 finished.")


if __name__ == "__main__":
    main()
