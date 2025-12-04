"""
AS_autosync_v3_2.py
AutoSync 3.2 - Self-Healing 1단계 + 명령 분석 + 무결성

역할:
1) snapshot 생성
2) 변경 감지
3) AutoSync 2.0 processor로 JSON 정규화
4) AutoSync 2.5 integrity 검사
5) AutoSync 3.2 healer로 JSON/상태 파일 자동 복구
6) snapshot 정리
7) AutoSync 3.1 command intent 결과와 병합하여 state/report 생성

이 단계는 파일(.py) 코드를 절대 수정하지 않는다.
"""

import time, json, hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from AS_watcher_v1_5 import load_rules, build_snapshot
from AS_processor_v2_0 import process_changed_files
from AS_integrity_v2_5 import run_integrity_check
from AS_healer_v3_2 import run_healer


BASE_DIR = Path(__file__).resolve().parent

RULE_FILE = BASE_DIR / "AS_sync_rules_v1_5.json"

STATE_FILE_V32 = BASE_DIR / "AS_state_v3_2.json"
REPORT_FILE_V32 = BASE_DIR / "AS_report_v3_2.json"

COMMAND_PLAN = BASE_DIR / "generated" / "AS_command_plan_v3_1.json"


def safe_print(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[AS] {ts} | {msg}")


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


def detect_changes(old: Dict[str, float], new: Dict[str, float]):
    added, modified, deleted = [], [], []
    oldk, newk = set(old.keys()), set(new.keys())

    added.extend(newk - oldk)
    deleted.extend(oldk - newk)
    for k in oldk & newk:
        if old[k] != new[k]:
            modified.append(k)

    return {
        "added": sorted(added),
        "modified": sorted(modified),
        "deleted": sorted(deleted),
    }


def compute_snapshot_hash(files: Dict[str, float]):
    items = [f"{p}:{m}" for p, m in sorted(files.items())]
    data = "\n".join(items).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def main():
    start = time.time()
    safe_print("AutoSync v3.2 (Self-Healing mode) started.")

    # 1) 규칙 로드
    if not RULE_FILE.exists():
        safe_print("ERROR: sync rules missing.")
        return
    rules = load_rules(RULE_FILE)

    # 2) snapshot
    snapshot: Dict[str, float] = {}
    scanned = []

    for rel in rules.get("watch_paths", []):
        root = (BASE_DIR / rel).resolve()
        if not root.exists():
            continue
        scanned.append(str(root))
        snap = build_snapshot(root, rules)
        prefix = root.name
        for p, m in snap.items():
            snapshot[f"{prefix}/{p}"] = m

    # 이전 상태가 없으면 빈 dict
    prev_state = load_json(STATE_FILE_V32, default={"files": {}})
    changes = detect_changes(prev_state.get("files", {}), snapshot)

    # 3) v2.0 processor (JSON 정규화)
    auto_actions, processor_issues = process_changed_files(BASE_DIR.parent, changes)

    # 4) v2.5 integrity
    integrity, integrity_issues = run_integrity_check(snapshot, prev_state)
    risk = integrity.get("risk_score", 0)

    # 5) v3.2 healer (Self-Healing)
    heal_actions, heal_issues, healed_snapshot = run_healer(BASE_DIR, snapshot)

    # 6) snapshot 덮어쓰기
    snapshot = healed_snapshot

    # 7) 3.1 command plan 로드
    command_plan = load_json(COMMAND_PLAN, default={"intents": []})

    # 모든 issue 통합
    issues = processor_issues + integrity_issues + heal_issues

    # 8) state/report 생성
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_state = {
        "version": "3.2",
        "last_scan": now,
        "file_count": len(snapshot),
        "snapshot_hash": compute_snapshot_hash(snapshot),
        "auto_actions": auto_actions,
        "heal_actions": heal_actions,
        "issues": issues,
        "risk_score": risk,
        "integrity": integrity,
        "command_intents": command_plan.get("intents", []),
        "changes": changes,
    }

    save_json(STATE_FILE_V32, new_state)

    new_report = {
        "version": "3.2",
        "generated_at": now,
        "summary": {
            "total_files": len(snapshot),
            "duration": round(time.time() - start, 3),
            "scan_paths": scanned,
        },
        "risk_score": risk,
        "changes": changes,
        "heal_actions": heal_actions,
        "issues": issues,
        "command_intents": command_plan.get("intents", []),
    }

    save_json(REPORT_FILE_V32, new_report)

    safe_print(f"Added      : {len(changes['added'])}")
    safe_print(f"Modified   : {len(changes['modified'])}")
    safe_print(f"Deleted    : {len(changes['deleted'])}")
    safe_print(f"HealFix    : {len(heal_actions['fixed'])}")
    safe_print(f"Issues     : {len(issues)}")
    safe_print(f"RiskScore  : {risk}")
    safe_print(f"Total      : {len(snapshot)} files")
    safe_print("AutoSync v3.2 finished.")


if __name__ == "__main__":
    main()
