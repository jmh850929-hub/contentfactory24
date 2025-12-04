from __future__ import annotations
import json
import subprocess
from pathlib import Path
from datetime import datetime

# SafeGuard 1.2 (Static Omega 2.5 전용)
# - StaticEngine 실행 래퍼
# - 연속 실패 횟수 관리
# - Safe State 진입/해제
# - 스케줄러는 이 파일을 대신 호출

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "SGD_config.json"
STATE_PATH = BASE_DIR / "SGD_state.json"


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


def log(msg: str, cfg: dict) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[SafeGuard] {ts} | {msg}"
    print(line)
    log_file = cfg.get("log_file", "SGD_log.txt")
    log_path = BASE_DIR / log_file
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_static_engine(cfg: dict, state: dict) -> int:
    """
    StaticEngine(OMG_main_engine_static_v25.py)을 실행하고
    returncode 를 그대로 돌려준다.
    """
    engine_cmd: list[str] = cfg.get(
        "engine_cmd",
        ["python", "OMG_main_engine_static_v25.py"],
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


def main():
    # 0) 설정/상태 로딩
    cfg_default = {
        "max_failures": 3,
        "engine_cmd": ["python", "OMG_main_engine_static_v25.py"],
        "engine_cwd": r"C:\A1-M2\OmegaEngine",
        "log_file": "SGD_log.txt",
        "auto_resume": True,
    }
    cfg = load_json(CONFIG_PATH, cfg_default)

    state_default = {
        "safe_state": False,
        "consecutive_failures": 0,
        "last_status": None,      # "success" / "fail"
        "last_error": None,
        "last_run_at": None,
        "last_success_at": None,
    }
    state = load_json(STATE_PATH, state_default)

    # 1) Safe State 인지 먼저 확인
    if state.get("safe_state", False):
        msg = "SAFE STATE → 실행 차단"
        if cfg.get("auto_resume", False):
            msg += " (auto_resume=True 이므로 1회 시도)"
        log(msg, cfg)
        if not cfg.get("auto_resume", False):
            return

    # 2) StaticEngine 실행
    rc = run_static_engine(cfg, state)

    # 3) 결과에 따른 상태 업데이트
    now = datetime.now().isoformat(timespec="seconds")

    if rc == 0:
        # 성공
        state["last_status"] = "success"
        state["last_error"] = None
        state["last_run_at"] = now
        state["last_success_at"] = now
        state["consecutive_failures"] = 0

        if state.get("safe_state", False):
            log("StaticEngine 성공 → SAFE STATE 해제", cfg)
        state["safe_state"] = False

    else:
        # 실패
        state["last_status"] = "fail"
        state["last_error"] = f"returncode={rc}"
        state["last_run_at"] = now
        state["consecutive_failures"] = int(state.get("consecutive_failures", 0)) + 1

        max_failures = int(cfg.get("max_failures", 3))
        log(
            f"StaticEngine FAIL (rc={rc}) → count={state['consecutive_failures']}/{max_failures}",
            cfg,
        )

        if state["consecutive_failures"] >= max_failures:
            state["safe_state"] = True
            log("FAIL count ≥ max_failures → SAFE STATE 진입", cfg)

    # 4) 상태 저장
    save_json(STATE_PATH, state)


if __name__ == "__main__":
    main()
