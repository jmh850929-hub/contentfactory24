from __future__ import annotations
import json
import subprocess
from pathlib import Path
from datetime import datetime

# SafeGuard 1.3 (OmegaEngine v2.7 대응)
# - StaticEngine v26 실행 지원
# - 신호등 연동(GREEN/YELLOW/RED)
# - 연속 실패 관리
# - Safe State (FAIL 누적 시 차단)
# - Scheduler가 참조하는 SGD_state.json 구조 강화
# - AutoResume 지원

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "SGD_config.json"
STATE_PATH = BASE_DIR / "SGD_state.json"


# ---------------------------------------------
# 공용 JSON 로드/저장
# ---------------------------------------------
def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------
# 로그 기록
# ---------------------------------------------
def log(msg: str, cfg: dict) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[SafeGuard] {ts} | {msg}"
    print(line)

    log_file = cfg.get("log_file", "SGD_log.txt")
    log_path = BASE_DIR / log_file

    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------------------------------------
# StaticEngine 실행
# ---------------------------------------------
def run_static_engine(cfg: dict) -> int:
    """
    StaticEngine v26 실행
    """
    engine_cmd = cfg.get(
        "engine_cmd",
        ["python", "OMG_main_engine_static_v26.py"],
    )
    engine_cwd = Path(cfg.get("engine_cwd", r"C:\A1-M2\OmegaEngine"))

    log(f"Running StaticEngine: {engine_cmd} (cwd={engine_cwd})", cfg)

    try:
        proc = subprocess.run(
            engine_cmd,
            cwd=engine_cwd,
            capture_output=False,
            check=False,
        )
        rc = proc.returncode
        log(f"StaticEngine exited with code {rc}", cfg)
        return rc

    except Exception as e:
        log(f"StaticEngine launch error: {e}", cfg)
        return 999


# ---------------------------------------------
# 메인 로직
# ---------------------------------------------
def main():
    # 0) config/state 로드
    cfg_default = {
        "max_failures": 3,
        "engine_cmd": ["python", "OMG_main_engine_static_v26.py"],
        "engine_cwd": r"C:\A1-M2\OmegaEngine",
        "log_file": "SGD_log.txt",
        "auto_resume": True,
    }
    cfg = load_json(CONFIG_PATH, cfg_default)

    state_default = {
        "safe_state": False,
        "consecutive_failures": 0,
        "last_status": None,
        "last_error": None,
        "last_run_at": None,
        "last_success_at": None,
        "state": "UNKNOWN",      # Scheduler 1.7 신호등용
        "failures": 0,           # Scheduler 1.7 신호등용
        "warnings": 0            # Scheduler 1.7 신호등용
    }
    state = load_json(STATE_PATH, state_default)

    # 1) Safe State 여부 확인
    if state.get("safe_state", False):
        msg = "SAFE STATE → 실행 차단"
        if cfg.get("auto_resume", False):
            msg += " (auto_resume=True → 1회 시도)"
        log(msg, cfg)

        if not cfg.get("auto_resume", False):
            # 완전 차단
            state["state"] = "ERROR"
            save_json(STATE_PATH, state)
            return

    # 2) StaticEngine 실행
    rc = run_static_engine(cfg)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3) 정상/오류 분기
    if rc == 0:
        # 성공
        state["last_status"] = "success"
        state["last_error"] = None
        state["last_run_at"] = now
        state["last_success_at"] = now
        state["consecutive_failures"] = 0

        state["safe_state"] = False
        state["state"] = "OK"
        state["failures"] = 0
        state["warnings"] = 0

        log("StaticEngine SUCCESS → GREEN", cfg)

    else:
        # 실패
        state["last_status"] = "fail"
        state["last_error"] = f"returncode={rc}"
        state["last_run_at"] = now
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1

        max_failures = int(cfg.get("max_failures", 3))

        log(f"StaticEngine FAIL (rc={rc}) → {state['consecutive_failures']}/{max_failures}", cfg)

        # 신호등(YELLOW/RED) 반영
        state["state"] = "FAIL"
        state["failures"] = state["consecutive_failures"]
        state["warnings"] = 1

        if state["consecutive_failures"] >= max_failures:
            state["safe_state"] = True
            log("FAIL count ≥ max_failures → SAFE STATE 진입 (RED)", cfg)

    # 4) 상태 저장
    save_json(STATE_PATH, state)


if __name__ == "__main__":
    main()
