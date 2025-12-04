#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB_deploy_bridge_v1_0.py

CAPS DeployBridge v1.0
----------------------------------------
역할:
- WebRack(또는 Scheduler)이 생성한 site-dist 폴더를
  실제 배포 대상으로 전달하는 "브릿지" 역할을 한다.
- 현재 버전(v1.0)은 로컬 폴더 복사 + 로그 기록까지 담당하는 스텁 엔진이며,
  이후 Netlify CLI / Git / API 연동의 기반이 된다.

구조:
- config/deploy_config.json : 사이트별 src/dst 경로 정의
- logs/deploy_log_YYYYMMDD.txt : 배포 로그
- out/{site_id}/ : 실제 배포용 파일이 쌓이는 위치

향후 AutoSync 연동:
- AutoSync가 이 모듈을 import하여 deploy_site(site_id) 를 호출함으로써
  패치 후 자동 배포를 수행할 수 있다.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


# -----------------------------------------------------
# 메타 정보
# -----------------------------------------------------
DEPLOY_BRIDGE_VERSION = "1.0.0"
MODULE_NAME = "DeployBridge"


# -----------------------------------------------------
# 데이터 모델
# -----------------------------------------------------

@dataclass
class SiteConfig:
    site_id: str
    src_dir: Path
    dst_root: Path  # site_id별 root (timestamp 하위에 실제 배포본이 쌓임)


# -----------------------------------------------------
# DeployBridge 본체
# -----------------------------------------------------

class DeployBridge:
    """
    DeployBridge v1.0
    - 사이트별 site-dist 폴더를 읽어와, 배포 대상(out) 폴더로 복사한다.
    - 추후 Netlify CLI / Git push / API 연동 시 이 클래스에 훅을 추가하면 된다.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent

        # 하위 디렉터리
        self.config_dir = self.base_dir / "config"
        self.logs_dir = self.base_dir / "logs"
        self.out_dir = self.base_dir / "out"

        # 설정 파일
        self.config_path = self.config_dir / "deploy_config.json"

        # 내부 상태
        self.site_configs: Dict[str, SiteConfig] = {}

        self._ensure_directories()
        self._ensure_default_config()
        self._load_config()

    # -------------------------------------------------
    # 디렉터리 / 설정
    # -------------------------------------------------
    def _ensure_directories(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_default_config(self) -> None:
        """
        deploy_config.json 이 없을 경우 기본 템플릿을 생성한다.
        우현이가 직접 경로를 수정해서 사용할 수 있다.
        """
        if self.config_path.exists():
            return

        # 기본값: WebRack의 site-dist 구조를 가정
        default_config = {
            "version": "1.0",
            "description": "DeployBridge v1.0 기본 설정 템플릿",
            "sites": {
                # 예시 3개 사이트 (필요 시 수정)
                "01-sangsangpiano": {
                    "src_dir": r"C:\A1-M2\WebRack\site-dist\01-sangsangpiano",
                    "dst_root": r"C:\A1-M2\DeployBridge\out\01-sangsangpiano"
                },
                "02-jay-gongbang": {
                    "src_dir": r"C:\A1-M2\WebRack\site-dist\02-jay-gongbang",
                    "dst_root": r"C:\A1-M2\DeployBridge\out\02-jay-gongbang"
                },
                "rack-random": {
                    "src_dir": r"C:\A1-M2\WebRack\site-dist\rack-random",
                    "dst_root": r"C:\A1-M2\DeployBridge\out\rack-random"
                }
            }
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

    def _load_config(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"deploy_config.json 이 없습니다: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        sites = raw.get("sites", {})
        configs: Dict[str, SiteConfig] = {}

        for site_id, info in sites.items():
            src_dir = Path(info.get("src_dir", "")).resolve()
            dst_root = Path(info.get("dst_root", "")).resolve()

            configs[site_id] = SiteConfig(
                site_id=site_id,
                src_dir=src_dir,
                dst_root=dst_root
            )

        self.site_configs = configs

    # -------------------------------------------------
    # 로깅
    # -------------------------------------------------
    def _log(self, message: str) -> None:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        log_file = self.logs_dir / f"deploy_log_{date_str}.txt"

        line = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)

        print(line, end="")

    # -------------------------------------------------
    # 배포 로직
    # -------------------------------------------------
    def deploy_site(self, site_id: str) -> Path:
        """
        특정 site_id에 대해 배포를 수행한다.
        - src_dir → dst_root/timestamp 로 전체 복사
        - 최종 복사된 경로를 반환한다.
        """
        if site_id not in self.site_configs:
            raise ValueError(f"알 수 없는 site_id 입니다: {site_id}")

        cfg = self.site_configs[site_id]

        if not cfg.src_dir.exists():
            raise FileNotFoundError(f"소스 디렉터리가 존재하지 않습니다: {cfg.src_dir}")

        # 타겟 루트 디렉터리 보장
        cfg.dst_root.mkdir(parents=True, exist_ok=True)

        # timestamp 기반 하위 폴더 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = cfg.dst_root / timestamp

        # 혹시라도 동일 폴더가 있을 경우를 대비
        idx = 1
        while target_dir.exists():
            target_dir = cfg.dst_root / f"{timestamp}_{idx}"
            idx += 1

        self._log(f"[{site_id}] 배포 시작: {cfg.src_dir} → {target_dir}")

        # 디렉터리 전체 복사
        shutil.copytree(cfg.src_dir, target_dir)

        self._log(f"[{site_id}] 배포 완료: {target_dir}")

        return target_dir

    # -------------------------------------------------
    # 요약 출력
    # -------------------------------------------------
    def print_site_summary(self) -> None:
        print(f"[{MODULE_NAME} v{DEPLOY_BRIDGE_VERSION}] 등록된 사이트 목록:")
        for site_id, cfg in self.site_configs.items():
            print(f"- {site_id:16s} | src={cfg.src_dir} | dst_root={cfg.dst_root}")


# -----------------------------------------------------
# 엔트리 포인트 (CLI)
# -----------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{MODULE_NAME} v{DEPLOY_BRIDGE_VERSION} - site-dist 배포 브릿지"
    )
    parser.add_argument(
        "--site",
        type=str,
        required=False,
        help="배포할 사이트 ID (예: 01-sangsangpiano, 02-jay-gongbang, rack-random)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="등록된 사이트 목록만 출력하고 종료"
    )
    return parser.parse_args()


def main() -> None:
    bridge = DeployBridge()
    args = parse_args()

    if args.list or not args.site:
        # 사이트 목록만 보여주고 끝낼 수도 있음
        bridge.print_site_summary()
        if not args.site:
            print("\n--site 옵션으로 배포할 사이트를 지정하면 실제 복사가 수행됩니다.")
            return

    # 실제 배포
    try:
        target = bridge.deploy_site(args.site)
        print(f"\n[{MODULE_NAME} v{DEPLOY_BRIDGE_VERSION}] 최종 배포 경로: {target}")
    except Exception as e:
        bridge._log(f"[ERROR] 배포 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
