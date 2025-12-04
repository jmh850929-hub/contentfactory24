"""
AS_integrity_v2_5.py
CAPS AutoSync 2.5 - 무결성(Integrity) 검사 + 위험도(Risk Score) 분석 엔진

역할:
- CAPS 전체 파일 구조의 정상 여부 검사
- OmegaEngine / Scheduler / SafeGuard / AutoSync 간 의존성 확인
- 위험 점수(risk_score) 계산 후 AutoSync 보고서에 반영
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple


def check_required_files(snapshot: Dict[str, float]) -> List[str]:
    """
    각 모듈의 필수 파일이 존재하는지 검사한다.
    """
    required = [
        # OmegaEngine 핵심 엔진 파일
        "OmegaEngine/OMG_main_engine_static_v26.py",
        "OmegaEngine/OMG_engine_gpt_v27.py",
        "OmegaEngine/OMG_version.json",

        # Scheduler 핵심 파일
        "Scheduler/SCH_scheduler_v1_7_1.py",
        "Scheduler/SCH_settings.json",

        # SafeGuard 핵심 파일
        "SafeGuard/SGD_safe_guard_v1_3.py",
        "SafeGuard/SGD_state.json",

        # AutoSync 핵심 파일
        "AutoSync/AS_autosync_v2_0.py",
        "AutoSync/AS_processor_v2_0.py",
    ]

    missing = [path for path in required if path not in snapshot]
    return missing


def compute_risk_score(
    missing_files: List[str],
    issues: List[str],
    snapshot_size: int
) -> int:
    """
    위험 점수를 계산한다 (0~5)
    기준:
        - 필수 파일 누락: +2
        - JSON 파싱 문제: +2
        - snapshot 비정상 감소: +1
    """
    score = 0

    if missing_files:
        score += 2

    if issues:
        score += 2

    if snapshot_size < 50:  # 갑자기 파일 수가 줄어들면 위험
        score += 1

    return min(score, 5)


def run_integrity_check(
    snapshot: Dict[str, float],
    autosync_state: Dict
) -> Tuple[Dict, List[str]]:
    """
    무결성 검사 전체 실행
    """
    issues: List[str] = []

    # 1) 필수 파일 검사
    missing = check_required_files(snapshot)
    if missing:
        issues.append(f"MISSING_FILES:{missing}")

    # 2) JSON 파싱 문제는 autosync_state.issues 에 이미 들어있음
    json_issues = autosync_state.get("issues", [])
    issues.extend(json_issues)

    # 3) 위험 점수 계산
    risk_score = compute_risk_score(missing, json_issues, len(snapshot))

    return {
        "risk_score": risk_score,
        "missing_files": missing,
    }, issues
