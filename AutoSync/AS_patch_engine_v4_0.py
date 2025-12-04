"""
AS_patch_engine_v4_0.py
AutoSync 4.0 - Full Patch Engine
(코드 자동 수정 + 버전업 + 시뮬레이션 + Safe-Patch)

역할:
- AutoSync 3.1 Intent 기반으로 ‘실제 코드’를 수정하는 단계.
- 적용 전에 sandbox에 복사하여 테스트 후 실제 반영.
- 위험한 패치는 BLOCK 처리.

자동 수정 기능은 ‘안전 영역’만 허용:
- version header 갱신
- 특정 함수 덧붙이기
- 파일 끝에 추가 함수 붙이기
- config 내부 key 업데이트
"""

from __future__ import annotations
import json, shutil, re
from pathlib import Path
from typing import Dict, Any
import subprocess


BASE = Path(__file__).resolve().parent
PATCH_DIR = BASE / "patches"
SANDBOX = BASE / "sandbox"

PATCH_DIR.mkdir(exist_ok=True)
SANDBOX.mkdir(exist_ok=True)


def safe_print(msg: str):
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[PATCH-4.0] {ts} | {msg}")


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)
    return backup


def sandbox_copy(path: Path) -> Path:
    """
    실제 파일을 sandbox로 복사해놓고,
    수정은 sandbox 파일에서 먼저 수행한다.
    """
    target = SANDBOX / path.name
    shutil.copy2(path, target)
    return target


def update_version_header(path: Path, new: str) -> bool:
    """
    # Version: x.x  →  # Version: new
    """
    if not path.exists():
        return False
    txt = path.read_text(encoding="utf-8")
    new_txt = re.sub(r"(#\s*Version:\s*)(\d+\.\d+)", rf"\1{new}", txt)
    if new_txt != txt:
        path.write_text(new_txt, encoding="utf-8")
        return True
    return False


def append_function(path: Path, func_name: str, code: str) -> bool:
    """
    파일 끝에 함수 블록을 추가한다.
    """
    if not path.exists():
        return False
    original = path.read_text(encoding="utf-8")
    addition = f"\n\ndef {func_name}():\n" + "\n".join([f"    {line}" for line in code.splitlines()])
    new_txt = original + addition
    path.write_text(new_txt, encoding="utf-8")
    return True


def syntax_check(path: Path) -> list:
    issues = []
    try:
        src = path.read_text(encoding="utf-8")
        compile(src, str(path), "exec")
    except SyntaxError as e:
        issues.append(f"SYNTAX_ERROR:{e.msg} at line {e.lineno}")
    except Exception as e:
        issues.append(f"COMPILE_ERROR:{e}")
    return issues


def simulate_patch(path: Path) -> bool:
    """
    sandbox 파일을 실제로 `python -m py_compile` 로 검증해본다.
    """
    try:
        res = subprocess.run(
            ["python", "-m", "py_compile", str(path)],
            capture_output=True, text=True
        )
        return res.returncode == 0
    except Exception:
        return False


def apply_safe_patch(target: Path, changes: Dict[str, Any]):
    """
    safe patching:
    - version header update
    - append new function
    """
    patched = []

    # 1) version header
    if "version" in changes:
        new_ver = changes["version"]
        ok = update_version_header(target, new_ver)
        if ok:
            patched.append(f"Version header updated → {target.name}")

    # 2) append function
    if "new_function" in changes:
        func_name = changes["new_function"]["name"]
        code = changes["new_function"]["code"]
        ok = append_function(target, func_name, code)
        if ok:
            patched.append(f"Function added → {func_name} in {target.name}")

    return patched


def full_patch(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    AutoSync 4.0 가장 중요한 함수.
    intent → 실제 코드 패치.
    """
    results = {"status": "OK", "patched": [], "errors": []}

    itype = intent.get("intent_type")
    module = intent.get("target_module")
    ver_hint = intent.get("target_version")

    # 현재 버전에서 실제 패치 가능한 대상(안전 영역)
    if module == "Scheduler":
        target = BASE.parent / "Scheduler" / "SCH_new_feature_v3_6_stub.py"
    else:
        return {"status": "SKIP", "patched": [], "errors": []}

    # target 존재 확인
    if not target.exists():
        return {"status": "ERROR", "patched": [], "errors": [f"Target file not found: {target}"]}

    # 1) sandbox copy
    sfile = sandbox_copy(target)

    changes = {}

    # version update
    if itype == "update_version" and ver_hint:
        changes["version"] = ver_hint

    # feature append
    if itype == "create_feature":
        changes["new_function"] = {
            "name": "auto_generated_feature",
            "code": "print('AutoSync 4.0 generated feature running')"
        }

    # 아무런 변화 없으면 skip
    if not changes:
        return {"status": "NOCHANGE", "patched": [], "errors": []}

    # 2) sandbox에 패치
    patched = apply_safe_patch(sfile, changes)

    # 3) syntax check
    issues = syntax_check(sfile)
    if issues:
        return {"status": "BLOCK", "patched": [], "errors": issues}

    # 4) simulate
    if not simulate_patch(sfile):
        return {"status": "BLOCK", "patched": [], "errors": ["SIMULATION_FAILED"]}

    # 5) 실제 적용
    backup_file(target)
    shutil.copy2(sfile, target)

    return {"status": "APPLIED", "patched": patched, "errors": []}
