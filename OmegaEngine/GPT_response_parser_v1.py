"""
GPT_response_parser_v1.py
GPT 엔진의 텍스트 응답을 final JSON으로 구조화하는 모듈
"""

from typing import Dict


def parse_gpt_text(raw_text: str, meta: Dict) -> Dict:
    """
    raw_text: GPT 최종 본문 텍스트
    meta    : gpt_payload의 meta 정보
    """
    title = meta.get("title") or "제목 미정"

    return {
        "title": title,
        "content_markdown": raw_text.strip(),
        "meta": meta
    }
