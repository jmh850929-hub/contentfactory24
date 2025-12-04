from __future__ import annotations
import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# default dynamic rules path
DYNAMIC_RULES_PATH_DEFAULT = os.path.join("..", "dynamic", "dynamic_rules.json")

def load_dynamic_rules(path: Optional[str] = None) -> Dict[str, Any]:
    if path is None:
        path = DYNAMIC_RULES_PATH_DEFAULT

    rules: Dict[str, Any] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                rules = json.load(f)
        except Exception:
            rules = {}

    rules.setdefault("min_sections", 4)
    rules.setdefault("max_sections", 7)
    rules.setdefault("target_chars_per_section", 450)
    rules.setdefault("fallback_enabled", True)
    rules.setdefault("flavor_overrides", {})

    return rules

def _resolve_section_count(img_count: int, rules: Dict[str, Any]) -> int:
    min_sec = int(rules.get("min_sections", 4))
    max_sec = int(rules.get("max_sections", 7))
    base = img_count + 2
    count = max(min_sec, base)
    count = min(count, max_sec)
    return count

def _choose_flavor_rules(flavor: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    overrides = rules.get("flavor_overrides", {}) or {}
    flavor_rule = overrides.get(flavor, {})
    merged = dict(rules)
    merged.update(flavor_rule)
    return merged

def _build_paragraph_segments(flavor: str) -> Tuple[List[str], List[str], List[str]]:
    intro_parts = [
        "오늘 공간에서 느껴지는 차분한 공기와 조용한 긴장감은,",
        "악기와 가구가 가지런히 놓인 실내 풍경은,",
        "사진 속 피아노와 주변 환경이 전해주는 첫인상은,",
        "입실 직후 느껴지는 조용한 숨소리와 미세한 소음들까지,",
    ]

    common_body = [
        "학습자가 음악에 집중할 수 있도록 시선을 분산시키는 요소들을 최대한 줄여 주고,",
        "소리의 반사와 잔향을 적절히 조절하여 연주자의 작은 뉘앙스까지 드러나게 해 주며,",
        "교사와 학생이 서로의 호흡을 맞추기 쉬운 동선과 배치를 제공하고,",
        "일관된 온도와 조명이 유지되어 장시간 머물러도 피로감이 덜하도록 설계되어 있으며,",
        "악보를 펼쳐두기 좋은 책상 높이와 의자 높이가 자연스럽게 맞춰져 있어,",
    ]

    if flavor == "piano_lesson":
        flavor_body = [
            "학생이 긴장보다는 기대에 가까운 감정을 느끼도록, 시각적인 안정감을 우선으로 두고 있고,",
            "레슨 중 대화를 방해하지 않도록 소음이 차단된 구조를 채택하고 있으며,",
            "교사가 손가락 모양이나 자세를 세밀하게 관찰할 수 있게 충분한 공간 여유를 두고 있고,",
            "첫 방문 학생도 바로 자리를 찾을 수 있도록 동선이 단순하게 구성되어 있다는 점이 돋보이며,",
        ]
        closing_pool = [
            "이러한 요소들이 함께 어우러져, 학생이 매주 이 공간에서 자연스럽게 연습 루틴을 쌓아갈 수 있는 기반이 된다.",
            "결국 이 공간은 단순한 연습실이 아니라, 음악을 통해 자신감을 쌓아가는 작은 플랫폼 역할을 하게 된다.",
            "그 덕분에 이곳에서의 레슨은 '숙제'가 아니라, 스스로 찾아오고 싶은 시간으로 기억되기 쉽다.",
        ]
    else:
        flavor_body = [
            "실제 연주자뿐 아니라 보호자나 방문객도 편안하게 머물 수 있도록 좌석과 동선이 구성되어 있고,",
            "악보·교재·부가 교구들을 깔끔하게 정리해 둘 수 있는 수납 구조가 마련되어 있으며,",
            "공간 전체의 톤을 과하지 않게 통일하여, 사진으로 기록했을 때에도 정돈된 인상을 남기고,",
            "간접 조명과 자연광을 적절히 섞어, 하루 중 어느 시간대에 촬영해도 안정적인 밝기를 확보할 수 있게 설계되어 있으며,",
        ]
        closing_pool = [
            "이런 구성 덕분에 이 공간은 '단순한 연습방'을 넘어, 하루의 기록을 남기고 싶은 장면으로 자주 선택된다.",
            "그 결과, 사용자는 이곳을 기능적인 작업 공간을 넘어, 마음을 정리하고 생각을 정돈하는 장소로 경험하게 된다.",
            "따라서 사진 한 장만 보더라도, 이 공간이 얼마나 많은 순간들을 담아왔는지 자연스럽게 상상하게 된다.",
        ]

    return intro_parts, common_body + flavor_body, closing_pool

def _generate_paragraph(idx: int, flavor: str, target_chars: int) -> str:
    intro_parts, body_parts, closing_pool = _build_paragraph_segments(flavor)
    random.shuffle(intro_parts)
    random.shuffle(body_parts)

    selected = []
    selected.append(intro_parts[0])

    body_count = random.randint(3, 4)
    selected.extend(body_parts[:body_count])

    closing = random.choice(closing_pool)
    selected.append(closing)

    paragraph = " ".join(selected).strip()

    if len(paragraph) < target_chars * 0.7:
        extra = " 공간의 작은 디테일 하나까지도 소리에 영향을 준다는 점을 고려하면, 이러한 구성은 단순한 인테리어를 넘어 '악기의 일부'처럼 작동하게 된다."
        paragraph += " " + extra

    if len(paragraph) > target_chars * 1.5:
        paragraph = paragraph[: int(target_chars * 1.5)].rsplit(" ", 1)[0] + "..."

    return paragraph

def build_sections(images: List[Dict[str, Any]], flavor: str, rules: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    if rules is None:
        rules = load_dynamic_rules()

    rules = _choose_flavor_rules(flavor, rules)
    img_count = len(images)
    target_chars = int(rules.get("target_chars_per_section", 450))

    section_count = _resolve_section_count(img_count, rules)

    sections: List[Dict[str, Any]] = []
    headings = {
        "piano_lesson": [
            "첫인상과 레슨 분위기",
            "학생이 머무는 공간의 구조",
            "소리에 영향을 주는 요소들",
            "레슨 동선과 교사 시야",
            "집중을 돕는 환경 디테일",
            "장기 레슨을 고려한 구성",
            "공간이 남기는 정서적 여운",
        ],
        "piano_info": [
            "공간이 전해주는 기본 인상",
            "피아노와 주변 환경의 조화",
            "촬영에 적합한 빛과 구도",
            "정리된 악보와 수납 구조",
            "방문자가 체감하는 편안함",
            "기록을 남기기 좋은 포인트",
            "일상 속 작은 공연장 같은 느낌",
        ],
    }

    heading_pool = headings.get(flavor, headings["piano_info"])

    for idx in range(section_count):
        heading = heading_pool[idx] if idx < len(heading_pool) else f"섹션 {idx+1}"
        body = _generate_paragraph(idx, flavor, target_chars)

        sections.append({
            "index": idx + 1,
            "heading": heading,
            "body": body,
        })

    return sections

def build_article(images: List[Dict[str, Any]], flavor: str, rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if rules is None:
        rules = load_dynamic_rules()

    sections = build_sections(images, flavor, rules)

    summary_parts = []
    for s in sections[:2]:
        summary_parts.append(s["body"].split(" ")[:18])
    summary = " ".join(" ".join(p) for p in summary_parts)

    return {
        "flavor": flavor,
        "section_count": len(sections),
        "sections": sections,
        "summary": summary,
    }
