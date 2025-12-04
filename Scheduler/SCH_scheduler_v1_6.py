"""
SCH_scheduler_v1_6.py
CAPS Scheduler 1.6 - SafeGuard 연동 + AutoSync + CAPS Pipeline Hook
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
    """
    전체 설정(JSON) 로드.
    - schedule
    - autosync
    - pipeline
    """
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_status():
    """
    상태 파일 로드. 없으면 기본값 생성.
    """
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


def pick_time(schedule_cfg):
    """
    설정 기준으로 오늘 실행 시각 선택.
    - random_time=True 면 time_range 내에서 랜덤
    - False면 fixed_time 사용
    """
    if schedule_cfg.get("random_time", True):
        start, end = schedule_cfg.get("time_range", ["10:00", "22:00"])
        sh, sm = parse_time(start)
        eh, em = parse_time(end)
        smin = sh * 60 + sm
        emin = eh * 60 + em
        pick = random.randint(smin, emin)
        return pick // 60, pick % 60
    else:
        return parse_time(schedule_cfg.get("fixed_time", "14:00"))


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


def create_daily_plan():
    """
    아주 단순한 형태의 '오늘 작업 계획' JSON 생성.
    - 나중에 Multi-Client / Multi-Job 구조로 확장 가능.
    """
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    plan = {
        "date": today,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "PENDING",
        "jobs": [
            {
                "id": 1,
                "type": "CAPS_DAILY_BATCH",
                "status": "PENDING",
                "notes": "Omega → Builder → Router → Deploy 일괄 실행"
            }
        ]
    }

    base_dir = Path(__file__).resolve().parent
    plan_path = base_dir / f"SCH_plan_{today}.json"

    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    log(f"오늘 작업 계획 생성: {plan_path}")
    return plan_path


def update_plan_done(plan_path, success=True):
    """
    작업 완료 후 계획 파일 상태 갱신.
    """
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            plan = json.load(f)
    except Exception:
        return

    plan["state"] = "DONE" if success else "FAILED"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plan["finished_at"] = now

    if plan.get("jobs"):
        plan["jobs"][0]["status"] = "DONE" if success else "FAILED"
        plan["jobs"][0]["finished_at"] = now

    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def run_autosync_if_enabled(autosync_cfg):
    """
    AutoSync 훅.
    - 실제 AutoSync 스크립트 이름/경로는 우현이가 쓰는 구조에 맞게 조정하면 됨.
    """
    if not autosync_cfg.get("enabled", False):
        log("AutoSync 비활성화 상태 → 건너뜀")
        return

    try:
        base_dir = Path(__file__).resolve().parent
        autosync_dir = base_dir.parent / "AutoSync"

        # ★ 여기서 실제 AutoSync 스크립트 이름만 바꿔주면 됨
        autosync_script = autosync_dir / "ASY_autosync_v1_0.py"

        if not autosync_script.exists():
            log(f"AutoSync 스크립트 없음: {autosync_script} → 건너뜀")
            return

        log(f"AutoSync 실행: {autosync_script}")
        proc = subprocess.run(
            ["python", str(autosync_script)],
            cwd=str(autosync_dir),
            capture_output=True,
            text=True
        )
        log(f"AutoSync 종료 코드: {proc.returncode}")
        if proc.stdout:
            log(f"AutoSync 출력:\n{proc.stdout}")

    except Exception as e:
        log(f"AutoSync 실행 오류: {e}")


def run_caps_pipeline_if_enabled(pipeline_cfg):
    """
    CAPS 메인 파이프라인 훅.
    - Omega → Builder → Router → Deploy를 실행하는 메인 스크립트를 호출.
    - 실제 파일명/경로는 우현이 환경에 맞게 수정하면 됨.
    """
    if not pipeline_cfg.get("enabled", False):
        log("CAPS Pipeline 비활성화 상태 → 건너뜀")
        return False

    try:
        base_dir = Path(__file__).resolve().parent
        # 예시: Publish/engine 아래 메인 파이프라인 스크립트
        publish_engine_dir = base_dir.parent / "Publish" / "engine"

        # ★ 여기서 실제 파이프라인 스크립트 이름만 바꿔주면 됨
        pipeline_script = publish_engine_dir / "PUB_main_pipeline_v1_0.py"

        if not pipeline_script.exists():
            log(f"Pipeline 스크립트 없음: {pipeline_script} → 실행 불가")
            return False

        log(f"CAPS Pipeline 실행: {pipeline_script}")
        proc = subprocess.run(
            ["python", str(pipeline_script)],
            cwd=str(publish_engine_dir),
            capture_output=True,
            text=True
        )
        log(f"CAPS Pipeline 종료 코드: {proc.returncode}")
        if proc.stdout:
            log(f"CAPS Pipeline 출력:\n{proc.stdout}")

        return proc.returncode == 0

    except Exception as e:
        log(f"CAPS Pipeline 실행 오류: {e}")
        return False


def main():
    cfg = load_cfg()
    schedule_cfg = cfg.get("schedule", {})
    autosync_cfg = cfg.get("autosync", {})
    pipeline_cfg = cfg.get("pipeline", {})

    status = load_status()

    log("Scheduler v1.6 started.")

    # 스케줄러 사용 여부 체크
    if not schedule_cfg.get("enabled", True):
        log("스케줄러 비활성화 상태 → 종료")
        return

    # 요일 필터
    weekdays = schedule_cfg.get("weekdays", [])
    if weekdays:
        idx = datetime.now().weekday()
        weekmap = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        if weekmap[idx] not in weekdays:
            log("실행 요일 아님 → 종료")
            return

    # 실행 시간 계산
    rh, rm = pick_time(schedule_cfg)
    run_at = datetime.combine(datetime.now().date(), datetime.min.time()) + timedelta(
        hours=rh, minutes=rm
    )

    log(f"오늘 실행 예정 시각: {run_at}")

    status = update_next_run(status, run_at)
    save_status(status)

    # 오늘 작업 계획 생성 (아주 단순 버전)
    plan_path = create_daily_plan()

    # 대기 루프
    while datetime.now() < run_at:
        time.sleep(5)

    log("스케줄 시간 도달 → SafeGuard 실행")

    # SafeGuard 실행
    try:
        safe_guard_dir = Path(__file__).resolve().parent.parent / "SafeGuard"
        sg_script = safe_guard_dir / "SGD_safe_guard_v1_2.py"

        if not sg_script.exists():
            log(f"SafeGuard 스크립트 없음: {sg_script}")
            status["safe_guard"] = {"state": "ERROR", "failures": 1, "warnings": 0}
            status = update_traffic_light(status)
            save_status(status)
            return

        proc = subprocess.run(
            ["python", str(sg_script)],
            cwd=str(safe_guard_dir),
            capture_output=True,
            text=True
        )
        log(f"SafeGuard 종료 코드: {proc.returncode}")
        if proc.stdout:
            log(f"SafeGuard 출력:\n{proc.stdout}")

        # SafeGuard 상태 파일 로드
        sg_state_path = safe_guard_dir / "SGD_state.json"
        if sg_state_path.exists():
            with open(sg_state_path, "r", encoding="utf-8") as f:
                sg_state = json.load(f)
        else:
            sg_state = {"state": "UNKNOWN", "failures": 0, "warnings": 0}

        # 상태 업데이트
        status["safe_guard"] = sg_state
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["scheduler"]["last_run"] = now_str
        status["last_update"] = now_str

        # 신호등 업데이트
        status = update_traffic_light(status)
        save_status(status)

    except Exception as e:
        log(f"SafeGuard 실행 오류: {e}")
        status["safe_guard"] = {"state": "ERROR", "failures": 1, "warnings": 0}
        status = update_traffic_light(status)
        save_status(status)
        return

    # 신호등 기준으로 후속 작업 결정
    if status.get("traffic_light") != "GREEN":
        log(f"신호등 상태가 GREEN이 아님({status.get('traffic_light')}) → AutoSync/Pipeline 수행 안 함")
        update_plan_done(plan_path, success=False)
        return

    # 1) AutoSync (옵션)
    run_autosync_if_enabled(autosync_cfg)

    # 2) CAPS Pipeline (옵션)
    success = run_caps_pipeline_if_enabled(pipeline_cfg)
    update_plan_done(plan_path, success=success)


if __name__ == "__main__":
    main()
