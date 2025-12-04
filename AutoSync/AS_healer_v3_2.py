"""
AS_healer_v3_2.py
AutoSync 3.2 - Self-Healing Engine (JSON-Level Auto Fixes)

역할:
- JSON 파일 파싱 오류 자동 복구
- 누락된 필드 보정
- 타입 오류 보정
- 상태 파일(SGD_state.json, SCH_settings.json) 기본값 복구
- 스냅샷/실제 파일 불일치 자동 정리

이 단계에서는 Python 코드(.py)는 절대 수정하지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any


# 기본값 셋
DEFAULT_SGD_STATE = {
    "autosync_risk": 0,
    "status": "GREEN",
}

DEFAULT_SCH_SETTINGS = {
    "enabled": True,
    "mode": "normal",
    "random_seed": 42,
}


def load_json_safe(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, str(e)


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fix_missing_fields(data: Dict, required: Dict[str, Any]) -> Tuple[Dict, bool]:
    changed = False
    for key, default_value in required.items():
        if key not in data:
            data[key] = default_value
            changed = True
    return data, changed


def heal_json_file(path: Path, required_fields: Dict[str, Any]) -> Tuple[bool, str]:
    """
    JSON 파일을 읽어보고:
    - 파싱 오류 있으면 복구
    - 누락 필드 보정
    """
    data, err = load_json_safe(path)
    if data is None:
        # 파싱 실패 → 기본값으로 복구
        save_json(path, required_fields)
        return True, f"JSON_PARSE_FIXED:{path.name}"

    # 누락 필드 보정
    data, changed = fix_missing_fields(data, required_fields)
    if changed:
        save_json(path, data)
        return True, f"JSON_FIELDS_FIXED:{path.name}"

    return False, ""


def heal_snapshot(snapshot: Dict[str, float], base_dir: Path) -> Tuple[Dict, List[str]]:
    """
    스냅샷에는 있는데 실제 파일이 없는 항목 제거 (오류 상태 방지)
    """
    issues = []
    cleaned = {}

    for rel, mtime in snapshot.items():
        full = base_dir / rel
        if not full.exists():
            issues.append(f"SNAPSHOT_MISSING_FILE:{rel}")
            continue
        cleaned[rel] = mtime

    return cleaned, issues


def run_healer(base_dir: Path, snapshot: Dict[str, float]) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Self-Healing 전체 실행
    """
    actions: Dict[str, List[str]] = {"fixed": [], "warnings": []}
    issues: List[str] = []

    # 대상 파일들
    sg_state_path = base_dir.parent / "SafeGuard" / "SGD_state.json"
    sch_settings_path = base_dir.parent / "Scheduler" / "SCH_settings.json"

    # 1) SafeGuard 상태 복구
    fixed, msg = heal_json_file(sg_state_path, DEFAULT_SGD_STATE)
    if fixed:
        actions["fixed"].append(msg)

    # 2) Scheduler 설정 복구
    fixed, msg = heal_json_file(sch_settings_path, DEFAULT_SCH_SETTINGS)
    if fixed:
        actions["fixed"].append(msg)

    # 3) Snapshot 정리
    healed_snapshot, snapshot_issues = heal_snapshot(snapshot, base_dir.parent)
    issues.extend(snapshot_issues)

    return actions, issues, healed_snapshot
