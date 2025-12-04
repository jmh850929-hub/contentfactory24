"""
SCH_scheduler_v1_5.py
CAPS Scheduler 1.5 - SafeGuard 연동 + 신호등 시스템
"""

import time
import random
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import json

SETTINGS_FILE = "SCH_settings.json"
STATUS_FILE = "SCH_status_light.json"


def load_cfg():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("schedule", {})
    except Exception:
        return {}


def load_status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "last_update": "",
            "safe_guard": {"state": "UNKNOWN", "failures": 0, "warnings": 0},
            "scheduler": {"next_run": "", "last_run": ""},
            "traffic_light": "GREY"
        }


def save_status(st):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SCH] {ts} | {msg}")


def parse_time(t):
    h, m = map(int, t.split(":"))
    return h, m


def pick_time(cfg):
    if cfg.get("random_time", True):
        start, end = cfg.get("time_range", ["10:00", "22:00"])
        sh, sm = parse_time(start)
        eh, em = parse_time(end)
        smin = sh * 60 + sm
        emin = eh * 60 + em
        pick = random.randint(smin, emin)
        return pick // 60, pick % 60
    else:
        return parse_time(cfg.get("fixed_time", "14:00"))


def update_traffic_light(status):
    """
    SafeGuard 결과 기반 신호등 설정
    GREEN  = OK
    YELLOW = 경고 또는 실패 1회
    RED    = 연속 오류 >= 2
    """

    sg = status["safe_guard"]
    failures = sg.get("failures", 0)
    warnings = sg.get("warnings", 0)
    state = sg.get("state", "UNKNOWN")

    if state == "OK" and failures == 0:
        status["traffic_light"] = "GREEN"
    elif failures >= 2:
        status["traffic_light"] = "RED"
    else:
        status["traffic_light"] = "YELLOW"

    return status


def update_next_run(status, run_at):
    status["scheduler"]["next_run"] = run_at.strftime("%Y-%m-%d %H:%M:%S")
    return status


def main():
    cfg = load_cfg()
    status = load_status()

    log("Scheduler v1.5 started.")

    # 요일 필터
    weekdays = cfg.get("weekdays", [])
    if weekdays:
        idx = datetime.now().weekday()
        weekmap = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        if weekmap[idx] not in weekdays:
            log("실행 요일 아님 → 종료")
            return

    # 실행 시간 계산
    rh, rm = pick_time(cfg)
    run_at = datetime.combine(datetime.now().date(), datetime.min.time()) + timedelta(
        hours=rh, minutes=rm
    )

    log(f"오늘 실행 예정 시각: {run_at}")

    status = update_next_run(status, run_at)
    save_status(status)

    # 대기
    while datetime.now() < run_at:
        time.sleep(5)

    log("스케줄 시간 도달 → SafeGuard 실행")

    # SafeGuard 실행
    try:
        proc = subprocess.run(
            ["python", "SGD_safe_guard_v1_2.py"],
            cwd=str(Path(__file__).resolve().parent.parent / "SafeGuard"),
            capture_output=True,
            text=True
        )
        log(f"SafeGuard 종료 코드: {proc.returncode}")

        # SafeGuard 상태 파일 로드
        sg_state_path = Path(__file__).resolve().parent.parent / "SafeGuard" / "SGD_state.json"
        if sg_state_path.exists():
            with open(sg_state_path, "r", encoding="utf-8") as f:
                sg_state = json.load(f)
        else:
            sg_state = {"state": "UNKNOWN", "failures": 0, "warnings": 0}

        # 상태 업데이트
        status["safe_guard"] = sg_state
        status["scheduler"]["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 신호등 업데이트
        status = update_traffic_light(status)
        save_status(status)

    except Exception as e:
        log(f"SafeGuard 실행 오류: {e}")
        status["safe_guard"] = {"state": "ERROR", "failures": 1, "warnings": 0}
        status = update_traffic_light(status)
        save_status(status)


if __name__ == "__main__":
    main()
