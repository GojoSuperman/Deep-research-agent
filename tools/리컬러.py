"""프로토타입 벽을 연구소 벽 색으로 바꾼다.

Kenney Isometric Miniature Prototype 팩은 배치 확인용이라 전부 주황(#ed8b1c)이다.
그 팩에만 있는 wall·wallCorner·window·doorway 가 필요해서 색만 바꿔 쓴다.
CC0 라 수정·재배포에 제약이 없다.

    python tools/리컬러.py <팩을 푼 Isometric 폴더>
"""
from __future__ import annotations

import colorsys
import sys
from pathlib import Path

from PIL import Image

OUT = Path("web/assets/walls")

# 이름 → (색조, 채도 배수, 명도 배수). 화면에서 고를 수 있게 세 벌을 만든다.
TONES = {
    "beige": (0.098, 0.30, 0.98),   # 따뜻한 베이지 — 서고의 나무색과 붙는다
    "gray":  (0.083, 0.10, 0.96),   # 차분한 회색 — 사무실 느낌이 가장 강하다
    "cream": (0.110, 0.18, 1.06),   # 밝은 미색
}

# 화면 뒤쪽 두 변만 쓰므로 _E(왼쪽 위)·_S(오른쪽 위)면 충분하다. 모서리는 한 장이 두 변을 덮는다.
PIECES = ["wall_E", "wall_S", "wallCorner_S", "window_E", "window_S", "doorway_E", "doorway_S"]


def recolor(im: Image.Image, hue: float, sat: float, val: float) -> Image.Image:
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            _, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            R, G, B = colorsys.hsv_to_rgb(hue, s * sat, min(1.0, v * val))
            px[x, y] = (int(R * 255), int(G * 255), int(B * 255), a)
    return im


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1])
    made = 0
    for tone, (hue, sat, val) in TONES.items():
        d = OUT / tone
        d.mkdir(parents=True, exist_ok=True)
        for name in PIECES:
            p = src / f"{name}.png"
            if not p.exists():
                print(f"  ⚠ 없음: {p}")
                continue
            recolor(Image.open(p).convert("RGBA"), hue, sat, val).save(d / f"{name}.png")
            made += 1
    print(f"벽 {made}장 생성 → {OUT}")


if __name__ == "__main__":
    main()
