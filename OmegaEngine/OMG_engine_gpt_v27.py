"""
OmegaEngine v2.7 - GPT를 이용한 최종 본문 생성 엔진
gpt_payload/*.json → GPT 호출 → final_output/*.json

v2.6이 만든 draft_content를 GPT로 다듬어
최종 블로그용 문서로 만든다.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from GPT_retry_recovery_v1 import call_with_retry
from GPT_response_parser_v1 import parse_gpt_text


BASE = Path(__file__).resolve().parent
PAYLOAD_DIR = BASE / "gpt_payload"
FINAL_DIR   = BASE / "final_output"
GPT_CFG     = BASE / "OMG_prompt_gpt_v1.json"


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[OMG 2.7] {ts} | {msg}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_user_prompt(template: str, payload: Dict[str, Any]) -> str:
    meta = payload.get("meta", {})
    client_name = meta.get("client_name") or meta.get("location") or "해당 공간"
    return template.replace("{client_name}", client_name)


def main():
    log("OmegaEngine v2.7 GPT Engine started.")

    if not PAYLOAD_DIR.exists():
        log("gpt_payload 폴더 없음 → 종료")
        return

    gpt_cfg = load_json(GPT_CFG)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    count = 0
    for p in PAYLOAD_DIR.glob("*_gpt_payload.json"):

        payload = load_json(p)
        meta = payload.get("meta", {})

        system_prompt = payload.get("system_prompt") or gpt_cfg.get("system_prompt", "")
        user_prompt_t = payload.get("user_prompt_template") or gpt_cfg.get("user_prompt_template","")
        draft = payload.get("draft_content","")

        if not draft.strip():
            log(f"draft_content 없음 → 스킵: {p.name}")
            continue

        user_prompt = (
            build_user_prompt(user_prompt_t, payload)
            + "\n\n---\n\n"
            + draft
        )

        # GPT 호출 or mock
        gpt_text = call_with_retry(
            gpt_cfg,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            draft_content=draft
        )

        parsed = parse_gpt_text(gpt_text, meta)

        final_obj = {
            "version": "2.7",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "meta": parsed["meta"],
            "style": payload.get("style", {}),
            "draft_content": draft,
            "gpt_output": {
                "title": parsed["title"],
                "content_markdown": parsed["content_markdown"]
            }
        }

        out_name = p.name.replace("_gpt_payload.json", "_final_v27.json")
        save_json(FINAL_DIR / out_name, final_obj)
        count += 1

    log(f"총 생성된 최종 본문 수: {count}")
    log("OmegaEngine v2.7 GPT Engine finished.")


if __name__ == "__main__":
    main()
