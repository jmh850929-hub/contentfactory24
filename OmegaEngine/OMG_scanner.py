from __future__ import annotations
from pathlib import Path
from typing import List, Optional

def get_client_dir(root: Path, client_name: str) -> Path:
    """CAPS_Clients 아래에서 client_name 폴더를 찾는다."""
    cdir = root / client_name
    if not cdir.exists() or not cdir.is_dir():
        raise SystemExit(f"[scanner] ERROR: client folder not found: {cdir}")
    return cdir

def pick_latest_product_dir(client_dir: Path) -> Path:
    """거래처 폴더 내에서 '가장 최근에 수정된 하위 폴더'를 상품 폴더로 선택.
    - 하위 폴더가 없으면 client_dir 자체를 상품 폴더로 사용.
    """
    subdirs: List[Path] = [p for p in client_dir.iterdir() if p.is_dir()]
    if not subdirs:
        return client_dir

    # 수정 시간 기준 가장 최신 폴더 선택
    latest = max(subdirs, key=lambda p: p.stat().st_mtime)
    return latest