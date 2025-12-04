# Version: 1.8
"""
Scheduler v1.8
CAPS - WebRack 대응 버전
- 상업용 / 비상업용 사이트 분리
- 비상업용 12종 랜덤 포스팅
- AutoSync 4.0 Safe-Patch 영역 지원
"""

import json
import random
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
SETTINGS = BASE_DIR / "SCH_settings.json"
STATUS_LIGHT = BASE_DIR / "SCH_status_light.json"
PLAN_FILE = BASE_DIR / f"SCH_plan_{datetime.now().strftime('%Y-%m-%d')}.json"

# 12종 비상업용 카테고리 Pool
INFO_POOL = [
    "정보성", "지역 행사", "운영자 일상", "업계 상식",
    "FAQ", "주변 장소 소개", "장비 정보", "일반 잡정보",
    "주간 브리핑", "리뷰 요약", "사진 기반 콘텐츠", "미니 칼럼"
]

def safe_print(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SCH 1.8] {ts} | {msg}")

def load_json(path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_web_rack(client):
    return client.startswith("rack")

def select_random_category():
    return random.choice(INFO_POOL)

def build_payload(client, category):
    return {
        "client": client,
        "category": category,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def run_scheduler():
    # Light status check
    status = load_json(STATUS_LIGHT, {"light": "GREEN"})
    if status.get("light") != "GREEN":
        safe_print("SafeGuard not green. Scheduler halted.")
        return

    # Settings
    settings = load_json(SETTINGS, {"clients": []})
    clients = settings.get("clients", [])

    plan = {"run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tasks": []}

    for client in clients:
        if is_web_rack(client["id"]):
            category = select_random_category()
            safe_print(f"WebRack Client → {client['id']} / 랜덤 카테고리: {category}")
        else:
            category = client.get("category", "상업용")

        payload = build_payload(client["id"], category)
        plan["tasks"].append(payload)

    save_json(PLAN_FILE, plan)
    safe_print(f"Plan generated → {PLAN_FILE.name}")

    return plan

if __name__ == "__main__":
    run_scheduler()
