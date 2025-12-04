from __future__ import annotations
import re
import random
from pathlib import Path


###############################################
# OmegaEngine 2.4 – TITLE BUILDER (완성판)
###############################################

"""
이 엔진의 목적:
- 기존 2.3의 단순 랜덤 제목에서 벗어나
- 상용화된 자연스러운 제목 생성
- 폴더명 + 학원명 + 사진 특징 → 자동 조합
- 언더바 제거, 숫자 제거, 의미만 남김
"""

# 제목 패턴 후보
TITLE_PATTERNS = [
    "{client} {topic} – 오늘의 공간 기록",
    "{client} {topic} – 조용한 하루의 한 장면",
    "{client} {topic} – 실제 레슨 분위기",
    "{topic} 살펴보기 – {client}",
    "{client} 교실 풍경 – {topic}",
    "{client} 레슨 공간 이야기 – {topic}",
    "{client} 일상 기록 – {topic}",
    "{topic} 공간 소개 – {client}",
]


# topic 후보 (피아노 사진 기반)
TOPIC_LESSON = [
    "피아노 레슨 공간",
    "학원 연습 자리",
    "교실 분위기",
    "연습실 한쪽 모습",
    "피아노가 놓인 자리",
    "수업이 이루어지던 공간",
]


def clean_folder_name(raw: str) -> str:
    """
    폴더명에서 숫자/언더바 제거하고 자연어 문구로 치환
    예: 01_상상피아노_악기_악보 → 상상피아노 악기 악보
    """
    raw = raw.replace("_", " ")
    raw = re.sub(r"\d+", "", raw).strip()
    raw = re.sub(r"\s+", " ", raw)
    return raw


def detect_topic_from_folder(folder_name: str) -> str:
    """
    폴더명에서 의미있는 토픽 자동 추출
    """
    base = folder_name.lower()

    if "악보" in base:
        return "악보 정리 공간"
    if "악기" in base:
        return "악기 보관·정리 공간"
    if "연습" in base:
        return "연습 공간"
    if "교실" in base:
        return "교실 내부"
    if "자리" in base:
        return "피아노 자리"

    # 기본 토픽
    return random.choice(TOPIC_LESSON)


def build_title(client_name: str, product_dir: Path) -> str:
    """
    최종 제목 생성:
    - 폴더명 기반 의미 추출
    - 학원명 + 토픽 + 제목 템플릿 조합
    """
    raw_folder = product_dir.name
    clean_name = clean_folder_name(raw_folder)
    topic = detect_topic_from_folder(clean_name)

    client_clean = clean_folder_name(client_name)

    pattern = random.choice(TITLE_PATTERNS)
    title = pattern.format(client=client_clean, topic=topic)

    # 공백 정리
    title = re.sub(r"\s+", " ", title).strip()

    return title

