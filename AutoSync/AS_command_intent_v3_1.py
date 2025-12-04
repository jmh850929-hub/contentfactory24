"""
AS_command_intent_v3_1.py
AutoSync 3.1 - 노마드 명령 의도 분석 엔진 (Command Intent Layer)

역할:
- 노마드에서 들어온 자연어 명령을 분석해
  "무슨 모듈에", "어떤 작업을", "어느 버전으로" 요청하는지 구조화한다.
- 이 단계에서는 실제 코드를 수정하지 않고, intent 정보만 생성한다.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict


@dataclass
class CommandIntent:
    command_id: str
    raw_text: str
    intent_type: str  # e.g. "create_feature", "update_version", "run_selfcheck", "unknown"
    target_module: str  # "OmegaEngine", "Scheduler", "SafeGuard", "AutoSync", "GLOBAL", "Unknown"
    target_version: Optional[str] = None
    notes: str = ""


def _detect_module(text: str) -> str:
    t = text.lower()

    if "omega" in t or "오메가" in t:
        return "OmegaEngine"
    if "스케줄러" in t or "scheduler" in t:
        return "Scheduler"
    if "세이프가드" in t or "safeguard" in t:
        return "SafeGuard"
    if "오토싱크" in t or "autosync" in t or "autosync" in t:
        return "AutoSync"
    if "전체" in t or "캡스" in t or "caps" in t:
        return "GLOBAL"

    return "Unknown"


def _detect_intent_type(text: str) -> str:
    t = text.lower()

    # 기능 생성 / 추가
    if any(k in t for k in ["기능", "feature", "새로", "만들어", "만들어줘", "추가해", "추가해줘"]):
        return "create_feature"

    # 버전 업 / 업데이트
    if any(k in t for k in ["버전", "version", "올려", "업데이트", "업그레이드"]):
        return "update_version"

    # self-check / 점검 / 테스트
    if any(k in t for k in ["체크", "점검", "self-check", "selfcheck", "검사"]):
        return "run_selfcheck"

    # 실행 / 테스트
    if any(k in t for k in ["실행", "run", "test"]):
        return "run_task"

    return "unknown"


def _detect_version_hint(text: str) -> Optional[str]:
    # 아주 단순한 버전 패턴 감지 (예: "3.5", "v3.5")
    import re

    m = re.search(r"v?\s*(\d+\.\d+)", text.lower())
    if m:
        return m.group(1)
    return None


def analyze_command(command_id: str, text: str) -> Dict:
    """
    단일 명령 문자열을 CommandIntent 구조로 변환한다.
    """
    intent_type = _detect_intent_type(text)
    target_module = _detect_module(text)
    version_hint = _detect_version_hint(text)

    notes_parts = []

    if intent_type == "unknown":
        notes_parts.append("의도를 명확히 파악하지 못했습니다. 텍스트를 조금 더 구체적으로 적어주세요.")
    if target_module == "Unknown":
        notes_parts.append("어떤 모듈(오메가/스케줄러/세이프가드/오토싱크)에 대한 명령인지 불명확합니다.")

    notes = " ".join(notes_parts)

    ci = CommandIntent(
        command_id=command_id,
        raw_text=text,
        intent_type=intent_type,
        target_module=target_module,
        target_version=version_hint,
        notes=notes,
    )
    return asdict(ci)
