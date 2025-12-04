#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SCH_scheduler_lts_v1_0.py

CAPS Scheduler LTS v1.0 (정식 LTS 버전)
----------------------------------------
역할:
- CAPS 공식 스케줄 규칙(LTS)을 기반으로 매일 포스팅 '작업 요청'을 생성한다.
- 생성된 작업은 OmegaEngine LTS가 텍스트 생성에 사용한다.
- 기존 스케줄러 v1.5~v2.0 기능은 모두 '기능 레이어'로 보존하고,
  LTS 뼈대는 AutoSync 패치/확장 전용으로 만든다.

구조:
- config/scheduler_config.json        → 기본 설정
- queue/                              → OmegaEngine 작업 요청이 생성되는 폴더
- logs/scheduler_log_YYYYMMDD.txt     → 스케줄러 실행 로그
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


SCHEDULER_LTS_VERSION = "1.0.0"
MODULE_NAME = "SchedulerLTS"


class SchedulerLTS:
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent

        # 폴더 구조
        self.config_dir = self.base_dir / "config"
        self.queue_dir = self.base_dir / "queue"
        self.logs_dir = self.base_dir / "logs"

        # 파일 경로
        self.config_path = self.config_dir / "scheduler_config.json"

        # 설정 로드 준비
        self.config: Dict[str, Any] = {}

        self._ensure_directories()
        self._ensure_default_config()
        self._load_config()

        # LTS 스케줄 규칙
        self.fixed_commercial_type = "commercial"
        self.random_type_pool = [
            "info", "local_event", "operator_story", "industry_trend",
            "faq", "local_place", "equipment_info", "general_info",
            "weekly_brief", "review_summary", "tip", "reference"
        ]

    # ---------------------------------------------------------
    # 초기 설정
    # ---------------------------------------------------------
    def _ensure_directories(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_default_config(self) -> None:
        if self.config_path.exists():
            return

        default_conf = {
            "version": "1.0",
            "description": "Scheduler LTS v1.0 기본 설정",
            "site_id": "01-sangsangpiano",
            "commercial_title": "상업성 홍보 포스팅",
            "commercial_intro": "상업성 콘텐츠 기본 소개입니다.",
            "commercial_body": "상업성 콘텐츠 본문입니다.",
            "commercial_outro": "문의는 언제나 환영합니다.",
            "random_post_title": "비상업성 랜덤 콘텐츠",
            "default_intro": "기본 소개 문장",
            "default_body": "기본 본문 내용 (AutoSync 패치 예정)",
            "default_outro": "감사합니다."
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(default_conf, f, indent=2, ensure_ascii=False)

    def _load_config(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    # ---------------------------------------------------------
    # 로깅
    # ---------------------------------------------------------
    def _log(self, msg: str) -> None:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        log_path = self.logs_dir / f"scheduler_log_{date_str}.txt"
        line = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
        print(line, end="")

    # ---------------------------------------------------------
    # 큐 작업 1개 생성
    # ---------------------------------------------------------
    def _create_job(self, post_type: str, title: str, intro: str, body: str, outro: str) -> Path:
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_file = self.queue_dir / f"{job_id}.json"

        job = {
            "job_id": job_id,
            "site_id": self.config["site_id"],
            "post_type": post_type,
            "title": title,
            "payload": {
                "intro": intro,
                "body": body,
                "outro": outro
            }
        }

        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(job, f, indent=2, ensure_ascii=False)

        return job_file

    # ---------------------------------------------------------
    # 오늘 스케줄 생성
    # ---------------------------------------------------------
    def run_today_schedule(self) -> None:
        # 1) 상업성 1개 고정
        self._log("[INFO] 상업성 포스팅 생성 시작")
        com_path = self._create_job(
            post_type="commercial",
            title=self.config["commercial_title"],
            intro=self.config["commercial_intro"],
            body=self.config["commercial_body"],
            outro=self.config["commercial_outro"]
        )
        self._log(f"[OK] 상업성 포스팅 큐 생성: {com_path}")

        # 2) 비상업성 랜덤 1개
        random_type = random.choice(self.random_type_pool)
        self._log(f"[INFO] 비상업성 랜덤 선택: {random_type}")

        rand_path = self._create_job(
            post_type=random_type,
            title=self.config["random_post_title"],
            intro=self.config["default_intro"],
            body=self.config["default_body"],
            outro=self.config["default_outro"]
        )
        self._log(f"[OK] 비상업성 포스팅 큐 생성: {rand_path}")

        self._log("[DONE] 오늘 스케줄 생성 완료")

    # ---------------------------------------------------------
    # 전체 강제 생성 (테스트용)
    # ---------------------------------------------------------
    def run_force_all(self) -> None:
        self._log("[INFO] 전체 스케줄 강제 생성 시작")

        # 상업성
        self._create_job(
            post_type="commercial",
            title=self.config["commercial_title"],
            intro=self.config["commercial_intro"],
            body=self.config["commercial_body"],
            outro=self.config["commercial_outro"]
        )

        # 12종 비상업성 모두 생성
        for t in self.random_type_pool:
            self._create_job(
                post_type=t,
                title=f"랜덤({t}) 포스팅",
                intro=self.config["default_intro"],
                body=self.config["default_body"],
                outro=self.config["default_outro"]
            )

        self._log("[DONE] 전체 비상업성 스케줄 강제 생성 완료")

    # ---------------------------------------------------------
    # 요약 출력
    # ---------------------------------------------------------
    def print_summary(self) -> None:
        print(f"[{MODULE_NAME} v{SCHEDULER_LTS_VERSION}] 설정 요약")
        print(f"- site_id           : {self.config['site_id']}")
        print(f"- commercial_title  : {self.config['commercial_title']}")
        print(f"- queue_dir         : {self.queue_dir}")
        print(f"- logs_dir          : {self.logs_dir}")
        print(f"- version           : {self.config['version']}")
        print()


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{MODULE_NAME} v{SCHEDULER_LTS_VERSION} - CAPS Scheduler LTS"
    )
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--force-all", action="store_true")
    return parser.parse_args()


def main() -> None:
    sch = SchedulerLTS()
    args = parse_args()

    if args.summary:
        sch.print_summary()
        return

    if args.force_all:
        sch.run_force_all()
        return

    if args.run:
        sch.run_today_schedule()
        return

    # 기본 출력
    sch.print_summary()


if __name__ == "__main__":
    main()
