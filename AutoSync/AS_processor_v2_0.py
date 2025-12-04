"""
AS_processor_v2_0.py
CAPS AutoSync 2.0 - 자동 JSON 정규화 / 검증 엔진

역할:
- AutoSync 관련 상태/리포트 JSON을 자동으로 정규화(필수 키 채우기)
- 변경된 기타 JSON 파일의 파싱 여부를 검증하고 결과 로깅
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

# AutoSync state / report에 반드시 있어야 하는 키 목록
REQUIRED_STATE_KEYS = [
    "version",
    "last_scan",
    "snapshot_hash",
    "file_count",
    "modules",
    "files",
    "auto_actions",
    "issues",
]

REQUIRED_REPORT_KEYS = [
    "version",
    "generated_at",
    "source_state_version",
    "summary",
    "changes",
    "unused_candidates",
    "module_health",
    "warnings",
    "errors",
    "auto_actions",
]


def load_json_safe(path: Path):
    """JSON 파일을 안전하게 로드한다. 실패 시 에러 메시지 반환."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, str(e)


def save_json(path: Path, data: dict):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_autosync_state(path: Path, actions: List[dict], issues: List[str]):
    """AutoSync 상태 JSON에 누락된 필드를 자동으로 채운다."""
    data, err = load_json_safe(path)
    if data is None:
        issues.append(f"STATE_PARSE_ERROR:{path.name}:{err}")
        return

    changed = False

    for key in REQUIRED_STATE_KEYS:
        if key not in data:
            if key == "version":
                data[key] = "2.0"
            elif key in ("modules", "files"):
                data[key] = {}
            elif key in ("auto_actions", "issues"):
                data[key] = []
            elif key == "file_count":
                data[key] = len(data.get("files", {}))
            else:
                data[key] = ""
            changed = True

    if changed:
        save_json(path, data)
        actions.append(
            {
                "path": str(path),
                "action": "normalize_state",
                "detail": "Filled missing keys for AutoSync state v2.0",
            }
        )


def normalize_autosync_report(path: Path, actions: List[dict], issues: List[str]):
    """AutoSync 리포트 JSON에 누락된 필드를 자동으로 채운다."""
    data, err = load_json_safe(path)
    if data is None:
        issues.append(f"REPORT_PARSE_ERROR:{path.name}:{err}")
        return

    changed = False

    for key in REQUIRED_REPORT_KEYS:
        if key not in data:
            if key == "version":
                data[key] = "2.0"
            elif key == "summary":
                data[key] = {
                    "total_files": 0,
                    "scanned_paths": [],
                    "duration_seconds": 0.0,
                }
            elif key == "changes":
                data[key] = {"added": [], "modified": [], "deleted": []}
            elif key == "module_health":
                data[key] = {}
            elif key in ("warnings", "errors", "auto_actions", "unused_candidates"):
                data[key] = []
            else:
                data[key] = ""
            changed = True

    if changed:
        save_json(path, data)
        actions.append(
            {
                "path": str(path),
                "action": "normalize_report",
                "detail": "Filled missing keys for AutoSync report v2.0",
            }
        )


def process_changed_files(base_dir: Path, changed_paths: Dict[str, List[str]]) -> Tuple[List[dict], List[str]]:
    """
    변경된 파일 목록을 입력받아
    - AutoSync 관련 JSON은 정규화
    - 기타 JSON은 파싱 검증
    """
    actions: List[dict] = []
    issues: List[str] = []

    autosync_state_candidates = [
        "AutoSync/AS_state_v1_5.json",
        "AutoSync/AS_state_v2_0.json",
    ]
    autosync_report_candidates = [
        "AutoSync/AS_report_v1_5.json",
        "AutoSync/AS_report_v2_0.json",
    ]

    targets = changed_paths.get("modified", []) + changed_paths.get("added", [])

    for rel in targets:
        full = base_dir / rel
        if not full.exists():
            continue

        norm_rel = rel.replace("\\", "/")

        if norm_rel in autosync_state_candidates:
            normalize_autosync_state(full, actions, issues)

        elif norm_rel in autosync_report_candidates:
            normalize_autosync_report(full, actions, issues)

        elif norm_rel.endswith(".json"):
            # 일반 JSON 파일은 파싱만 검증
            data, err = load_json_safe(full)
            if data is None:
                issues.append(f"JSON_PARSE_ERROR:{norm_rel}:{err}")
            else:
                actions.append(
                    {
                        "path": str(full),
                        "action": "validate_json",
                        "detail": "JSON parsed successfully",
                    }
                )

    return actions, issues
