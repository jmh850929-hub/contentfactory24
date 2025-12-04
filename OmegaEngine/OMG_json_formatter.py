from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Optional


###############################################
# OmegaEngine 2.4 — JSON Output Formatter
# - NOMAD / ControlCore에서 사용
# - 포스팅 결과를 구조화된 JSON으로 저장
###############################################


def ensure_dir(path: Path):
    """폴더 없으면 생성"""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


def save_post_json(
    output_root: Path,
    title: str,
    flavor: str,
    sections: List[Dict[str, Any]],
    summary: str,
    image_map: Dict[str, str],
    post_id: Optional[int] = None,
    client_name: str = "",
    version: str = "2.4",
):
    """
    구조화된 포스팅 결과를 JSON으로 저장.
    NOMAD / ControlCore / Scheduler 영역에서 사용 가능.
    """

    ensure_dir(output_root)

    # 파일명: 2024_11_28_오후02_레슨공간.json 형태
    safe_title = title.replace(" ", "_").replace("/", "_")
    out_file = output_root / f"{safe_title}.json"

    data = {
        "version": version,
        "client": client_name,
        "title": title,
        "summary": summary,
        "flavor": flavor,
        "sections": sections,
        "image_map": image_map,
        "post_id": post_id,
    }

    with out_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"[json_formatter] saved → {out_file}")
    return out_file
