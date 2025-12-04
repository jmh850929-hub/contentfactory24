"""
SCH_scheduler_v1_7.py
CAPS Scheduler 1.7
- Multi-Client 스케줄링
- SafeGuard 연동
- AutoSync 훅
- CAPS Pipeline 훅
"""

import time
import random
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import json

SETTINGS_FILE = "SCH_settings.json"
STATUS_FILE = "SCH_status_light.json"


# ---------------- 기본 유틸 ----------------

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


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SCH] {ts} | {msg}")


def parse_time(t: str):
    h, m = map(int, t.split(":"))
    return h, m


# ---------------- 시간 관련 ----------------

def pick_time_range(schedule_cfg):
    """time_range 로부터 시작/끝 분 단위로 반환"""
    start, end = schedule_cfg.get("time_range", ["10:00", "22:00"])
    sh, sm = parse_time(start)
    eh, em = parse_time(end)
    smin = sh * 60 + sm
    emin = eh * 60 + em
    return smin, emin


def generate_time_slots(num_jobs: int, schedule_cfg):
    """
    여러 거래처용 시간 슬롯 생성.
    - 전체 time_range 를 num_jobs 구간으로 나누고
    - 각 구간 안에서 랜덤으로 하나씩 선택
    """
    if num_jobs <= 0:
        return []

    random_time = schedule_cfg.get("random_time", True)
    if not random_time:
        # 고정 시간 하나만 모든 작업에 사용
        h, m = parse_time(schedule_cfg.get("fixed_time", "14:00"))
        base = datetime.combine(datetime.now().date(), datetime.min.time())
        run_at = base + timedelta(hours=h, minutes=m)
        return [run_at for _ in range(num_jobs)]

    smin, emin = pick_time_range(schedule_cfg)
    total = emin - smin
    if total <= 0:
        total = 60  # 방어용

    base = datetime.combine(datetime.now().date(), datetime.min.time())

    slots = []
    segment = total / num_jobs

    for i in range(num_jobs):
        seg_start = int(smin + segment * i)
        seg_end = int(smin + segment * (i + 1))
        if seg_end <= seg_start:
            seg_end = seg_start + 5

        picked = random.randint(seg_start, seg_end)
        rh = picked // 60
        rm = picked % 60
        run_at = base + timedelta(hours=rh, minutes=rm)
        slots.append(run_at)

    slots.sort()
    return slots


def update_next_run(status, first_run_at):
    status["scheduler"]["next_run"] = first_run_at.strftime("%Y-%m-%d %H:%M:%S")
    return status


def update_traffic_light(status):
    """
    SafeGuard 결과 기반 신호등 설정
    GREEN  = OK
    YELLOW = 경고 또는 실패 1회
    RED    = 연속 오류 >= 2
    """
    sg = status.get("safe_guard", {})
    failures = sg.get("failures", 0)
    state = sg.get("state", "UNKNOWN")

    if state == "OK" and failures == 0:
        status["traffic_light"] = "GREEN"
    elif failures >= 2:
        status["traffic_light"] = "RED"
    else:
        status["traffic_light"] = "YELLOW"
    return status


# ---------------- 클라이언트 / 플랜 ----------------

def discover_clients(cfg):
    """
    clients.root 기준으로 하위 폴더를 클라이언트로 인식.
    예) ../Clients/01_Piano, ../Clients/02_Cafe ...
    """
    base_dir = Path(__file__).resolve().parent
    clients_cfg = cfg.get("clients", {})
    root_rel = clients_cfg.get("root", "..\\Clients")

    clients_root = (base_dir / root_rel).resolve()
    if not clients_root.exists():
        log(f"클라이언트 루트 폴더 없음: {clients_root}")
        return []

    clients = []
    for p in sorted(clients_root.iterdir()):
        if p.is_dir():
            clients.append({
                "id": p.name,          # 폴더명 그대로 ID로 사용
                "path": str(p)
            })

    log(f"감지된 클라이언트 수: {len(clients)}")
    return clients


def create_daily_plan(clients, time_slots):
    """
    오늘 작업 계획 JSON 생성.
    jobs 리스트에 거래처별 작업 기록.
    """
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    jobs = []
    for idx, client in enumerate(clients):
        jobs.append({
            "job_id": idx + 1,
            "client_id": client["id"],
            "client_path": client["path"],
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

    log(f"오늘 작업 계획 생성: {plan_path}")
    return plan_path


def load_plan(plan_path: Path):
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_plan(plan_path: Path, plan):
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def mark_job_status(plan, job_idx, status_str: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    job = plan["jobs"][job_idx]
    job["status"] = status_str
    job["finished_at"] = now


def finalize_plan(plan, success: bool):
    plan["state"] = "DONE" if success else "FAILED"
    plan["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------- 외부 훅: AutoSync, Pipeline ----------------

def run_autosync_if_enabled(cfg):
    autosync_cfg = cfg.get("autosync", {})
    if not autosync_cfg.get("enabled", False):
        log("AutoSync 비활성화 상태 → 건너뜀")
        return

    try:
        base_dir = Path(__file__).resolve().parent
        autosync_dir = base_dir.parent / "AutoSync"
        autosync_script = autosync_dir / "ASY_autosync_v1_0.py"  # 필요시 파일명 수정

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


def run_caps_pipeline_for_client(cfg, client_id: str):
    """
    특정 클라이언트에 대해 CAPS Pipeline 실행.
    - 환경변수나 인자로 client_id 를 넘겨서 사용.
    """
    pipeline_cfg = cfg.get("pipeline", {})
    if not pipeline_cfg.get("enabled", False):
        log("CAPS Pipeline 비활성화 상태 → 건너뜀")
        return False

    try:
        base_dir = Path(__file__).resolve().parent
        publish_engine_dir = base_dir.parent / "engine"
        # 필요시 파일명/경로 수정
        pipeline_script = publish_engine_dir / "PUB_main_pipeline_v1_0.py"

        if not pipeline_script.exists():
            log(f"Pipeline 스크립트 없음: {pipeline_script} → 실행 불가")
            return False

        log(f"CAPS Pipeline 실행 (client={client_id}): {pipeline_script}")
        proc = subprocess.run(
            ["python", str(pipeline_script), "--client", client_id],
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


def run_safeguard(status):
    """
    SafeGuard 실행 후 상태/신호등 업데이트 반환.
    """
    try:
        safe_guard_dir = Path(__file__).resolve().parent.parent / "SafeGuard"
        sg_script = safe_guard_dir / "SGD_safe_guard_v1_2.py"

        if not sg_script.exists():
            log(f"SafeGuard 스크립트 없음: {sg_script}")
            status["safe_guard"] = {"state": "ERROR", "failures": 1, "warnings": 0}
            status = update_traffic_light(status)
            save_status(status)
            return status

        proc = subprocess.run(
            ["python", str(sg_script)],
            cwd=str(safe_guard_dir),
            capture_output=True,
            text=True
        )
        log(f"SafeGuard 종료 코드: {proc.returncode}")
        if proc.stdout:
            log(f"SafeGuard 출력:\n{proc.stdout}")

        sg_state_path = safe_guard_dir / "SGD_state.json"
        if sg_state_path.exists():
            with open(sg_state_path, "r", encoding="utf-8") as f:
                sg_state = json.load(f)
        else:
            sg_state = {"state": "UNKNOWN", "failures": 0, "warnings": 0}

        status["safe_guard"] = sg_state
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["scheduler"]["last_run"] = now_str
        status["last_update"] = now_str

        status = update_traffic_light(status)
        save_status(status)
        return status

    except Exception as e:
        log(f"SafeGuard 실행 오류: {e}")
        status["safe_guard"] = {"state": "ERROR", "failures": 1, "warnings": 0}
        status = update_traffic_light(status)
        save_status(status)
        return status


# ---------------- 메인 ----------------

def main():
    cfg = load_config()
    schedule_cfg = cfg.get("schedule", {})
    status = load_status()

    log("Scheduler v1.7 started.")

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

    # 클라이언트 목록
    clients = discover_clients(cfg)
    if not clients:
        log("클라이언트가 없음 → 종료")
        return

    # 각 클라이언트별 실행 시각 생성
    time_slots = generate_time_slots(len(clients), schedule_cfg)
    first_run_at = min(time_slots)
    status = update_next_run(status, first_run_at)
    save_status(status)
    plan_path = create_daily_plan(clients, time_slots)

    # 메인 루프: 각 작업 시각까지 기다렸다가 실행
    plan = load_plan(plan_path)
    if not plan:
        log("플랜 로드 실패 → 종료")
        return

    all_success = True

    for idx, job in enumerate(plan["jobs"]):
        client_id = job["client_id"]
        run_at = datetime.strptime(job["run_at"], "%Y-%m-%d %H:%M:%S")

        # 해당 작업 시간까지 대기
        while datetime.now() < run_at:
            time.sleep(5)

        log(f"작업 시작 (client={client_id}) → SafeGuard 실행")
        status = run_safeguard(status)

        if status.get("traffic_light") != "GREEN":
            log(f"신호등 상태가 GREEN 아님({status.get('traffic_light')}) → 이후 작업 중단")
            mark_job_status(plan, idx, "SKIPPED")
            all_success = False
            break

        # AutoSync (옵션, 전체 공통)
        run_autosync_if_enabled(cfg)

        # CAPS Pipeline 실행 (클라이언트별)
        success = run_caps_pipeline_for_client(cfg, client_id)
        if success:
            mark_job_status(plan, idx, "DONE")
        else:
            mark_job_status(plan, idx, "FAILED")
            all_success = False
            # 실패 시 다음 작업 진행 여부는 정책에 따라 조정 가능
            # 여기서는 일단 계속 진행

        save_plan(plan_path, plan)

    finalize_plan(plan, all_success)
    save_plan(plan_path, plan)
    log(f"오늘 스케줄 종료. 전체 성공 여부: {all_success}")


if __name__ == "__main__":
    main()
