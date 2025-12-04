# structure_scanner.py
# AutoSync 4.0 - 구조 스캔 최소 모듈

import os

def scan_structure(base_dir="."):
    """
    AutoSync가 변경 여부를 판단하기 위해
    폴더 구조/파일 목록을 스캔하는 기본 기능
    """
    structure = {}

    for root, dirs, files in os.walk(base_dir):
        # AutoSync 내부 파일들은 제외
        if "__pycache__" in root:
            continue
        if "logs" in root:
            continue
        if "state" in root:
            continue

        rel_root = os.path.relpath(root, base_dir)
        structure[rel_root] = sorted(files)

    return structure
