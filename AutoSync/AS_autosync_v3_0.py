"""
AS_autosync_v3_0.py
CAPS AutoSync 3.0 - 진화 제안(Sandbox) + 통합 상태 관리

역할:
1) v2.5와 동일하게 전체 스냅샷 생성 및 변경 감지.
2) AutoSync 2.0 Processor로 JSON 정규화/검증 수행.
3) AutoSync 2.5 Integrity 엔진으로 무결성 검사 + risk_score 계산.
4) Evolver v3.0으로 "개선 제안 + 스텁 코드"를 generated/ 폴더에 생성.
5) SafeGuard 상태에 risk_score 반영.
6) AutoSync v3.0 state/report JSON 생성.
"""

import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from AS_watcher_v1_5 import load_rules, build_snapshot
from AS_processor_v2_0 import process_changed_files
from AS_integrity_v2_5 import run_integrity_check
from AS_evolver_v3_0 import generate_proposals


BASE_DIR = Path(__file__).resolve().parent

RULE_FILE = BASE_DIR / "AS_sync_rules_v1_5.json"

STATE_FILE_V30 = BASE_DIR / "AS_state_v3_0.json"
STATE_FILE_V25 = BASE_DIR / "AS_state_v2_5.json"

REPORT_FILE_V30 = BASE_DIR / "AS_report_v3_0.json"
REPORT_FILE_V25 = BASE_DIR / "AS_report_v2_5.json"

SAFEGUARD_STATE = BASE_DIR.parent / "SafeGuard" / "SGD_state.json"


def safe_print(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[AS] {ts} | {msg}")


def load_json(path: Path, default=None):
    if default is None:
        default = {}
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def detect_changes(old: Dict[str, float], new: Dict[str, float]) -> Dict[str, List[str]]:
    added, modified, deleted = [], [], []

    old_keys = set(old.keys())
    new_keys = set(new.keys())

    for k in new_keys - old_keys:
        added.append(k)
    for k in old_keys - new_keys:
        deleted.append(k)
    for k in old_keys & new_keys:
        if old[k] != new[k]:
            modified.append(k)

    return {
        "added": sorted(added),
        "modified": sorted(modified),
        "deleted": sorted(deleted),
    }


def compute_snapshot_hash(files: Dict[str, float]) -> str:
    items = [f"{p}:{m}" for p, m in sorted(files.items())]
    data = "\n".join(items).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def main():
    start_ts = time.time()
    safe_print("AutoSync v3.0 started.")

    # 1) 규칙 로드
    if not RULE_FILE.exists():
        safe_print("ERROR: AS_sync_rules_v1_5.json not found.")
        return

    rules = load_rules(RULE_FILE)
    watch_paths = rules.get("watch_paths", [])
    if not watch_paths:
        safe_print("No watch_paths defined. Nothing to scan.")
        return

    # 2) 스냅샷 생성
    snapshot: Dict[str, float] = {}
    scanned_paths: List[str] = []

    for rel in watch_paths:
        root = (BASE_DIR / rel).resolve()
        if not root.exists():
            safe_print(f"Skip (not found): {root}")
            continue
        scanned_paths.append(str(root))
        snap = build_snapshot(root, rules)
        prefix = root.name
        for path, mtime in snap.items():
            snapshot[f"{prefix}/{path}"] = mtime

    # 3) 이전 상태(v2.5) 로드 + 변경 감지
    prev_state = load_json(STATE_FILE_V25, default={"files": {}, "modules": {}})
    old_files = prev_state.get("files", {})
    changes = detect_changes(old_files, snapshot)

    # 4) AutoSync 2.0 Processor 실행 (JSON 정규화/검증)
    auto_actions, issues = process_changed_files(BASE_DIR.parent, changes)

    # 5) Integrity / RiskScore 계산 (v2.5 엔진 재사용)
    integrity, more_issues = run_integrity_check(snapshot, prev_state)
    risk_score = integrity.get("risk_score", 0)
    issues.extend(more_issues)

    # 6) Evolver v3.0으로 개선 제안 생성 (Sandbox)
    proposals_result = generate_proposals(snapshot, prev_state, load_json(REPORT_FILE_V25, {}))
    proposals = proposals_result.get("proposals", [])
    generated_files = proposals_result.get("generated_files", [])

    # 7) SafeGuard에 risk_score 반영 (기존 필드 유지 + autosync_risk 업데이트)
    sg_state = load_json(SAFEGUARD_STATE, default={})
    sg_state["autosync_risk"] = risk_score
    save_json(SAFEGUARD_STATE, sg_state)

    # 8) 새 state/report 저장 (v3.0)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    snapshot_hash = compute_snapshot_hash(snapshot)

    new_state = {
        "version": "3.0",
        "last_scan": now,
        "snapshot_hash": snapshot_hash,
        "file_count": len(snapshot),
        "modules": prev_state.get("modules", {}),
        "files": snapshot,
        "auto_actions": auto_actions,
        "issues": issues,
        "risk_score": risk_score,
        "integrity": integrity,
        "proposals_count": len(proposals),
        "generated_files": generated_files,
    }
    save_json(STATE_FILE_V30, new_state)

    new_report = {
        "version": "3.0",
        "generated_at": now,
        "source_state_version": "2.5",
        "summary": {
            "total_files": len(snapshot),
            "scanned_paths": scanned_paths,
            "duration_seconds": round(time.time() - start_ts, 3),
        },
        "changes": changes,
        "auto_actions": auto_actions,
        "warnings": issues,
        "risk_score": risk_score,
        "integrity": integrity,
        "proposals": proposals,
        "proposals_generated_files": generated_files,
    }
    save_json(REPORT_FILE_V30, new_report)

    # 9) 로그 출력
    safe_print(f"Added      : {len(changes['added'])}")
    safe_print(f"Modified   : {len(changes['modified'])}")
    safe_print(f"Deleted    : {len(changes['deleted'])}")
    safe_print(f"RiskScore  : {risk_score}")
    safe_print(f"Proposals  : {len(proposals)}")
    safe_print(f"Issues     : {len(issues)}")
    safe_print(f"Total      : {len(snapshot)} files")
    safe_print("AutoSync v3.0 finished.")


if __name__ == "__main__":
    main()
