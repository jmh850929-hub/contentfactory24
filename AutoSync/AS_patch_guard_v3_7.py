"""
AS_patch_guard_v3_7.py
AutoSync 3.7 - Patch Safety Guard (검증 전용, 코드 수정 없음)

역할:
- AutoSync 3.5/3.6에서 생성된 패치/스텁들을 검사한다.
- .py 파일을 compile()로 문법 검증하고,
  위험한 패턴(예: os.system, subprocess 등)을 간단히 필터링한다.
- 어떤 패치가 "SAFE" / "WARN" / "BLOCK" 인지 태그를 붙여준다.
- 실제 코드 수정/삭제는 절대 하지 않는다.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any


BASE_DIR = Path(__file__).resolve().parent
PATCH_DIR = BASE_DIR / "patches"
SCHEDULER_DIR = BASE_DIR.parent / "Scheduler"
OMEGA_DIR = BASE_DIR.parent / "OmegaEngine"
AUTOSYNC_DIR = BASE_DIR
SAFEGUARD_DIR = BASE_DIR.parent / "SafeGuard"


DANGEROUS_PATTERNS = [
    "os.system(",
    "subprocess.Popen",
    "subprocess.call",
    "eval(",
    "exec(",
    "open('/etc",
    "rm -rf",
]


def safe_print(msg: str) -> None:
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[GUARD] {ts} | {msg}")


def _categorize_file(path: Path) -> str:
    """
    파일이 어느 모듈에 속했는지 간단히 태그 지정.
    """
    try:
        p = path.resolve()
    except FileNotFoundError:
        return "Unknown"

    if str(p).startswith(str(SCHEDULER_DIR)):
        return "Scheduler"
    if str(p).startswith(str(OMEGA_DIR)):
        return "OmegaEngine"
    if str(p).startswith(str(SAFEGUARD_DIR)):
        return "SafeGuard"
    if str(p).startswith(str(AUTOSYNC_DIR)):
        return "AutoSync"
    if str(p).startswith(str(PATCH_DIR)):
        return "PatchSandbox"
    return "Unknown"


def validate_python_syntax(path: Path) -> List[str]:
    """
    .py 파일을 compile()로 문법 검증.
    에러가 있으면 메시지 리스트로 반환.
    """
    issues: List[str] = []
    try:
        src = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        issues.append("FILE_NOT_FOUND")
        return issues
    except Exception as e:
        issues.append(f"READ_ERROR:{e}")
        return issues

    try:
        compile(src, str(path), "exec")
    except SyntaxError as e:
        issues.append(f"SYNTAX_ERROR:{e.msg} at line {e.lineno}")
    except Exception as e:
        issues.append(f"COMPILE_ERROR:{e}")

    # 위험 패턴 검사
    for pat in DANGEROUS_PATTERNS:
        if pat in src:
            issues.append(f"DANGEROUS_PATTERN:{pat}")

    return issues


def guard_files(paths: List[str]) -> Dict[str, Any]:
    """
    주어진 경로 리스트에 대해 안전성 검사 실행.
    반환:
        {
          'results': [
            {'path': ..., 'module': ..., 'status': 'SAFE/WARN/BLOCK', 'issues': [...]},
            ...
          ],
          'summary': {...}
        }
    """
    results: List[Dict[str, Any]] = []
    safe_count = 0
    warn_count = 0
    block_count = 0

    for p_str in paths:
        p = Path(p_str)
        module = _categorize_file(p)
        issues = []

        if p.suffix == ".py":
            issues = validate_python_syntax(p)
        else:
            # .py가 아니면 현재는 단순 통과
            issues = []

        if not issues:
            status = "SAFE"
            safe_count += 1
        else:
            # 위험 패턴이나 치명적 오류 있으면 BLOCK, 그 외는 WARN
            if any(i.startswith("DANGEROUS_PATTERN") for i in issues):
                status = "BLOCK"
                block_count += 1
            elif any(i.startswith(("SYNTAX_ERROR", "COMPILE_ERROR")) for i in issues):
                status = "WARN"
                warn_count += 1
            else:
                status = "WARN"
                warn_count += 1

        results.append(
            {
                "path": str(p),
                "module": module,
                "status": status,
                "issues": issues,
            }
        )

    summary = {
        "total": len(paths),
        "safe": safe_count,
        "warn": warn_count,
        "block": block_count,
    }

    return {"results": results, "summary": summary}
