#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WR_webrack_v1_0.py

CAPS WebRack v1.0
----------------------------------------
역할:
- CAPS Scheduler/OmegaEngine이 사용할 HTML 출력 레이어의 "골격"을 생성한다.
- 각 사이트별 site-dist/{site_id}/index.html 을 생성하여
  DeployBridge가 배포할 수 있는 정적 파일 구조를 만든다.

구조:
- config/webrack_sites.json : 사이트별 설정 (처음 실행 시 템플릿 자동 생성)
- logs/render_log_YYYYMMDD.txt : 렌더링 로그
- site-dist/{site_id}/index.html : 실제 HTML 출력 위치

향후 확장:
- Scheduler/OmegaEngine이 이 모듈을 호출하여 동적으로 콘텐츠를 주입할 수 있다.
- 현재 v1.0은 정적 골격 템플릿을 생성하는 스텁 엔진이다.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


# -----------------------------------------------------
# 메타 정보
# -----------------------------------------------------
WEBRACK_VERSION = "1.0.0"
MODULE_NAME = "WebRack"


# -----------------------------------------------------
# 데이터 모델
# -----------------------------------------------------

@dataclass
class SiteInfo:
    site_id: str
    title: str
    description: str
    url: str


# -----------------------------------------------------
# WebRack 본체
# -----------------------------------------------------

class WebRack:
    """
    WebRack v1.0
    - webrack_sites.json 을 읽어 사이트별 HTML 골격을 생성한다.
    - site-dist/{site_id}/index.html 구조를 만들어 DeployBridge와 연결된다.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent

        # 디렉터리
        self.config_dir = self.base_dir / "config"
        self.logs_dir = self.base_dir / "logs"
        self.dist_dir = self.base_dir / "site-dist"

        # 설정 파일
        self.sites_config_path = self.config_dir / "webrack_sites.json"

        # 내부 상태
        self.sites: Dict[str, SiteInfo] = {}

        self._ensure_directories()
        self._ensure_default_sites_config()
        self._load_sites()

    # -------------------------------------------------
    # 디렉터리 / 설정
    # -------------------------------------------------
    def _ensure_directories(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.dist_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_default_sites_config(self) -> None:
        """
        webrack_sites.json 이 없으면 기본 템플릿을 생성한다.
        우현이가 도메인/제목/설명을 수정해서 사용하면 된다.
        """
        if self.sites_config_path.exists():
            return

        default_config = {
            "version": "1.0",
            "description": "WebRack v1.0 기본 사이트 설정 템플릿",
            "sites": {
                "01-sangsangpiano": {
                    "title": "상상피아노",
                    "description": "상상피아노 – 피아노 레슨 & 연습실",
                    "url": "https://01-sangsangpiano.content-factory.blog"
                },
                "02-jay-gongbang": {
                    "title": "제이공방",
                    "description": "제이공방 – 수공예 & 공방 체험",
                    "url": "https://02-jay-gongbang.content-factory.blog"
                },
                "rack-random": {
                    "title": "랜덤 인포 랙",
                    "description": "랜덤 비상업용 포스팅 WebRack",
                    "url": "https://rack-random.content-factory.blog"
                }
            }
        }

        with open(self.sites_config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

    def _load_sites(self) -> None:
        if not self.sites_config_path.exists():
            raise FileNotFoundError(f"webrack_sites.json 이 없습니다: {self.sites_config_path}")

        with open(self.sites_config_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        sites_raw = raw.get("sites", {})
        sites: Dict[str, SiteInfo] = {}

        for site_id, info in sites_raw.items():
            sites[site_id] = SiteInfo(
                site_id=site_id,
                title=info.get("title", site_id),
                description=info.get("description", ""),
                url=info.get("url", ""),
            )

        self.sites = sites

    # -------------------------------------------------
    # 로깅
    # -------------------------------------------------
    def _log(self, message: str) -> None:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        log_file = self.logs_dir / f"render_log_{date_str}.txt"

        line = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)

        print(line, end="")

    # -------------------------------------------------
    # HTML 템플릿 생성
    # -------------------------------------------------
    def _build_html(self, site: SiteInfo) -> str:
        """
        v1.0용 기본 HTML 골격.
        추후 Scheduler/OmegaEngine이 본문 콘텐츠를 채워넣는 구조로 확장 가능.
        """
        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>{site.title}</title>
    <meta name="description" content="{site.description}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- CAPS WebRack v{WEBRACK_VERSION} -->
</head>
<body>
    <header>
        <h1>{site.title}</h1>
        <p>{site.description}</p>
    </header>

    <main>
        <!-- CAPS Scheduler / OmegaEngine 가 생성하는 본문 콘텐츠가 들어갈 영역 -->
        <section>
            <h2>콘텐츠 준비 중</h2>
            <p>이 페이지는 CAPS WebRack v{WEBRACK_VERSION} 을 통해 생성된 기본 템플릿입니다.</p>
        </section>
    </main>

    <footer>
        <p>Powered by CAPS WebRack v{WEBRACK_VERSION}</p>
        <p>URL: {site.url}</p>
    </footer>
</body>
</html>
"""

    def render_site(self, site_id: str) -> Path:
        """
        특정 site_id에 대해 site-dist/{site_id}/index.html 을 생성한다.
        """
        if site_id not in self.sites:
            raise ValueError(f"알 수 없는 site_id 입니다: {site_id}")

        site = self.sites[site_id]
        target_dir = self.dist_dir / site_id
        target_dir.mkdir(parents=True, exist_ok=True)

        html_path = target_dir / "index.html"
        html_content = self._build_html(site)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self._log(f"[{site_id}] index.html 생성 완료: {html_path}")
        return html_path

    def render_all(self) -> None:
        """
        등록된 모든 사이트에 대해 HTML을 생성한다.
        """
        for site_id in self.sites.keys():
            self.render_site(site_id)

    # -------------------------------------------------
    # 요약 출력
    # -------------------------------------------------
    def print_site_summary(self) -> None:
        print(f"[{MODULE_NAME} v{WEBRACK_VERSION}] 등록된 사이트 목록:")
        for site_id, site in self.sites.items():
            print(f"- {site_id:16s} | title={site.title} | url={site.url}")


# -----------------------------------------------------
# CLI 엔트리 포인트
# -----------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{MODULE_NAME} v{WEBRACK_VERSION} - site-dist HTML 생성 엔진"
    )
    parser.add_argument(
        "--site",
        type=str,
        required=False,
        help="렌더링할 사이트 ID (예: 01-sangsangpiano, 02-jay-gongbang, rack-random)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="등록된 모든 사이트에 대해 HTML 생성"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="등록된 사이트 목록만 출력하고 종료"
    )
    return parser.parse_args()


def main() -> None:
    wr = WebRack()
    args = parse_args()

    if args.list:
        wr.print_site_summary()
        return

    if args.all:
        wr.render_all()
        return

    if args.site:
        wr.render_site(args.site)
        return

    # 인자가 아무것도 없으면 목록만 보여주고 사용법 안내
    wr.print_site_summary()
    print("\n--site 또는 --all 옵션으로 HTML 생성 작업을 실행할 수 있습니다.")


if __name__ == "__main__":
    main()
