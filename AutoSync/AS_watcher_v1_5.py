"""
AS_watcher_v1_5.py
CAPS AutoSync 1.5 - 파일 스냅샷 유틸리티

역할:
- 규칙 파일을 읽어들여 감시 대상 디렉터리의 스냅샷을 생성한다.
"""

import os
from pathlib import Path
from typing import Dict
import json


def load_rules(rule_file: Path) -> dict:
    """
    규칙 파일(JSON)을 로드한다.
    """
    with rule_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def should_skip(path: Path, rules: dict) -> bool:
    """
    디렉터리/파일 제외 규칙 및 확장자 필터 적용
    """
    # 디렉터리 제외
    for d in rules.get("exclude_dirs", []):
        if d and d in path.parts:
            return True

    # 파일 제외
    for name in rules.get("exclude_files", []):
        if path.name == name:
            return True

    # 확장자 필터
    exts = rules.get("include_extensions", [])
    if exts and path.suffix not in exts:
        return True

    return False


def build_snapshot(base_dir: Path, rules: dict) -> Dict[str, float]:
    """
    base_dir 이하의 파일들을 훑어서
    {상대경로: mtime} 형태의 dict를 만든다.
    """
    snapshot: Dict[str, float] = {}

    for root, dirs, files in os.walk(base_dir):
        root_path = Path(root)

        # exclude_dirs 처리
        dirs[:] = [d for d in dirs if d not in rules.get("exclude_dirs", [])]

        for file in files:
            file_path = root_path / file
            rel_path = file_path.relative_to(base_dir)

            # 규칙 검사
            if should_skip(rel_path, rules):
                continue

            try:
                mtime = file_path.stat().st_mtime
                snapshot[str(rel_path).replace("\\", "/")] = mtime
            except FileNotFoundError:
                continue

    return snapshot
