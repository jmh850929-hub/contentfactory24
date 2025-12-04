"""
AS_autosync_v3_1.py
AutoSync 3.1 - 노마드 명령 인식 + 명령 계획 생성 (Sandbox, No-Code-Change)

역할:
1) AS_commands_v3_1.json 에 적힌 노마드 명령들을 읽는다.
2) 각 명령에 대해 Command Intent 엔진으로 의도를 분석한다.
3) 분석 결과를 기반으로 "명령 실행 계획"을 generated/AS_command_plan_v3_1.json 에 저장한다.
4) AS_state_v3_1.json / AS_report_v3_1.json 에 요약 정보를 기록한다.

주의:
- 3.1 단계에서는 실제 코드 수정/버전업은 수행하지 않는다.
- 오직 "명령 → 구조화된 의도/계획" 까지만 진행한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from AS_command_intent_v3_1 import analyze_command


BASE_DIR = Path(__file__).resolve().parent
COMMAND_FILE = BASE_DIR / "AS_commands_v3_1.json"
STATE_FILE = BASE_DIR / "AS_state_v3_1.json"
REPORT_FILE = BASE_DIR / "AS_report_v3_1.json"
GENERATED_DIR = BASE_DIR / "generated"
PLAN_FILE = GENERATED_DIR / "AS_command_plan_v3_1.json"


def safe_print(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[AS] {ts} | {msg}")


def load_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_default_commands_file() -> None:
    """
    명령 파일이 없으면 템플릿을 생성한다.
    """
    if COMMAND_FILE.exists():
        return

    template = {
        "version": "3.1",
        "description": "노마드에서 AutoSync에 전달하는 명령 리스트입니다.",
        "commands": [
            {
                "id": "example-1",
                "source": "Nomad",
                "text": "스케줄러에 주간 모드 기능 만들어줘.",
                "status": "pending"
            }
        ]
    }
    save_json(COMMAND_FILE, template)


def main():
    safe_print("AutoSync v3.1 (command mode) started.")

    # 1) 명령 인박스 템플릿 확보
    ensure_default_commands_file()

    # 2) 명령 로드
    raw = load_json(COMMAND_FILE, default={"commands": []})
    commands: List[Dict[str, Any]] = raw.get("commands", [])

    if not commands:
        safe_print("No commands found in AS_commands_v3_1.json")
        analyzed: List[Dict[str, Any]] = []
    else:
        safe_print(f"Loaded {len(commands)} commands.")
        analyzed = []
        for cmd in commands:
            cid = str(cmd.get("id", "unknown"))
            text = str(cmd.get("text", "")).strip()
            if not text:
                continue
            intent = analyze_command(cid, text)
            intent["status"] = cmd.get("status", "pending")
            analyzed.append(intent)

    # 3) generated 폴더 및 계획 파일 생성
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    plan = {
        "version": "3.1",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "command_count": len(analyzed),
        "intents": analyzed,
    }
    save_json(PLAN_FILE, plan)

    # 4) 상태/리포트 파일 생성
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    state = {
        "version": "3.1",
        "last_run": now,
        "command_count": len(analyzed),
        "pending": sum(1 for i in analyzed if i.get("status") == "pending"),
        "by_intent_type": {},
        "by_module": {},
    }

    # intent 통계
    for item in analyzed:
        itype = item.get("intent_type", "unknown")
        mod = item.get("target_module", "Unknown")
        state["by_intent_type"][itype] = state["by_intent_type"].get(etype := itype, 0) + 1
        state["by_module"][mod] = state["by_module"].get(mod, 0) + 1

    report = {
        "version": "3.1",
        "generated_at": now,
        "summary": {
            "command_count": len(analyzed),
            "pending": state["pending"],
        },
        "intents": analyzed,
        "plan_file": str(PLAN_FILE),
    }

    save_json(STATE_FILE, state)
    save_json(REPORT_FILE, report)

    safe_print(f"Commands : {len(analyzed)}")
    safe_print(f"Pending  : {state['pending']}")
    safe_print("AutoSync v3.1 (command mode) finished.")


if __name__ == "__main__":
    main()
