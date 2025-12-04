"""
AS_patch_engine_v3_6.py
AutoSync 3.6 - 패치 확장 엔진 (Scheduler 기능 파일 생성)

역할:
- v3.5 패치 엔진 결과를 기반으로
  - 생성된 스텁(scheduler_new_feature_v3_5_stub.py)을 Scheduler 폴더로 복사해
    실제 기능 파일(SCH_new_feature_v3_6_stub.py)로 등록한다.
- 기존 파일을 덮어쓰지 않고, 필요한 경우 .bak 백업을 남긴다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import shutil

from AS_patch_engine_v3_5 import process_intent as base_process_intent, safe_print


BASE_DIR = Path(__file__).resolve().parent


def _backup_if_exists(path: Path) -> str | None:
    """
    대상 파일이 이미 존재하면 .bak 백업으로 rename.
    """
    if not path.exists():
        return None
    backup_path = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup_path)
    return str(backup_path)


def process_intent(intent: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    v3.5 패치 엔진 결과 + Scheduler 기능 파일 생성까지 확장.
    """
    # 1) 우선 v3.5 기본 로직 실행
    result = base_process_intent(intent)
    patches: List[str] = result.get("patches", [])
    generated: List[str] = result.get("generated", [])

    intent_type = intent.get("intent_type")
    module = intent.get("target_module")

    # 2) Scheduler용 새 기능 생성 요청일 경우만 확장
    if intent_type == "create_feature" and module == "Scheduler":
        # v3.5에서 만든 스텁 중 하나를 사용
        stub_paths = [Path(p) for p in generated if p.endswith(".py")]
        if stub_paths:
            stub_path = stub_paths[0]

            scheduler_dir = BASE_DIR.parent / "Scheduler"
            scheduler_dir.mkdir(exist_ok=True)

            target_file = scheduler_dir / "SCH_new_feature_v3_6_stub.py"

            backup_info = _backup_if_exists(target_file)
            if backup_info:
                patches.append(f"Backup existing file: {backup_info}")

            shutil.copy2(stub_path, target_file)
            patches.append(f"Copied stub to Scheduler: {target_file.name}")
            generated.append(str(target_file))

            safe_print(f"Scheduler feature stub deployed: {target_file}")

    return {"patches": patches, "generated": generated}
