"""
AS_autosync_v3_7.py
AutoSync 3.7 - Patch Safety Validation Mode

역할:
- AutoSync 3.6에서 만든 state_v3_6.json을 읽어
  patches / generated_files 목록을 가져온다.
- AS_patch_guard_v3_7.guard_files()로 안전성 검사 실행.
- 결과를 AS_state_v3_7.json / AS_report_v3_7.json 에 저장한다.
- 실제 코드 수정/삭제는 아무것도 하지 않는다. (검증 전용)
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

from AS_patch_guard_v3_7 import guard_files, safe_print


BASE_DIR = Path(__file__).resolve().parent

STATE_V36 = BASE_DIR / "AS_state_v3_6.json"
STATE_V37 = BASE_DIR / "AS_state_v3_7.json"
REPORT_V37 = BASE_DIR / "AS_report_v3_7.json"


def load_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    safe_print("AutoSync v3.7 (Patch Safety Validation) started.")

    # 1) v3.6 state 로드
    v36 = load_json(STATE_V36, default={"patches": [], "generated_files": []})
    patches: List[str] = v36.get("patches", [])
    generated_files: List[str] = v36.get("generated_files", [])

    # 검사 대상 파일: 패치 설명 문자열 중 실제 경로가 들어간 경우 + generated_files
    # 여기서는 generated_files 리스트를 우선적으로 검사
    target_paths: List[str] = []
    for p in generated_files:
        if isinstance(p, str):
            target_paths.append(p)

    if not target_paths:
        safe_print("No generated files found from v3.6 state. Nothing to validate.")
        results = {"results": [], "summary": {"total": 0, "safe": 0, "warn": 0, "block": 0}}
    else:
        # 2) 패치 안전성 검사
        results = guard_files(target_paths)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3) state_v3_7 저장
    state_v37: Dict[str, Any] = {
        "version": "3.7",
        "last_run": now,
        "validated_files": target_paths,
        "validation_summary": results.get("summary", {}),
        "validation_results": results.get("results", []),
    }
    save_json(STATE_V37, state_v37)

    # 4) report_v3_7 저장
    report_v37: Dict[str, Any] = {
        "version": "3.7",
        "generated_at": now,
        "summary": results.get("summary", {}),
        "details": results.get("results", []),
    }
    save
