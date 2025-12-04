#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AS_autosync_hybrid_loop_v1_0.py

CAPS AutoSync Hybrid Loop v1.0
------------------------------
역할:
- AutoSync LTS(AS_autosync_lts_v4_0)의 run_from_plan()을 반복 실행하면서
  모듈 패치 + SafeGuard 검증을 자동 수행한다.
- 각 루프에서 SafeGuard 상태가 GREEN일 때만 AutoSync Core(autosync_core.autosync_run)를 실행하여
  WebRack + DeployBridge(Netlify)까지 연결한다.
- "필요할 때만" 반복되도록 설계된 조건 기반 하이브리드 루프:
    - 최소 1회는 무조건 실행
    - 각 루프에서 패치된 모듈 수가 0이면, 더 이상 할 일이 없다고 보고 종료
    - SafeGuard 상태가 GREEN이 아닐 경우 즉시 종료
    - 무한 루프 방지를 위해 max_loops 제한

사용 예시 (CMD):

    cd C:\A1-M2\AutoSync
    python AS_autosync_hybrid_loop_v1_0.py --run

옵션 예시:

    # 최대 10회까지 루프 돌리기
    python AS_autosync_hybrid_loop_v1_0.py --run --max-loops 10

    # Dry-run: 실제 모듈 실행 없이 plan만 따라가면서 루프 구조 확인
    python AS_autosync_hybrid_loop_v1_0.py --run --dry-run

"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# AutoSync LTS / Core 가져오기
from AS_autosync_lts_v4_0 import AutoSyncLTS, AUTOSYNC_VERSION as LTS_VERSION  # :contentReference[oaicite:1]{index=1}
from autosync_core import autosync_run  # :contentReference[oaicite:2]{index=2}


HYBRID_VERSION = "1.0.0"
MODULE_NAME = "AutoSyncHybridLoop"


@dataclass
class LoopStats:
    loop_index: int
    patched_count: int
    state: str
    run_at: str


class HybridRunner:
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent
        self.logs_dir = self.base_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────
    # 로깅
    # ─────────────────────────────
    def _log(self, msg: str) -> None:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        log_path = self.logs_dir / f"autosync_hybrid_{date_str}.txt"
        line = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
        print(line, end="")

    # ─────────────────────────────
    # LTS 1회 실행 래핑
    # ─────────────────────────────
    def _run_lts_once(self, dry_run: bool = False) -> Dict[str, Any]:
        autosync = AutoSyncLTS(self.base_dir)
        self._log(f"[INFO] LTS 실행 (dry_run={dry_run}) 시작")
        result = autosync.run_from_plan(dry_run=dry_run)
        self._log(f"[INFO] LTS 실행 종료: state={result.get('state')}, patched={len(result.get('patch_results', []))}")
        return result

    # ─────────────────────────────
    # 하이브리드 루프
    # ─────────────────────────────
    def run_hybrid(
        self,
        max_loops: int = 5,
        min_loops: int = 1,
        sleep_seconds: float = 0.0,
        dry_run: bool = False,
        disable_core: bool = False,
    ) -> Dict[str, Any]:
        """
        하이브리드 루프 실행:

        - 최소 min_loops 만큼은 무조건 실행
        - 각 루프마다:
            1) LTS 실행 (모듈 패치 + SafeGuard)
            2) state != GREEN 이면 즉시 종료
            3) state == GREEN 이고 dry_run=False 이면 AutoSync Core 실행
            4) 패치된 모듈 수가 0이고, 이미 min_loops 이상 돌았다면 종료
            5) max_loops에 도달하면 안전상 종료
        """
        self._log(f"[INFO] {MODULE_NAME} v{HYBRID_VERSION} 시작 (LTS v{LTS_VERSION}, dry_run={dry_run})")
        loop_stats: List[LoopStats] = []

        loops_ran = 0
        total_patched = 0
        last_state = "UNKNOWN"

        while True:
            loops_ran += 1
            self._log(f"[LOOP] ----- Hybrid Loop #{loops_ran} 시작 -----")

            # 1) LTS 1회 실행
            result = self._run_lts_once(dry_run=dry_run)
            state = result.get("state", "UNKNOWN")
            patch_results = result.get("patch_results", [])
            patched_count = sum(1 for pr in patch_results if pr.get("success"))

            total_patched += patched_count
            last_state = state

            loop_stats.append(
                LoopStats(
                    loop_index=loops_ran,
                    patched_count=patched_count,
                    state=state,
                    run_at=result.get("run_at", datetime.now().isoformat(timespec="seconds")),
                )
            )

            self._log(f"[LOOP] #{loops_ran} 결과: state={state}, patched_count={patched_count}")

            # 2) SafeGuard 상태 체크
            if state != "GREEN":
                self._log(f"[STOP] SafeGuard 상태가 GREEN이 아님 → 하이브리드 루프 중단 (state={state})")
                break

            # 3) AutoSync Core 실행 (옵션)
            if not dry_run and not disable_core:
                try:
                    self._log("[CORE] AutoSync Core(autosync_run) 실행 시작")
                    autosync_run()
                    self._log("[CORE] AutoSync Core 실행 완료")
                except Exception as e:
                    self._log(f"[ERROR] AutoSync Core 실행 중 예외 발생 → 루프 중단: {e}")
                    break

            # 4) 반복 종료 조건
            # 4-1) max_loops 도달 시 강제 종료
            if loops_ran >= max_loops:
                self._log(f"[STOP] max_loops({max_loops}) 도달 → 하이브리드 루프 종료")
                break

            # 4-2) 패치된 모듈이 없고, 최소 루프 횟수는 만족하면 종료
            if patched_count == 0 and loops_ran >= min_loops:
                self._log("[STOP] 더 이상 패치할 모듈이 없음 + 최소 루프 횟수 충족 → 루프 종료")
                break

            # 5) 다음 루프 전 대기 (선택)
            if sleep_seconds > 0:
                self._log(f"[SLEEP] 다음 루프까지 {sleep_seconds}초 대기")
                time.sleep(sleep_seconds)

        # 요약 결과
        summary = {
            "loops_ran": loops_ran,
            "total_patched": total_patched,
            "last_state": last_state,
            "loop_stats": [ls.__dict__ for ls in loop_stats],
        }

        self._log(
            f"[SUMMARY] Hybrid Loop 종료: loops={loops_ran}, total_patched={total_patched}, last_state={last_state}"
        )

        return summary


# ─────────────────────────────────────────
# CLI
# ─────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{MODULE_NAME} v{HYBRID_VERSION} - CAPS AutoSync Hybrid Loop",
    )
    parser.add_argument("--run", action="store_true", help="하이브리드 루프 실행")
    parser.add_argument("--max-loops", type=int, default=5, help="최대 루프 횟수 (기본값: 5)")
    parser.add_argument("--min-loops", type=int, default=1, help="최소 실행 루프 횟수 (기본값: 1)")
    parser.add_argument("--sleep", type=float, default=0.0, help="루프 사이 대기 시간(초)")
    parser.add_argument("--dry-run", action="store_true", help="LTS를 dry-run 모드로 실행 (실제 패치/배포 없음)")
    parser.add_argument("--disable-core", action="store_true", help="AutoSync Core(autosync_run) 실행 비활성화")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runner = HybridRunner()

    if not args.run:
        print(f"[{MODULE_NAME} v{HYBRID_VERSION}]")
        print(f"- LTS version   : {LTS_VERSION}")
        print(f"- base_dir      : {runner.base_dir}")
        print(f"- logs_dir      : {runner.logs_dir}")
        print("기본 사용 예시:")
        print("  python AS_autosync_hybrid_loop_v1_0.py --run")
        print("옵션 예시:")
        print("  python AS_autosync_hybrid_loop_v1_0.py --run --max-loops 10")
        print("  python AS_autosync_hybrid_loop_v1_0.py --run --dry-run")
        return

    runner.run_hybrid(
        max_loops=args.max_loops,
        min_loops=args.min_loops,
        sleep_seconds=args.sleep,
        dry_run=args.dry_run,
        disable_core=args.disable_core,
    )


if __name__ == "__main__":
    main()
