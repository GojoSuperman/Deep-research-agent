"""Blender STUDIO 렌더를 Kenney 원본 색에 맞춘다.

Workbench STUDIO 는 면별 음영을 남기지만 전체가 어두워진다
(실측: 바닥 #99816c, 원본 #ffcb81). 음영 비율은 지키면서 밝기와 채도만 끌어올린다.

    python tools/보정.py <입력 폴더> <출력 폴더>
"""
from __future__ import annotations

import colorsys
import sys
from pathlib import Path

from PIL import Image

GAIN = 1.62      # 밝기 — 원본과 대표색을 맞춰 정한 값
SAT = 1.45       # 채도 — STUDIO 가 색을 흐리게 만든 만큼 되돌린다

# 바닥은 가구와 같은 나무색이라 그대로 두면 가구가 묻힌다. 채도를 낮춰 뒤로 물린다.
FLOOR = {"floorFull", "floorHalf"}
FLOOR_SAT = 0.30
FLOOR_GAIN = 1.72


def fix(im: Image.Image, gain: float = GAIN, sat: float = SAT) -> Image.Image:
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            R, G, B = colorsys.hsv_to_rgb(h, min(1.0, s * sat), min(1.0, v * gain))
            px[x, y] = (int(R * 255), int(G * 255), int(B * 255), a)
    return im


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in sorted(src.glob("*.png")):
        base = p.stem.rsplit("_", 1)[0]
        floor = base in FLOOR
        gain = FLOOR_GAIN if floor else GAIN
        sat = FLOOR_SAT if floor else SAT
        fix(Image.open(p).convert("RGBA"), gain, sat).save(dst / p.name)
        n += 1
    print(f"보정 {n}장 → {dst}")


if __name__ == "__main__":
    main()
