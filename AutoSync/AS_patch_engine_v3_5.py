"""
AS_patch_engine_v3_5.py
AutoSync 3.5 - 제한적 코드 자동 수정 엔진

역할:
- 노마드 명령 intent 기반으로 필요한 코드 스텁 생성
- 간단한 구조 변경, 버전 헤더 갱신, config 수정 등 ‘안전한 수정’만 자동 수행
- 모든 수정 이전/이후 버전은 patches/ 에 백업
"""

from __future__ import annotations
from pathlib import Path
import json
import shutil
import re
from typing import Dict, Any


BASE_DIR = Path(__file__).resolve().parent
PATCH_DIR = BASE_DIR / "patches"
PATCH_DIR.mkdir(exist_ok=True)


def safe_print(msg: str):
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[PATCH] {ts} | {msg}")


def backup_file(path: Path):
    """
    원본 파일 백업 (덮어쓰기 이전 반드시 수행)
    """
    if not path.exists():
        return None

    backup_path = PATCH_DIR / f"{path.name}.bak"
    shutil.copy2(path, backup_path)
    return str(backup_path)


def update_version_header(path: Path, new_version: str) -> bool:
    """
    파일 상단에 "# Version: x.x" 형태의 헤더가 있으면 자동 업데이트
    """
    if not path.exists():
        return False

    text = path.read_text(encoding="utf-8")
    new_text = re.sub(
        r"(#\s*Version:\s*)(\d+\.\d+)",
        rf"\g<1>{new_version}",
        text
    )

    if new_text != text:
        backup_file(path)
        path.write_text(new_text, encoding="utf-8")
        return True

    return False


def apply_simple_patch(path: Path, search: str, replace: str) -> bool:
    """
    특정 문자열 교체 기반 간단 패치 (안전한 영역에서만 사용)
    """
    if not path.exists():
        return False

    text = path.read_text(encoding="utf-8")
    if search not in text:
        return False

    backup_file(path)
    new_text = text.replace(search, replace)
    path.write_text(new_text, encoding="utf-8")
    return True


def generate_code_stub(target_module: str, feature_name: str) -> Path:
    """
    명령 기반 새 기능 스텁 생성
    """
    stub_name = f"{target_module.lower()}_{feature_name}_v3_5_stub.py"
    stub_path = PATCH_DIR / stub_name

    code = f'''"""
{stub_name}
AutoSync 3.5 - Generated Feature Stub

이 파일은 AutoSync가 제안한 새 기능 스켈레톤입니다.
실제 적용 전 반드시 검토하세요.
"""

def run_feature():
    print("Feature stub for: {feature_name}")
'''

    stub_path.write_text(code, encoding="utf-8")
    return stub_path


def process_intent(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    단일 intent 처리.
    반환: {'patches': [...], 'generated': [...]}
    """
    results = {"patches": [], "generated": []}

    itype = intent.get("intent_type")
    module = intent.get("target_module")
    version_hint = intent.get("target_version")
    raw = intent.get("raw_text", "")

    # 1) feature 생성 요청
    if itype == "create_feature":
        feature_stub = generate_code_stub(module, "new_feature")
        results["generated"].append(str(feature_stub))
        return results

    # 2) 버전업 요청
    if itype == "update_version" and version_hint:
        # 예: AutoSync/AS_autosync_v3_0.py
        target_file = BASE_DIR.parent / module / f"{module.lower()}_main.py"
        # 위 파일은 실제로 존재할 가능성이 낮음 → AutoSync 3.5는 sandbox 기반
        # 위험 방지를 위해 AutoSync 폴더만 조정 가능하도록 제한
        target_file = BASE_DIR / f"AS_autosync_v3_0.py"
        if target_file.exists():
            ok = update_version_header(target_file, version_hint)
            if ok:
                results["patches"].append(f"Version header updated → {target_file.name}")
        return results

    # 3) self-check 실행 요청 → 별도 처리 없음 (v3.0 stub 있음)
    if itype == "run_selfcheck":
        return results

    return results
