# Version: 2.0 (Production-Ready: WebRack HTML Builder)
"""
Scheduler v2.0
CAPS WebRack + HTML Generator + Multi-Site Template Builder

핵심:
- 거래처 / WebRack 구분 HTML 생성
- site-dist/<client>/index.html 자동 생성
- SafeGuard GREEN 시에만 동작
- AutoSync 4.x 배포 패치 지원
- OmegaEngine HTML Hook 탑재 (2.1에서 활성화)
"""

import json
import random
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
DIST = BASE / "site-dist"
SETTINGS = BASE / "SCH_settings.json"
STATUS_LIGHT = BASE / "SCH_status_light.json"

INFO_POOL = [
    "정보성",
    "지역 행사",
    "운영자 일상",
    "업계 상식",
    "FAQ",
    "주변 장소 소개",
    "장비/재료 정보",
    "일반 잡정보",
    "주간 브리핑",
    "리뷰 요약",
    "사진 기반 콘텐츠",
    "미니 칼럼"
]

def safe_print(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SCH 2.0] {ts} | {msg}")

def load_json(path: Path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def ensure_settings():
    if not SETTINGS.exists():
        base = {
            "clients": [
                {"id": "01-sangsangpiano", "title": "상상피아노"},
                {"id": "02-jay-gongbang", "title": "제이공방"},
                {"id": "rack-random", "title": "랜덤 웹랙"}
            ]
        }
        save_json(SETTINGS, base)
        return base
    return load_json(SETTINGS)

def ensure_status():
    if not STATUS_LIGHT.exists():
        save_json(STATUS_LIGHT, {"light": "GREEN"})
        return {"light": "GREEN"}
    return load_json(STATUS_LIGHT)

def is_webrack(cid: str) -> bool:
    return cid.startswith("rack")

def pick_category():
    return random.choice(INFO_POOL)

def html_template(client_name: str, category: str) -> str:
    """v2.0 기본 HTML 템플릿"""
    return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>{client_name} - {category}</title>
    <meta name="description" content="{client_name} / CAPS 자동생성 / 카테고리: {category}">
</head>
<body>
    <h1>{client_name}</h1>
    <p>카테고리: {category}</p>
    <p>자동 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body>
</html>
""".strip()

def build_site(client_id: str, client_name: str, category: str):
    """site-dist/<client>/index.html 생성"""
    path = DIST / client_id
    path.mkdir(parents=True, exist_ok=True)

    html_code = html_template(client_name, category)
    index_file = path / "index.html"

    index_file.write_text(html_code, encoding="utf-8")
    safe_print(f"HTML built → {index_file}")

def run_scheduler():
    status = ensure_status()
    if status.get("light") != "GREEN":
        safe_print("SafeGuard not green. Scheduler halted.")
        return None

    settings = ensure_settings()
    clients = settings.get("clients", [])

    DIST.mkdir(exist_ok=True)

    plan = []

    for client in clients:
        cid = client["id"]
        cname = client.get("title", cid)

        if is_webrack(cid):
            category = pick_category()
        else:
            category = client.get("category", "상업용")

        # HTML 생성
        build_site(cid, cname, category)

        plan.append({
            "client": cid,
            "category": category,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    plan_file = BASE / f"SCH_plan_{datetime.now().strftime('%Y-%m-%d')}.json"
    save_json(plan_file, {"version": "2.0", "tasks": plan})
    safe_print(f"Plan saved → {plan_file.name}")

    return plan

if __name__ == "__main__":
    run_scheduler()
