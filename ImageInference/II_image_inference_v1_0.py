#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
II_image_inference_v1_0.py

CAPS ImageInference Module v1.0
----------------------------------------
역할:
- 이미지 품질 간단 분석(스텁 기반)
- 흐린 사진, 너무 어두운 사진, 너무 밝은 사진, 너무 작은 해상도,
  중복 이미지 감지
- Scheduler가 사용할 'good / bad' 이미지 분류 결과 생성

구조:
- config/inference_config.json (없으면 자동 생성)
- logs/inference_log_YYYYMMDD.txt
- input/   (테스트용)
- output/  (결과 저장)

향후 AutoSync 연동:
- AutoSync 패치 후, ImageInference.generate_report() 를 호출하여
  이미지 품질 분석을 자동 수행할 수 있음.
"""

from __future__ import annotations

import argparse
import json
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from PIL import Image, ImageStat


# -----------------------------------------------------
# 메타 정보
# -----------------------------------------------------
IMAGE_INFERENCE_VERSION = "1.0.0"
MODULE_NAME = "ImageInference"


# -----------------------------------------------------
# 데이터 모델
# -----------------------------------------------------

@dataclass
class ImageResult:
    good_images: List[str]
    bad_images: List[str]
    reason_map: Dict[str, List[str]]


# -----------------------------------------------------
# ImageInference 본체
# -----------------------------------------------------

class ImageInference:
    """
    ImageInference v1.0
    - 이미지 품질 기반 분류 엔진 (스텁 기반)
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent

        # 디렉터리
        self.config_dir = self.base_dir / "config"
        self.logs_dir = self.base_dir / "logs"
        self.input_dir = self.base_dir / "input"
        self.output_dir = self.base_dir / "output"

        # 설정 파일
        self.config_path = self.config_dir / "inference_config.json"

        # 내부 설정
        self.conf = {}

        self._ensure_directories()
        self._ensure_default_config()
        self._load_config()

    # -------------------------------------------------
    # 디렉터리 / 설정
    # -------------------------------------------------
    def _ensure_directories(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_default_config(self) -> None:
        if self.config_path.exists():
            return

        default_config = {
            "version": "1.0",
            "description": "ImageInference v1.0 기본 설정 템플릿",
            "auto_scan_dir": r"C:\A1-M2\ImageInference\input",
            "brightness_low_threshold": 30,
            "brightness_high_threshold": 220,
            "min_width": 300,
            "min_height": 300
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

    def _load_config(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.conf = json.load(f)

    # -------------------------------------------------
    # 로깅
    # -------------------------------------------------
    def _log(self, msg: str) -> None:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        log_path = self.logs_dir / f"inference_log_{date_str}.txt"

        line = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)

        print(line, end="")

    # -------------------------------------------------
    # 품질 분석
    # -------------------------------------------------
    def _hash_image(self, img_path: Path) -> str:
        h = hashlib.sha256()
        with open(img_path, "rb") as f:
            h.update(f.read())
        return h.hexdigest()

    def _analyze_image(self, img_path: Path) -> List[str]:
        """
        v1.0 스텁 기반 품질 분석:
        - brightness 평균값
        - 해상도 검사
        """
        reasons = []
        try:
            img = Image.open(img_path)
            stat = ImageStat.Stat(img.convert("L"))

            brightness = stat.mean[0]
            width, height = img.size

            # 밝기 검사
            if brightness < self.conf["brightness_low_threshold"]:
                reasons.append("too_dark")
            elif brightness > self.conf["brightness_high_threshold"]:
                reasons.append("too_bright")

            # 해상도 검사
            if width < self.conf["min_width"] or height < self.conf["min_height"]:
                reasons.append("low_resolution")

        except Exception as e:
            reasons.append("load_error")
            self._log(f"[ERROR] 이미지 로드 실패: {img_path} | {e}")

        return reasons

    # -------------------------------------------------
    # 메인 분석 엔진
    # -------------------------------------------------
    def scan_directory(self, dir_path: Path) -> ImageResult:
        """
        특정 디렉터리를 스캔하여 이미지 품질 분석 결과를 반환한다.
        """
        if not dir_path.exists():
            raise FileNotFoundError(f"스캔 대상 디렉터리가 존재하지 않습니다: {dir_path}")

        images = list(dir_path.glob("*.jpg")) + list(dir_path.glob("*.png"))
        reasons_map: Dict[str, List[str]] = {}
        good, bad = [], []

        seen_hashes = set()

        for img_path in images:
            img_name = img_path.name

            reason_list = self._analyze_image(img_path)

            # 중복 검사
            img_hash = self._hash_image(img_path)
            if img_hash in seen_hashes:
                reason_list.append("duplicate")
            else:
                seen_hashes.add(img_hash)

            if reason_list:
                bad.append(img_name)
                reasons_map[img_name] = reason_list
            else:
                good.append(img_name)

        result = ImageResult(
            good_images=good,
            bad_images=bad,
            reason_map=reasons_map
        )

        # 결과 저장
        result_path = self.output_dir / f"inference_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result.__dict__, f, indent=2, ensure_ascii=False)

        self._log(f"[완료] 분석 결과 저장: {result_path}")
        return result

    # -------------------------------------------------
    # CLI 요약
    # -------------------------------------------------
    def print_summary(self) -> None:
        print(f"[{MODULE_NAME} v{IMAGE_INFERENCE_VERSION}] 설정 요약:")
        print(f"- auto_scan_dir: {self.conf['auto_scan_dir']}")
        print(f"- bright_low : {self.conf['brightness_low_threshold']}")
        print(f"- bright_high: {self.conf['brightness_high_threshold']}")
        print(f"- min_size   : {self.conf['min_width']}x{self.conf['min_height']}")


# -----------------------------------------------------
# CLI 엔트리 포인트
# -----------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{MODULE_NAME} v{IMAGE_INFERENCE_VERSION} - CAPS 이미지 품질 분석 엔진"
    )
    parser.add_argument("--scan", type=str, help="지정 경로 이미지 분석")
    parser.add_argument("--auto", action="store_true", help="config.auto_scan_dir 자동 분석")
    parser.add_argument("--list", action="store_true", help="현재 설정 요약 출력")
    return parser.parse_args()


def main() -> None:
    ii = ImageInference()
    args = parse_args()

    if args.list:
        ii.print_summary()
        return

    if args.auto:
        target = Path(ii.conf["auto_scan_dir"])
        ii.scan_directory(target)
        return

    if args.scan:
        ii.scan_directory(Path(args.scan))
        return

    # 인자 없으면 설정 요약만
    ii.print_summary()


if __name__ == "__main__":
    main()
