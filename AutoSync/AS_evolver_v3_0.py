"""
AS_evolver_v3_0.py
CAPS AutoSync 3.0 - 진화 제안 엔진(Evolver, Sandbox Mode)

역할:
- AutoSync 2.5 상태/리포트 + 최신 스냅샷을 분석해
  "어떻게 개선하면 좋을지" 제안(proposals)을 생성한다.
- 실제 엔진/스케줄러 코드는 절대 수정하지 않고,
  AutoSync/generated/ 아래에 샌드박스용 스텁 코드와 제안 JSON만 생성한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "generated"


def safe_print(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[EVOLVER] {ts} | {msg}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_proposals(
    snapshot: Dict[str, float],
    autosync_state: Dict[str, Any],
    autosync_report: Dict[str, Any],
) -> Dict[str, Any]:
    """
    snapshot / state / report를 기반으로 개선 제안 목록 생성.
    실제 로직은 단순하지만, 구조는 확장 가능하게 설계한다.
    """
    proposals: List[Dict[str, Any]] = []
    generated_files: List[str] = []

    ensure_dir(GENERATED_DIR)

    risk_score = autosync_state.get("risk_score", 0)
    modules = autosync_state.get("modules", {})

    # 1) 전역 위험도 기반 제안
    if risk_score > 0:
        proposals.append(
            {
                "id": "global_risk_investigation",
                "module": "GLOBAL",
                "level": "HIGH",
                "title": "RiskScore가 0이 아님",
                "description": (
                    f"현재 AutoSync risk_score={risk_score} 입니다. "
                    "SafeGuard 로그 및 최근 변경 파일을 우선 점검하는 것이 좋습니다."
                ),
                "suggested_actions": [
                    "SafeGuard/SGD_log.txt 최근 항목 확인",
                    "변경된 파일(changes.modified) 코드 리뷰",
                ],
            }
        )

    # 2) 모듈별 Self-Check 스텁 코드 제안
    for module_name, info in modules.items():
        file_count = info.get("file_count", 0)
        last_mtime_str = info.get("last_mtime_str", "")

        proposal_id = f"{module_name.lower()}_selfcheck"
        stub_name = f"{module_name.lower()}_selfcheck_stub_v3_0.py"
        stub_path = GENERATED_DIR / stub_name

        # 간단한 스텁 코드 생성 (이미 존재하면 덮어쓰지 않고 유지해도 되지만,
        # 여기서는 항상 최신 버전으로 덮어쓴다.)
        stub_code = f'''"""
{stub_name}
AutoSync v3.0 - {module_name}용 Self-Check 스텁

이 파일은 AutoSync가 제안한 샘플 코드이며,
실제 시스템에 바로 연결되지 않습니다.

필요 시 내용을 채운 뒤, 수동으로 해당 모듈 폴더로 옮겨서 사용하세요.
"""

def run_self_check():
    # TODO: {module_name} 내부 파일 구조 / 설정값 등을 점검하는 코드를 작성하세요.
    # 예시:
    # - 필수 JSON 키 존재 여부
    # - 파일명 패턴 검증
    # - 설정값 범위 검사 등
    print("Self-check for module: {module_name} (stub)")
'''

        stub_path.write_text(stub_code, encoding="utf-8")
        generated_files.append(str(stub_path))

        proposals.append(
            {
                "id": proposal_id,
                "module": module_name,
                "level": "INFO",
                "title": f"{module_name} 모듈용 Self-Check 스텁 생성",
                "description": (
                    f"{module_name} 모듈에 대해 기본적인 구조/설정 점검을 수행할 수 있는 "
                    f"self-check 스텁 코드를 generated/{stub_name} 에 생성했습니다. "
                    "필요 시 내용을 채워서 사용하면 됩니다."
                ),
                "suggested_actions": [
                    f"generated/{stub_name} 내용을 검토하고 필요한 검사를 구현한다.",
                    f"{module_name} 폴더로 옮겨서 스케줄러/테스트 스크립트에서 호출하도록 연결한다.",
                ],
            }
        )

    # 3) 향후 확장용: snapshot 기반 간단 제안 (현재는 구조만)
    total_files = len(snapshot)
    proposals.append(
        {
            "id": "snapshot_summary",
            "module": "GLOBAL",
            "level": "INFO",
            "title": "현재 CAPS 스냅샷 요약",
            "description": f"현재 CAPS 전체 파일 수는 {total_files} 개입니다.",
            "suggested_actions": [],
        }
    )

    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "risk_score": risk_score,
        "proposals": proposals,
        "generated_files": generated_files,
    }

    # 제안 전체를 JSON으로도 저장
    proposals_path = GENERATED_DIR / "AS_proposals_v3_0.json"
    save_json(proposals_path, result)
    generated_files.append(str(proposals_path))

    safe_print(
        f"Generated {len(proposals)} proposals and {len(generated_files)} files "
        "in sandbox mode."
    )

    return result


def generate_proposals(
    snapshot: Dict[str, float],
    autosync_state: Dict[str, Any],
    autosync_report: Dict[str, Any],
) -> Dict[str, Any]:
    """
    AutoSync v3.0에서 호출하는 진입점.
    """
    return build_proposals(snapshot, autosync_state, autosync_report)
