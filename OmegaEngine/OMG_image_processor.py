"""
image_processor.py v1.7
HARD-REENCODE MODE: 완전 신규 RGB 캔버스 위에 복사 후 baseline JPEG 저장
WordPress/GD/Imagick 100% 호환 안정형 이미지 생성
"""
from __future__ import annotations
from pathlib import Path
from typing import List
from PIL import Image, ImageOps

def resize_and_normalize(
    image_root: Path,
    filenames: List[str],
    target_width: int = 900,
    normalize_ratio: bool = False,
    output_dir: Path | None = None
) -> List[Path]:

    if output_dir is None:
        output_dir = image_root / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = []

    for name in filenames:
        src_path = (image_root / name).resolve()
        if not src_path.exists():
            print(f"[image_processor] file not found: {src_path}")
            continue

        try:
            with Image.open(src_path) as img:
                # EXIF orientation fix
                img = ImageOps.exif_transpose(img)

                # Convert ALL to RGB
                if img.mode != "RGB":
                    img = img.convert("RGB")

                w, h = img.size

                # Resize
                if w != target_width:
                    ratio = target_width / float(w)
                    new_size = (target_width, int(h * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                    w, h = img.size

                # Optional 4:3 crop
                if normalize_ratio:
                    target_ratio = 4 / 3
                    cur_ratio = w / h
                    if cur_ratio > target_ratio:
                        new_w = int(h * target_ratio)
                        offset = (w - new_w) // 2
                        img = img.crop((offset, 0, offset + new_w, h))
                    elif cur_ratio < target_ratio:
                        new_h = int(w / target_ratio)
                        offset = (h - new_h) // 2
                        img = img.crop((0, offset, w, offset + new_h))
                        h = new_h

                # HARD RE-ENCODE: create fresh blank RGB canvas
                clean = Image.new("RGB", img.size, (255, 255, 255))
                clean.paste(img)

                out = output_dir / f"{src_path.stem}_900.jpg"

                # Baseline JPEG only (NO progressive, NO optimize)
                clean.save(
                    out,
                    format="JPEG",
                    quality=85,
                    optimize=False,
                    progressive=False
                )

                outputs.append(out)

        except Exception as e:
            print(f"[image_processor] ERROR processing {src_path}: {e}")
            continue

    return outputs
