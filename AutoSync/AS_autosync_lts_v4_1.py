#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AS_autosync_lts_v4_1.py

CAPS AutoSync LTS v4.1 (정식 운영 + AutoSync Core + DeployBridge 연동 버전)
---------------------------------------------------------------------------
역할:
- CAPS Core가 만든 plan(caps_core_plan.json)을 읽고,
  필요한 모듈(VersionDocs, Scheduler, OmegaEngine, etc.)을
  우선순위에 따라 순서대로 실행한다.
- 모듈 패치 후 SafeGuard LTS를 호출하여 GREEN/RED 상태를 확인하고,
  로그와 state 파일에 기록한다.
- SafeGuard 최종 상태가 GREEN일 때만 AutoSync Core(autosync_core.autosync_run)를 호출한다.
- AutoSync Core는 내부에서 WebRack + DeployBridge(Netlify)까지 자동 실행한다.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


AUTOSYNC_VERSION = "4.1.0"
MODULE_NAME = "AutoSyncLTS"


# ─────────────────────────────────────────────
# 데이터 모델
# ─────────────────────────────────────────────

@dataclass
class PlanItem:
    module: str
    action: str
    priority: int
    reason: str
    target_version: Optional[str]


@dataclass
class PatchResult:
    module: str
    action: str
    success: bool
    returncode: int
    message: str


# ─────────────────────────────────────────────
# AutoSync LTS 본체
# ─────────────────────────────────────────────

class AutoSyncLTS:
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent

        # 폴더 구조
        self.config_dir = self.base_dir / "config"
        self.logs_dir = self.base_dir / "logs"
        self.state_dir = self.base_dir / "state"

        # 파일 경로
        self.config_path = self.config_dir / "autosync_config.json"
        self.state_path = self.state_dir / "autosync_state.json"

        self.config: Dict[str, Any] = {}
        self.state: Dict[str, Any] = {}

        self._ensure_directories()
        self._ensure_default_config()
        self._load_config()
        self._load_state()

    # ─────────────────────────────────────
    # 초기 설정
    # ─────────────────────────────────────
    def _ensure_directories(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_default_config(self) -> None:
        if self.config_path.exists():
            return

        default_conf = {
            "version": "4.1",
            "description": "AutoSync LTS v4.1 기본 설정",
            "caps_core_plan": r"C:\A1-M2\CAPSCore\plan\caps_core_plan.json",
            "safeguard_script": r"C:\A1-M2\SafeGuard\SGD_safe_guard_lts_v1_0.py",
            "modules": {
                "VersionDocs": {
                    "script": r"C:\A1-M2\VersionDocs\VD_version_docs_v1_0.py",
                    "args": []
                },
                "Scheduler": {
                    "script": r"C:\A1-M2\Scheduler\SCH_scheduler_lts_v1_0.py",
                    "args": ["--run"]
                },
                "OmegaEngine": {
                    "script": r"C:\A1-M2\OmegaEngine\OMG_omega_engine_v1_0.py",
                    "args": ["--run-once"]
                },
                "DeployBridge": {
                    "script": r"C:\A1-M2\DeployBridge\DB_deploy_bridge_v1_0.py",
                    "args": ["--site", "01-sangsangpiano"]
                },
                "WebRack": {
                    "script": r"C:\A1-M2\WebRack\WR_webrack_v1_0.py",
                    "args": ["--all"]
                },
                "ImageInference": {
                    "script": r"C:\A1-M2\ImageInference\II_image_inference_v1_0.py",
                    "args": ["--auto"]
                },
                "LogCenter": {
                    "script": r"C:\A1-M2\LogCenter\LC_logcenter_v1_0.py",
                    "args": ["--merge"]
                },
                "MonitoringPanel": {
                    "script": r"C:\A1-M2\MonitoringPanel\MP_monitoring_panel_v1_0.py",
                    "args": ["--export"]
                },
                "SafeGuard": {
                    "script": r"C:\A1-M2\SafeGuard\SGD_safe_guard_lts_v1_0.py",
                    "args": ["--export"]
                }
            }
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(default_conf, f, indent=2, ensure_ascii=False)

    def _load_config(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def _load_state(self) -> None:
        if not self.state_path.exists():
            self.state = {
                "last_run": None,
                "last_state": None,
                "last_results": []
            }
        else:
            with open(self.state_path, "r", encoding="utf-8") as f:
                self.state = json.load(f)

    # ─────────────────────────────────────
    # 로깅
    # ─────────────────────────────────────
    def _log(self, msg: str) -> None:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        log_path = self.logs_dir / f"autosync_log_{date_str}.txt"
        line = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
        print(line, end="")

    # ─────────────────────────────────────
    # Core plan 읽기
    # ─────────────────────────────────────
    def _load_plan(self) -> List[PlanItem]:
        plan_path = Path(self.config["caps_core_plan"])
        if not plan_path.exists():
            self._log(f"[ERROR] caps_core_plan.json 없음: {plan_path}")
            return []

        with open(plan_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        items = []
        for it in raw.get("items", []):
            items.append(
                PlanItem(
                    module=it.get("module", ""),
                    action=it.get("action", ""),
                    priority=int(it.get("priority", 999)),
                    reason=it.get("reason", ""),
                    target_version=it.get("target_version")
                )
            )

        # 우선순위 순 정렬
        items.sort(key=lambda x: x.priority)
        return items

    # ─────────────────────────────────────
    # 모듈 패치 실행
    # ─────────────────────────────────────
    def _run_patch_for_module(self, item: PlanItem) -> PatchResult:
        # AutoSync 자기 자신은 스킵
        if item.module == "AutoSync":
            return PatchResult(
                module=item.module,
                action=item.action,
                success=True,
                returncode=0,
                message="AutoSync 자기 자신은 스킵"
            )

        modules_conf = self.config.get("modules", {})
        mod_conf = modules_conf.get(item.module)

        if not mod_conf:
            msg = f"모듈 설정 없음 (config.modules): {item.module}"
            self._log(f"[WARN] {msg}")
            return PatchResult(
                module=item.module,
                action=item.action,
                success=False,
                returncode=-1,
                message=msg
            )

        script = mod_conf.get("script")
        args = mod_conf.get("args", [])

        if not script or not Path(script).exists():
            msg = f"스크립트 경로 없음: {script}"
            self._log(f"[ERROR] {msg}")
            return PatchResult(
                module=item.module,
                action=item.action,
                success=False,
                returncode=-1,
                message=msg
            )

        cmd = ["python", script] + args

        self._log(f"[INFO] 모듈 실행 시작: {item.module} | action={item.action} | cmd={' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=False
            )
            success = (proc.returncode == 0)
            if success:
                self._log(f"[OK] 모듈 실행 성공: {item.module}")
            else:
                self._log(f"[FAIL] 모듈 실행 실패: {item.module} | returncode={proc.returncode}")
                if proc.stderr:
                    self._log(f"[STDERR] {proc.stderr.strip()}")

            msg = (proc.stdout or "").strip()
            if len(msg) > 200:
                msg = msg[:200] + "... (생략)"

            return PatchResult(
                module=item.module,
                action=item.action,
                success=success,
                returncode=proc.returncode,
                message=msg
            )
        except Exception as e:
            msg = f"예외 발생: {e}"
            self._log(f"[ERROR] {msg}")
            return PatchResult(
                module=item.module,
                action=item.action,
                success=False,
                returncode=-1,
                message=msg
            )

    # ─────────────────────────────────────
    # 전체 실행 (LTS 플로우)
    # ─────────────────────────────────────
    def run_from_plan(self, dry_run: bool = False) -> Dict[str, Any]:
        self._log(f"[INFO] AutoSync LTS v{AUTOSYNC_VERSION} 실행 시작 (dry_run={dry_run})")

        plan_items = self._load_plan()
        if not plan_items:
            self._log("[WARN] Plan 항목이 없습니다. 종료.")
            return {"state": "NO_PLAN", "results": []}

        patch_results: List[PatchResult] = []

        for item in plan_items:
            # CHECK_ONLY는 일단 로그만 남기고 스킵
            if item.action == "CHECK_ONLY":
                self._log(f"[INFO] CHECK_ONLY → 모듈 실행 스킵: {item.module}")
                continue

            if item.action == "PATCH":
                if dry_run:
                    self._log(f"[DRY-RUN] PATCH 대상: {item.module} (실행 안 함)")
                    continue
                res = self._run_patch_for_module(item)
                patch_results.append(res)
            else:
                self._log(f"[INFO] 알 수 없는 action={item.action} → 스킵")

        # SafeGuard 최종 검증
        overall_state = "UNKNOWN"
        if not dry_run:
            sg_script = self.config.get("safeguard_script")
            if sg_script and Path(sg_script).exists():
                cmd = ["python", sg_script, "--check"]
                self._log(f"[INFO] SafeGuard LTS 최종 검사 실행: {' '.join(cmd)}")
                try:
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        shell=False
                    )
                    if proc.returncode == 0:
                        overall_state = "GREEN"
                        self._log("[RESULT] SafeGuard 최종 상태: GREEN")
                    else:
                        overall_state = "RED"
                        self._log("[RESULT] SafeGuard 최종 상태: RED")
                        if proc.stderr:
                            self._log(f"[SafeGuard STDERR] {proc.stderr.strip()}")
                except Exception as e:
                    overall_state = "ERROR"
                    self._log(f"[ERROR] SafeGuard 실행 예외: {e}")
            else:
                overall_state = "NO_SAFEGUARD"
                self._log("[WARN] SafeGuard 스크립트 설정/경로가 올바르지 않습니다.")

        # state 저장
        result_dict = {
            "state": overall_state,
            "run_at": datetime.now().isoformat(timespec="seconds"),
            "patch_results": [pr.__dict__ for pr in patch_results],
            "dry_run": dry_run
        }
        self._save_state(result_dict)

        self._log(f"[INFO] AutoSync LTS v{AUTOSYNC_VERSION} 실행 종료")
        return result_dict

    # ─────────────────────────────────────
    # state 저장
    # ─────────────────────────────────────
    def _save_state(self, result: Dict[str, Any]) -> None:
        self.state["last_run"] = result["run_at"]
        self.state["last_state"] = result["state"]
        self.state["last_results"] = result["patch_results"]

        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    # ─────────────────────────────────────
    # 요약 출력
    # ─────────────────────────────────────
    def print_summary(self) -> None:
        print(f"[{MODULE_NAME} v{AUTOSYNC_VERSION}] 설정 요약")
        print(f"- caps_core_plan : {self.config['caps_core_plan']}")
        print(f"- safeguard_script: {self.config['safeguard_script']}")
        print(f"- modules:")
        for name, conf in self.config.get("modules", {}).items():
            print(f"  - {name:15s} → {conf.get('script')}")
        print(f"- state_path     : {self.state_path}")
        print()


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{MODULE_NAME} v{AUTOSYNC_VERSION} - CAPS AutoSync LTS"
    )
    parser.add_argument("--summary", action="store_true", help="설정 요약 출력")
    parser.add_argument("--run", action="store_true", help="plan에 따라 실제 모듈 실행")
    parser.add_argument("--dry-run", action="store_true", help="plan만 읽고 실행은 하지 않음")
    return parser.parse_args()


def main() -> None:
    autosync = AutoSyncLTS()
    args = parse_args()

    if args.summary:
        autosync.print_summary()
        return

    if args.dry_run:
        autosync.run_from_plan(dry_run=True)
        return

    if args.run:
        # 1차: LTS plan에 따른 모듈 실행 + SafeGuard 검사
        result = autosync.run_from_plan(dry_run=False)

        # 2차: SafeGuard 결과가 GREEN일 때만 AutoSync Core(4.0) 실행
        state = result.get("state")
        if state == "GREEN":
            autosync._log("[INFO] SafeGuard GREEN → AutoSync Core(autosync_core.autosync_run) 실행")
            try:
                from autosync_core import autosync_run
                autosync_run()
            except Exception as e:
                autosync._log(f"[ERROR] AutoSync Core 실행 중 예외 발생: {e}")
        else:
            autosync._log(f"[INFO] SafeGuard 상태가 GREEN이 아니므로 AutoSync Core를 실행하지 않습니다. (state={state})")
        return

    # 기본은 summary
    autosync.print_summary()


if __name__ == "__main__":
    main()
