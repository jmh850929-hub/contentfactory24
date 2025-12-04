#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OMG_omega_engine_v1_0.py

CAPS OmegaEngine LTS v1.0 (정식 완성형 뼈대)
----------------------------------------
역할:
- CAPS 스케줄러가 사용할 "콘텐츠 생성 엔진"의 LTS 기준 뼈대.
- 실제 텍스트 생성 로직은 스텁(stub)으로 두고,
  향후 AutoSync가 이 모듈을 기반으로 기능을 확장/교체할 수 있게 설계한다.

구조:
- config/omega_config.json         : 기본 설정 (없으면 자동 생성)
- templates/base_template.txt      : 기본 콘텐츠 템플릿
- queue/                           : 생성 대기 작업(.json) 폴더
- output/                          : 생성 결과 저장 폴더
- logs/omega_log_YYYYMMDD.txt      : 로그 기록

CLI:
- --summary : 현재 설정 요약
- --run-once : 큐에서 1개 작업만 처리
- --run-all  : 큐의 모든 작업 처리
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


OMEGA_VERSION = "1.0.0"
MODULE_NAME = "OmegaEngineLTS"


@dataclass
class OmegaJob:
    job_id: str
    site_id: str
    post_type: str
    title: str
    payload: Dict[str, Any]


class OmegaEngineLTS:
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        # 기본 베이스 디렉터리 = 이 파일이 위치한 폴더
        self.base_dir = base_dir or Path(__file__).resolve().parent

        # 하위 디렉터리
        self.config_dir = self.base_dir / "config"
        self.templates_dir = self.base_dir / "templates"
        self.queue_dir = self.base_dir / "queue"
        self.output_dir = self.base_dir / "output"
        self.logs_dir = self.base_dir / "logs"

        # 파일 경로
        self.config_path = self.config_dir / "omega_config.json"
        self.base_template_path = self.templates_dir / "base_template.txt"

        # 설정
        self.config: Dict[str, Any] = {}

        self._ensure_directories()
        self._ensure_default_files()
        self._load_config()

    # ─────────────────────────────────────
    # 디렉터리 / 초기 파일
    # ─────────────────────────────────────
    def _ensure_directories(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_default_files(self) -> None:
        """기본 설정/템플릿 파일 없으면 생성"""
        if not self.config_path.exists():
            default_conf = {
                "version": "1.0",
                "description": "OmegaEngine LTS v1.0 기본 설정",
                "default_language": "ko",
                "default_tone": "정보성",
                "max_body_length": 1500
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default_conf, f, indent=2, ensure_ascii=False)

        if not self.base_template_path.exists():
            tmpl = (
                "{title}\n"
                "==============================\n\n"
                "[개요]\n"
                "{intro}\n\n"
                "[본문]\n"
                "{body}\n\n"
                "[마무리]\n"
                "{outro}\n"
                "\n(생성 엔진: OmegaEngine LTS v" + OMEGA_VERSION + ")\n"
            )
            with open(self.base_template_path, "w", encoding="utf-8") as f:
                f.write(tmpl)

    def _load_config(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    # ─────────────────────────────────────
    # 로깅
    # ─────────────────────────────────────
    def _log(self, msg: str) -> None:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        log_path = self.logs_dir / f"omega_log_{date_str}.txt"
        line = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
        print(line, end="")

    # ─────────────────────────────────────
    # 큐 로딩
    # ─────────────────────────────────────
    def _load_jobs_from_queue(self) -> List[OmegaJob]:
        """
        queue 디렉터리의 *.json 파일을 읽어서 OmegaJob 리스트로 변환.
        파일 형식 예:
        {
          "job_id": "20251201_0001",
          "site_id": "01-sangsangpiano",
          "post_type": "info",
          "title": "상상피아노 레슨 안내",
          "payload": {
              "intro": "...",
              "body": "...",
              "outro": "..."
          }
        }
        """
        jobs: List[OmegaJob] = []
        for path in sorted(self.queue_dir.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                job = OmegaJob(
                    job_id=raw.get("job_id", path.stem),
                    site_id=raw.get("site_id", ""),
                    post_type=raw.get("post_type", "generic"),
                    title=raw.get("title", "제목 없음"),
                    payload=raw.get("payload", {})
                )
                jobs.append(job)
            except Exception as e:
                self._log(f"[ERROR] 큐 파일 읽기 실패: {path} | {e}")
        return jobs

    # ─────────────────────────────────────
    # 스텁 텍스트 생성 로직
    # ─────────────────────────────────────
    def _generate_text(self, job: OmegaJob) -> str:
        """
        v1.0에서는 실제 LLM 호출 대신 스텁 텍스트 생성.
        이후 AutoSync가 이 부분을 교체/확장하게 될 예정.
        """
        intro = job.payload.get("intro", f"{job.site_id}에 대한 안내 글입니다.")
        body = job.payload.get(
            "body",
            f"{job.post_type} 유형의 게시글입니다. "
            f"이 영역은 AutoSync 이후에 실제 생성 로직으로 교체될 예정입니다."
        )
        outro = job.payload.get(
            "outro",
            "오늘도 방문해 주셔서 감사합니다."
        )

        try:
            with open(self.base_template_path, "r", encoding="utf-8") as f:
                tmpl = f.read()
        except Exception:
            tmpl = "{title}\n\n{intro}\n\n{body}\n\n{outro}\n"

        text = tmpl.format(
            title=job.title,
            intro=intro,
            body=body,
            outro=outro
        )

        # 길이 제한
        max_len = int(self.config.get("max_body_length", 1500))
        if len(text) > max_len:
            text = text[:max_len] + "\n...\n(본문이 LTS 기본 길이 제한으로 잘렸습니다.)"
        return text

    # ─────────────────────────────────────
    # 결과 저장
    # ─────────────────────────────────────
    def _save_result(self, job: OmegaJob, content: str) -> Path:
        today = datetime.now().strftime("%Y%m%d")
        site_dir = self.output_dir / job.site_id / today
        site_dir.mkdir(parents=True, exist_ok=True)

        out_path = site_dir / f"{job.job_id}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

        return out_path

    # ─────────────────────────────────────
    # 큐 작업 1개 처리
    # ─────────────────────────────────────
    def process_one_job(self) -> None:
        jobs = self._load_jobs_from_queue()
        if not jobs:
            self._log("[INFO] 처리할 큐 작업이 없습니다.")
            return

        job = jobs[0]
        self._log(f"[INFO] 작업 처리 시작: job_id={job.job_id}, site_id={job.site_id}")
        content = self._generate_text(job)
        out_path = self._save_result(job, content)
        self._log(f"[INFO] 작업 처리 완료: {out_path}")

        # 처리 완료된 큐 파일은 .done.json 으로 변경
        src_path = self.queue_dir / f"{job.job_id}.json"
        if src_path.exists():
            done_path = self.queue_dir / f"{job.job_id}.done.json"
            src_path.rename(done_path)

    # ─────────────────────────────────────
    # 큐 전체 처리
    # ─────────────────────────────────────
    def process_all_jobs(self) -> None:
        jobs = self._load_jobs_from_queue()
        if not jobs:
            self._log("[INFO] 처리할 큐 작업이 없습니다.")
            return

        self._log(f"[INFO] 총 {len(jobs)}개 작업 처리 시작")
        for job in jobs:
            self._log(f"[INFO] 작업 처리 시작: job_id={job.job_id}, site_id={job.site_id}")
            content = self._generate_text(job)
            out_path = self._save_result(job, content)
            self._log(f"[INFO] 작업 처리 완료: {out_path}")

            src_path = self.queue_dir / f"{job.job_id}.json"
            if src_path.exists():
                done_path = self.queue_dir / f"{job.job_id}.done.json"
                src_path.rename(done_path)

        self._log("[INFO] 모든 큐 작업 처리 완료")

    # ─────────────────────────────────────
    # 요약 출력
    # ─────────────────────────────────────
    def print_summary(self) -> None:
        print(f"[{MODULE_NAME} v{OMEGA_VERSION}] 설정 요약")
        print(f"- base_dir         : {self.base_dir}")
        print(f"- default_language : {self.config.get('default_language')}")
        print(f"- default_tone     : {self.config.get('default_tone')}")
        print(f"- max_body_length  : {self.config.get('max_body_length')}")
        print(f"- queue_dir        : {self.queue_dir}")
        print(f"- output_dir       : {self.output_dir}")
        print(f"- templates_dir    : {self.templates_dir}")
        print(f"- logs_dir         : {self.logs_dir}")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{MODULE_NAME} v{OMEGA_VERSION} - CAPS OmegaEngine LTS"
    )
    parser.add_argument("--summary", action="store_true", help="설정 요약 출력")
    parser.add_argument("--run-once", action="store_true", help="큐에서 1개 작업 처리")
    parser.add_argument("--run-all", action="store_true", help="큐의 모든 작업 처리")
    return parser.parse_args()


def main() -> None:
    engine = OmegaEngineLTS()
    args = parse_args()

    if args.summary:
        engine.print_summary()
        return

    if args.run_all:
        engine.process_all_jobs()
        return

    if args.run_once:
        engine.process_one_job()
        return

    # 인자 없으면 요약만 출력
    engine.print_summary()


if __name__ == "__main__":
    main()
