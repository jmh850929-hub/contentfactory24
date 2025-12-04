"""
SCH_scheduler_v1_7_1.py
CAPS Scheduler 1.7.1 (Publish 경로 수정 + 안정화 패치)

- Multi-client 스케줄링
- SafeGuard 1.3 연동 (GREEN/YELLOW/RED)
- AutoSync 훅
- Publish Pipeline (Builder → Router → Deploy) 호출
- Publish/engine 경로 정확히 반영
"""

import time
import random
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import json


SETTINGS_FILE = "SCH_settings.json"
STATUS_FILE = "SCH_status_light.json"


# ======================================================
# Utility
# ======================================================

def load_config():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
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


# ======================================================
# 시간 생성
# ======================================================

def pick_time_range(cfg):
    start, end = cfg.get("time_range", ["10:00", "22:00"])
    sh, sm = parse_time(start)
    eh, em = parse_time(end)
    smin = sh * 60 + sm
    emin = eh * 60 + em
    return smin, emin


def generate_time_slots(num_jobs, cfg):
    if num_jobs <= 0:
        return []

    if not cfg.get("random_time", True):
        h, m = parse_time(cfg.get("fixed_time", "14:00"))
        base = datetime.combine(datetime.now().date(), datetime.min.time())
        t = base + timedelta(hours=h, minutes=m)
        return [t for _ in range(num_jobs)]

    smin, emin = pick_time_range(cfg)
    total = emin - smin
    if total <= 0:
        total = 60

    segment = total / num_jobs
    base = datetime.combine(datetime.now().date(), datetime.min.time())
    slots = []

    for i in range(num_jobs):
        seg_start = int(smin + segment * i)
        seg_end   = int(smin + segment * (i + 1))
        if seg_end <= seg_start:
            seg_end = seg_start + 5

        picked = random.randint(seg_start, seg_end)
        t = base + timedelta(hours=picked // 60, minutes=picked % 60)
        slots.append(t)

    slots.sort()
    return slots


# ======================================================
# SafeGuard 연동
# ======================================================

def run_safeguard(status):
    safe_dir = Path(__file__).resolve().parent.parent / "SafeGuard"
    sg_script = safe_dir / "SGD_safe_guard_v1_3.py"

    if not sg_script.exists():
        log("SafeGuard 스크립트 없음 → ERROR")
        status["safe_guard"] = {"state": "ERROR", "failures": 1, "warnings": 0}
        return status

    proc = subprocess.run(
        ["python", str(sg_script)],
        cwd=str(safe_dir),
        capture_output=False,
        check=False
    )

    sg_state_path = safe_dir / "SGD_state.json"
    if sg_state_path.exists():
        with open(sg_state_path, "r", encoding="utf-8") as f:
            sg = json.load(f)
    else:
        sg = {"state": "UNKNOWN", "failures": 0, "warnings": 0}

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status["safe_guard"] = sg
    status["scheduler"]["last_run"] = now
    status["last_update"] = now

    # 신호등 설정
    status = update_traffic_light(status)
    save_status(status)
    return status


def update_traffic_light(status):
    sg = status["safe_guard"]
    failures = sg.get("failures", 0)
    state    = sg.get("state", "UNKNOWN")

    if state == "OK" and failures == 0:
        status["traffic_light"] = "GREEN"
    elif failures >= 2:
        status["traffic_light"] = "RED"
    else:
        status["traffic_light"] = "YELLOW"

    return status


# ======================================================
# Plan 파일 생성 / 저장
# ======================================================

def discover_clients(cfg):
    base_dir = Path(__file__).resolve().parent
    root_rel = cfg.get("clients", {}).get("root", "..\\Clients")

    root_path = (base_dir / root_rel).resolve()
    if not root_path.exists():
        log(f"클라이언트 루트 폴더 없음: {root_path}")
        return []

    clients = [
        {"id": p.name, "path": str(p)}
        for p in sorted(root_path.iterdir())
        if p.is_dir()
    ]

    log(f"감지된 클라이언트 수: {len(clients)}")
    return clients


def create_daily_plan(clients, time_slots):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    jobs = []
    for idx, c in enumerate(clients):
        jobs.append({
            "job_id": idx + 1,
            "client_id": c["id"],
            "client_path": c["path"],
            "run_at": time_slots[idx].strftime("%Y-%m-%d %H:%M:%S"),
            "status": "PENDING",
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S")
        })

    plan = {
        "date": today,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "PENDING",
        "jobs": jobs
    }

    base_dir = Path(__file__).resolve().parent
    plan_path = base_dir / f"SCH_plan_{today}.json"

    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    return plan_path


def load_plan(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def save_plan(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def mark_job(plan, idx, status):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plan["jobs"][idx]["status"] = status
    plan["jobs"][idx]["finished_at"] = now


# ======================================================
# AutoSync / Pipeline 훅
# ======================================================

def run_autosync_if_enabled(cfg):
    autosync_cfg = cfg.get("autosync", {})
    if not autosync_cfg.get("enabled", False):
        return

    base_dir = Path(__file__).resolve().parent
    as_dir = base_dir.parent / "AutoSync"
    script = as_dir / "AS_autosync_v1_4.py"

    if not script.exists():
        log("AutoSync 스크립트 없음 → 건너뜀")
        return

    subprocess.run(
        ["python", str(script)],
        cwd=str(as_dir),
        capture_output=False,
        check=False
    )


def run_pipeline_for_client(cfg, client_id):
    pipeline_cfg = cfg.get("pipeline", {})
    if not pipeline_cfg.get("enabled", False):
        return False

    base_dir = Path(__file__).resolve().parent
    # ★★★ 핵심 수정점: Publish/engine 경로로 변경
    publish_engine_dir = base_dir.parent / "Publish" / "engine"
    script = publish_engine_dir / "PUB_main_pipeline_v1_0.py"

    if not script.exists():
        log(f"Pipeline 스크립트 없음: {script} → 실행 불가")
        return False

    log(f"Pipeline 실행 → client={client_id}")
    proc = subprocess.run(
        ["python", str(script), "--client", client_id],
        cwd=str(publish_engine_dir),
        capture_output=False,
        check=False
    )

    return proc.returncode == 0


# ======================================================
# Main
# ======================================================

def main():
    cfg = load_config()
    schedule_cfg = cfg.get("schedule", {})
    status = load_status()

    log("Scheduler v1.7.1 started.")

    if not schedule_cfg.get("enabled", True):
        log("스케줄러 비활성화 → 종료")
        return

    # 요일 체크
    weekdays = schedule_cfg.get("weekdays", [])
    if weekdays:
        idx = datetime.now().weekday()
        weekmap = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        if weekmap[idx] not in weekdays:
            log("실행 요일 아님 → 종료")
            return

    # 클라이언트 목록
    clients = discover_clients(cfg)
    if not clients:
        log("클라이언트 없음 → 종료")
        return

    # 시간 슬롯 생성
    slots = generate_time_slots(len(clients), schedule_cfg)
    first_run_at = min(slots)
    status["scheduler"]["next_run"] = first_run_at.strftime("%Y-%m-%d %H:%M:%S")
    save_status(status)

    # 플랜 생성
    plan_path = create_daily_plan(clients, slots)
    plan = load_plan(plan_path)

    all_success = True

    # 실행 루프
    for idx, job in enumerate(plan["jobs"]):
        run_at = datetime.strptime(job["run_at"], "%Y-%m-%d %H:%M:%S")
        client_id = job["client_id"]

        # 대기
        while datetime.now() < run_at:
            time.sleep(5)

        log(f"작업 시작 (client={client_id}) → SafeGuard 실행")
        status = run_safeguard(status)

        if status.get("traffic_light") != "GREEN":
            log(f"신호등 GREEN 아님({status.get('traffic_light')}) → 중단")
            mark_job(plan, idx, "SKIPPED")
            all_success = False
            break

        # AutoSync
        run_autosync_if_enabled(cfg)

        # Pipeline
        ok = run_pipeline_for_client(cfg, client_id)
        if ok:
            mark_job(plan, idx, "DONE")
        else:
            mark_job(plan, idx, "FAILED")
            all_success = False

        save_plan(plan_path, plan)

    # 플랜 마무리
    plan["state"] = "DONE" if all_success else "FAILED"
    plan["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_plan(plan_path, plan)

    log(f"오늘 스케줄 종료. 전체 성공 여부: {all_success}")


if __name__ == "__main__":
    main()
