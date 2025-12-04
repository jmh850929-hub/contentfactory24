# autosync_core.py

import datetime
import json
from structure_scanner import scan_structure
from file_patcher import apply_patch
from diff_checker import check_diff
from json_writer import write_json_version
from excel_writer import write_excel_version
from pdf_writer import write_pdf_version
from webrack_core import update_site_root
from safeguard_core import validate_patch

# 🔥 추가: DeployBridge import
from deploybridge_core import trigger_deploy


def autosync_run():
    """
    AutoSync 4.0 - Hybrid Loop Core
    패치 → 검증 → 문서화 → WebRack 갱신 → Netlify 자동 배포
    """

    print("🔧 [AutoSync] 구조 스캔 중...")
    structure_info = scan_structure()

    print("🔧 [AutoSync] 변경 감지 중...")
    diff = check_diff(structure_info)

    if not diff:
        print("✅ [AutoSync] 변경사항 없음. 종료.")
        return

    print("🔧 [AutoSync] 패치 적용 중...")
    patch_result = apply_patch(diff)

    print("🛡️ [AutoSync] SafeGuard 검증 실행...")
    validation = validate_patch()

    if validation != "GREEN":
        print("❌ [AutoSync] SafeGuard FAIL → 자동배포 중단")
        return

    print("📄 [AutoSync] VersionDocs 생성(JSON/Excel/PDF)...")
    write_json_version()
    write_excel_version()
    write_pdf_version()

    print("🧱 [AutoSync] WebRack site_root 업데이트 중...")
    update_site_root()

    # 🔥🔥🔥 여기서 자동배포 트리거!
    print("🚀 [AutoSync] Netlify DeployBridge 트리거 실행...")
    deploy_result = trigger_deploy("autosync_runtime")
    print("🌐 [AutoSync] DeployBridge Result:", deploy_result)

    print("🎉 [AutoSync] 전체 루프 완료.")
