#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CC_caps_core_v1_0.py

CAPS Core v1.0
- CAPS 직렬 파이프라인의 "두뇌" 역할
- LTS 규칙 + 모듈 상태를 읽고, AutoSync가 실행할 "계획(Plan)"을 생성한다.

역할 요약:
1) config/caps_lts_rules.json    # (옵션) LTS / 우선순위 / 정책
2) status/modules_status.json    # 현재 각 모듈 상태
3) plan/caps_core_plan.json      # AutoSync가 읽어갈 계획 출력
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional


# ─────────────────────────────────────────────
# 메타 정보
# ─────────────────────────────────────────────

CAPS_CORE_VERSION = "1.0.0"
CAPS_CORE_INTERNAL_NAME = "CAPS Core"


# ─────────────────────────────────────────────
# 데이터 모델
# ─────────────────────────────────────────────

@dataclass
class ModuleStatus:
    name: str
    current_version: str
    target_version: Optional[str]
    health: str  # e.g. "GREEN", "YELLOW", "RED"


@dataclass
class PlanItem:
    module: str
    action: str            # e.g. "PATCH", "CHECK_ONLY", "SKIP"
    priority: int          # 낮을수록 우선순위 높음 (0 > 10)
    reason: str
    target_version: Optional[str] = None


# ─────────────────────────────────────────────
# CAPS Core 본체
# ─────────────────────────────────────────────

class CapsCore:
    """
    CAPS Core
    - LTS 규칙 + 현재 모듈 상태를 바탕으로 "다음에 무엇을 할지"를 계획한다.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        # 기본 베이스 디렉터리 = 이 파일이 있는 폴더
        self.base_dir = base_dir or Path(__file__).resolve().parent

        # 하위 디렉터리
        self.config_dir = self.base_dir / "config"
        self.status_dir = self.base_dir / "status"
        self.plan_dir = self.base_dir / "plan"

        # 파일 경로
        self.lts_rules_path = self.config_dir / "caps_lts_rules.json"
        self.modules_status_path = self.status_dir / "modules_status.json"
        self.plan_output_path = self.plan_dir / "caps_core_plan.json"

        # 내부 상태
        self.lts_rules: Dict = {}
        self.modules: Dict[str, ModuleStatus] = {}
        self.plan_items: List[PlanItem] = []

        # LTS 직렬 의존성 순서 (Root Layer 제외: Nomad, Control Tower)
        # AutoSync → SafeGuard → VersionDocs → Scheduler/Omega → DeployBridge → WebRack → Image계층 → 모니터링/로그
        self.dependency_order = [
            "AutoSync",
            "SafeGuard",
            "VersionDocs",
            "Scheduler",
            "OmegaEngine",
            "DeployBridge",
            "WebRack",
            "ImageInference",
            "MonitoringPanel",
            "LogCenter",
        ]

    # ─────────────────────────────────────
    # 파일/디렉터리 유틸
    # ─────────────────────────────────────

    def _ensure_directories(self) -> None:
        """필요한 디렉터리가 없으면 생성."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.status_dir.mkdir(parents=True, exist_ok=True)
        self.plan_dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────
    # LTS 규칙 로딩
    # ─────────────────────────────────────

    def load_lts_rules(self) -> None:
        """
        LTS 규칙 파일을 읽는다.
        없으면 기본 규칙으로 초기화한다.
        """
        self._ensure_directories()

        if not self.lts_rules_path.exists():
            # 기본 규칙 (v1.0 템플릿)
            self.lts_rules = {
                "version": "1.0",
                "description": "Default LTS rules for CAPS Core v1.0",
                "serial_pipeline": self.dependency_order,
                "safe_state_required": True,
                "test_decoupling": True
            }
            # 초기 템플릿 저장 (나중에 수동/AutoSync로 수정 가능)
            with open(self.lts_rules_path, "w", encoding="utf-8") as f:
                json.dump(self.lts_rules, f, indent=2, ensure_ascii=False)
            return

        with open(self.lts_rules_path, "r", encoding="utf-8") as f:
            self.lts_rules = json.load(f)

    # ─────────────────────────────────────
    # 모듈 상태 로딩
    # ─────────────────────────────────────

    def load_modules_status(self) -> None:
        """
        각 모듈의 현재 상태를 읽는다.
        """
        if not self.modules_status_path.exists():
            raise FileNotFoundError(
                f"modules_status.json 이 없습니다: {self.modules_status_path}"
            )

        with open(self.modules_status_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        modules: Dict[str, ModuleStatus] = {}
        for name, info in raw.items():
            modules[name] = ModuleStatus(
                name=name,
                current_version=info.get("current_version", "0.0.0"),
                target_version=info.get("target_version"),
                health=info.get("health", "UNKNOWN")
            )
        self.modules = modules

    # ─────────────────────────────────────
    # 계획 저장
    # ─────────────────────────────────────

    def save_plan(self) -> None:
        """
        생성된 계획을 JSON으로 저장한다.
        AutoSync가 이 파일을 읽어 다음 패치를 수행한다.
        """
        self._ensure_directories()

        plan_dict = {
            "caps_core_version": CAPS_CORE_VERSION,
            "serial_order": self.dependency_order,
            "items": [asdict(item) for item in self.plan_items],
        }

        with open(self.plan_output_path, "w", encoding="utf-8") as f:
            json.dump(plan_dict, f, indent=2, ensure_ascii=False)

    # ─────────────────────────────────────
    # 계획 생성 로직 (핵심)
    # ─────────────────────────────────────

    def build_plan(self) -> None:
        """
        모듈 상태와 LTS 규칙을 기반으로 plan_items를 생성한다.
        Health → Version → 그 외 순서로 판단.
        """
        self.plan_items.clear()

        for index, module_name in enumerate(self.dependency_order):
            m = self.modules.get(module_name)
            if m is None:
                # 상태 정보가 없으면 일단 스킵
                self.plan_items.append(
                    PlanItem(
                        module=module_name,
                        action="SKIP",
                        priority=100 + index,
                        reason="status_missing"
                    )
                )
                continue

            # 기본 우선순위: dependency 순서 기준
            base_priority = index * 10

            # 1) Health 체크 우선
            if m.health == "RED":
                action = "PATCH"
                priority = base_priority      # 최우선
                reason = "health_red"
            elif m.health == "YELLOW":
                action = "PATCH"
                priority = base_priority + 5
                reason = "health_yellow"
            else:
                # GREEN 또는 기타 상태 → 버전 차이 확인
                if m.target_version and m.target_version != m.current_version:
                    action = "PATCH"
                    priority = base_priority + 7
                    reason = "version_mismatch"
                else:
                    action = "CHECK_ONLY"
                    priority = base_priority + 50
                    reason = "ok_no_action"

            self.plan_items.append(
                PlanItem(
                    module=m.name,
                    action=action,
                    priority=priority,
                    reason=reason,
                    target_version=m.target_version
                )
            )

        # 우선순위 정렬 (priority 오름차순)
        self.plan_items.sort(key=lambda x: x.priority)

    # ─────────────────────────────────────
    # 요약 출력
    # ─────────────────────────────────────

    def print_summary(self) -> None:
        """
        생성된 계획을 콘솔에 간단히 출력한다.
        """
        print(f"[{CAPS_CORE_INTERNAL_NAME} v{CAPS_CORE_VERSION}] 계획 요약")
        for item in self.plan_items:
            print(
                f"- {item.module:12s} | {item.action:10s} | "
                f"priority={item.priority:3d} | reason={item.reason} "
                f"| target={item.target_version}"
            )


# ─────────────────────────────────────────────
# 엔트리 포인트
# ─────────────────────────────────────────────

def main() -> None:
    core = CapsCore()
    core.load_lts_rules()
    core.load_modules_status()
    core.build_plan()
    core.save_plan()
    core.print_summary()


if __name__ == "__main__":
    main()
