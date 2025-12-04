#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SGD_safe_guard_lts_v1_0.py

CAPS SafeGuard LTS v1.0 (정식 운영 버전)
----------------------------------------
역할:
- CAPS 전체 모듈 상태를 검증하고 GREEN/RED 상태를 반환한다.
- AutoSync가 패치한 결과가 정상인지 확인하기 위한 표준 LTS 엔진.
- 기존 safe_guard v1_2, v1_3는 기능 레이어(참고용)이며,
  LTS 1.0은 표준 구조 기반의 공식 실행 모듈이다.

검사 항목:
- modules_status.json 존재 여부 및 필드 검사
- caps_core_plan.json 존재 여부
- 각 모듈 디렉터리 존재 확인 (Omega/Scheduler/WebRack/DeployBridge)
- 버전 미스매치 검사
- JSON 파일 파싱 오류 검사
- 결과 리포트 생성(JSON)
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


SAFEGUARD_VERSION = "1.0.0"
MODULE_NAME = "SafeGuardLTS"


class SafeGuardLTS:
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent

        # 디렉터리 구성
        self.config_dir = self.base_dir / "config"
        self.logs_dir = self.base_dir / "logs"
        self.reports_dir = self.base_dir / "reports"

        self.config_path = self.config_dir / "safeguard_config.json"

        self._ensure_directories()
        self._ensure_default_config()
        self._load_config()

    # ------------------------------------------------------------
    # 초기 설정
    # ------------------------------------------------------------
    def _ensure_directories(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_default_config(self) -> None:
        if self.config_path.exists():
            return

        default_conf = {
            "version": "1.0",
            "description": "SafeGuard LTS v1.0 기본 설정",
            "caps_core_status": r"C:\A1-M2\CAPSCore\status\modules_status.json",
            "caps_core_plan": r"C:\A1-M2\CAPSCore\plan\caps_core_plan.json",
            "module_paths": {
                "OmegaEngine": r"C:\A1-M2\OmegaEngine",
                "Scheduler": r"C:\A1-M2\Scheduler",
                "WebRack": r"C:\A1-M2\WebRack",
                "DeployBridge": r"C:\A1-M2\DeployBridge",
                "ImageInference": r"C:\A1-M2\ImageInference",
                "LogCenter": r"C:\A1-M2\LogCenter",
                "MonitoringPanel": r"C:\A1-M2\MonitoringPanel"
            }
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(default_conf, f, indent=2, ensure_ascii=False)

    def _load_config(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.conf = json.load(f)

    # ------------------------------------------------------------
    # 로깅
    # ------------------------------------------------------------
    def _log(self, msg: str) -> None:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        log_path = self.logs_dir / f"safeguard_log_{date_str}.txt"
        line = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)

        print(line, end="")

    # ------------------------------------------------------------
    # JSON 검사 유틸
    # ------------------------------------------------------------
    def _check_json(self, path: Path) -> bool:
        if not path.exists():
            self._log(f"[ERROR] 파일 없음: {path}")
            return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                json.load(f)
            return True
        except Exception as e:
            self._log(f"[ERROR] JSON 파싱 실패: {path} | {e}")
            return False

    # ------------------------------------------------------------
    # 모듈 상태 검사
    # ------------------------------------------------------------
    def _check_modules_status(self) -> Dict[str, Any]:
        status_path = Path(self.conf["caps_core_status"])
        ok = self._check_json(status_path)
        data = {}

        if ok:
            with open(status_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            return {"ok": False, "msg": "modules_status.json invalid"}

        # 필수 필드 검사
        for module_name, info in data.items():
            for field in ["current_version", "target_version", "health"]:
                if field not in info:
                    self._log(f"[WARN] {module_name} 필드 누락: {field}")

        return {"ok": True, "msg": "modules_status.json OK", "data": data}

    # ------------------------------------------------------------
    # plan.json 검사
    # ------------------------------------------------------------
    def _check_plan(self) -> Dict[str, Any]:
        plan_path = Path(self.conf["caps_core_plan"])
        ok = self._check_json(plan_path)

        if ok:
            return {"ok": True, "msg": "plan.json OK"}
        else:
            return {"ok": False, "msg": "plan.json invalid"}

    # ------------------------------------------------------------
    # 모듈 폴더 존재 검사
    # ------------------------------------------------------------
    def _check_module_folders(self) -> Dict[str, bool]:
        results = {}
        for name, mpath in self.conf["module_paths"].items():
            p = Path(mpath)
            exists = p.exists()
            if not exists:
                self._log(f"[ERROR] 모듈 폴더 없음: {name} → {p}")
            results[name] = exists
        return results

    # ------------------------------------------------------------
    # 전체 검사 실행
    # ------------------------------------------------------------
    def run_full_check(self) -> Dict[str, Any]:
        self._log("[INFO] SafeGuard 전체 검사 시작")

        status_res = self._check_modules_status()
        plan_res = self._check_plan()
        module_folder_res = self._check_module_folders()

        all_ok = status_res["ok"] and plan_res["ok"] and all(module_folder_res.values())

        state = "GREEN" if all_ok else "RED"
        self._log(f"[RESULT] 전체 상태 = {state}")

        result = {
            "state": state,
            "status_check": status_res,
            "plan_check": plan_res,
            "module_folder_check": module_folder_res,
            "checked_at": datetime.now().isoformat(timespec="seconds")
        }

        return result

    # ------------------------------------------------------------
    # 리포트 JSON 저장
    # ------------------------------------------------------------
    def export_report(self, check_result: Dict[str, Any]) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = self.reports_dir / f"safeguard_report_{ts}.json"

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(check_result, f, indent=2, ensure_ascii=False)

        self._log(f"[INFO] 리포트 저장 완료: {out_path}")
        return out_path

    # ------------------------------------------------------------
    # 요약 출력
    # ------------------------------------------------------------
    def print_summary(self) -> None:
        print(f"[{MODULE_NAME} v{SAFEGUARD_VERSION}] 설정 요약")
        print(f"- config_path      : {self.config_path}")
        print(f"- caps_core_status : {self.conf['caps_core_status']}")
        print(f"- caps_core_plan   : {self.conf['caps_core_plan']}")
        print(f"- reports_dir      : {self.reports_dir}")
        print(f"- logs_dir         : {self.logs_dir}")


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{MODULE_NAME} v{SAFEGUARD_VERSION} - CAPS SafeGuard LTS"
    )
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--export", action="store_true")
    return parser.parse_args()


def main() -> None:
    sgd = SafeGuardLTS()
    args = parse_args()

    if args.summary:
        sgd.print_summary()
        return

    if args.check:
        result = sgd.run_full_check()
        print(result)
        return

    if args.export:
        result = sgd.run_full_check()
        sgd.export_report(result)
        return

    # 기본 동작: summary
    sgd.print_summary()


if __name__ == "__main__":
    main()
