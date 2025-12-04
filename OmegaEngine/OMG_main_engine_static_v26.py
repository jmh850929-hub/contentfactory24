"""
OMG_main_engine_static_v26.py
OmegaEngine v2.6 - Pre-GPT Layer

역할:
1) OmegaEngine 2.5가 생성한 output JSON들을 읽는다.
2) OMG_prompt_layer_v1.json, OMG_pre_template_v26.json 설정을 바탕으로
   GPT에 넘길 수 있는 페이로드(gpt_payload)를 생성한다.
3) 결과는 gpt_payload 폴더에 파일별 JSON으로 저장된다.

주의:
- 실제 본문 글 생성은 여전히 v2.5 엔진이 담당한다.
- v2.6은 "출력 → GPT 입력" 사이의 전처리 레이어이다.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
PAYLOAD_DIR = BASE_DIR / "gpt_payload"

PROMPT_CONFIG_FILE = BASE_DIR / "OMG_prompt_layer_v1.json"
PRE_TEMPLATE_FILE = BASE_DIR / "OMG_pre_template_v26.json"


def safe_print(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[OMG 2.6] {ts} | {msg}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_draft_text(post: Dict[str, Any], template_cfg: Dict[str, Any]) -> str:
    """output JSON(title/sections/summary)을 하나의 텍스트 초안으로 합친다."""
    title_prefix = template_cfg.get("title_prefix", "")
    section_join = template_cfg.get("section_join", "\n\n")
    summary_prefix = template_cfg.get("summary_prefix", "\n\n요약: ")

    lines: List[str] = []

    title = post.get("title", "")
    if title:
        lines.append(f"{title_prefix}{title}")

    sections = post.get("sections", [])
    for sec in sections:
        heading = sec.get("heading", "").strip()
        body = sec.get("body", "").strip()
        if heading:
            lines.append(f"## {heading}")
        if body:
            lines.append(body)

    summary = post.get("summary", "").strip()
    if summary:
        lines.append(f"{summary_prefix}{summary}")

    return section_join.join(lines).strip()


def build_payload(
    post: Dict[str, Any],
    source_path: Path,
    prompt_cfg: Dict[str, Any],
    template_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """단일 output JSON을 GPT 페이로드 구조로 변환한다."""
    flavor = post.get("flavor", "")
    title = post.get("title", "")
    sections = post.get("sections", [])
    summary = post.get("summary", "")

    draft_text = build_draft_text(post, template_cfg)

    meta = {
        "flavor": flavor,
        "title": title,
        "section_count": len(sections),
        "source_file": source_path.name,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    payload = {
        "version": "2.6",
        "lang": prompt_cfg.get("language", "ko"),
        "meta": meta,
        "system_prompt": prompt_cfg.get("system_prompt", ""),
        "user_prompt_template": prompt_cfg.get("user_prompt_template", ""),
        "style": prompt_cfg.get("style", {}),
        "draft_content": draft_text,
        "summary": summary,
    }
    return payload


def main() -> None:
    safe_print("OmegaEngine v2.6 Pre-GPT Layer started.")

    if not OUTPUT_DIR.exists():
        safe_print(f"output 폴더가 없음: {OUTPUT_DIR}")
        return

    # 설정 로드
    prompt_cfg = load_json(PROMPT_CONFIG_FILE)
    template_cfg = load_json(PRE_TEMPLATE_FILE)
    safe_print(f"Loaded prompt config: {PROMPT_CONFIG_FILE.name}")
    safe_print(f"Loaded template config: {PRE_TEMPLATE_FILE.name}")

    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)

    count = 0
    for path in OUTPUT_DIR.glob("*.json"):
        try:
            post = load_json(path)
        except Exception as e:
            safe_print(f"JSON 로드 실패: {path.name} ({e})")
            continue

        payload = build_payload(post, path, prompt_cfg, template_cfg)
        out_name = f"{path.stem}_gpt_payload.json"
        out_path = PAYLOAD_DIR / out_name
        save_json(out_path, payload)
        count += 1

    safe_print(f"총 변환된 페이로드 수: {count}")
    safe_print("OmegaEngine v2.6 Pre-GPT Layer finished.")


if __name__ == "__main__":
    main()
