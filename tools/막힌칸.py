"""소품이 덮는 칸을 스프라이트 알파로 재서 config.js 의 BLOCKED 를 만든다.

  .venv/bin/python tools/막힌칸.py

renderer.js 의 그리기 변환을 그대로 따라간다. 소품을 옮기거나 배율을 바꿨으면 다시 돌려라.
추측으로 좌표를 적으면 캐릭터가 탁자 위에 올라선다 (실제로 그랬다).
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FURN = ROOT / "web/assets/furniture"
TILE_H, STEP_X, STEP_Y, SPR_W, SPR_H = 128, 128, 64, 384, 768

_cfg = (ROOT / "web/src/config.js").read_text(encoding="utf-8")
_g = re.search(r"GRID = \{ cols: (\d+), rows: (\d+)", _cfg)
COLS, ROWS = int(_g[1]), int(_g[2])       # 방 크기는 config 에서 읽는다


def foot(col: int, row: int) -> tuple[float, float]:
    return ((col - row) * STEP_X, (col + row) * STEP_Y)


def screen_rect(col, row, sprite, face="_SE", scale=1.0, scale_y=1.0, dx=0, dy=0):
    img = Image.open(FURN / f"{sprite}{face}.png")
    x0, y0, x1, y1 = img.getbbox()          # 불투명 영역만 본다
    fx, fy = foot(col, row)
    px, py = fx - SPR_W / 2 + dx, fy + TILE_H / 2 - SPR_H + dy
    k, ky = scale, scale * scale_y
    ax, ay = px + img.width / 2, py + img.height - TILE_H / 2
    ox, oy = ax - img.width / 2 * k, ay - (img.height - TILE_H / 2) * ky
    return (ox + x0 * k, oy + y0 * ky, ox + x1 * k, oy + y1 * ky)


def covered(rect) -> list[tuple[int, int]]:
    x0, y0, x1, y1 = rect
    return [(c, r) for r in range(ROWS) for c in range(COLS)
            if x0 <= foot(c, r)[0] <= x1 and y0 <= foot(c, r)[1] <= y1]


def parse_config() -> list[tuple[str, int, int, str, str, float, float]]:
    """config.js 의 PROPS·ZONES 를 읽는다. 화면에 올라가는 소품(dy 있는 것)은 뺀다."""
    src = (ROOT / "web/src/config.js").read_text(encoding="utf-8")
    out = []
    block = src[src.index("export const PROPS"):src.index("// 조사관 의자")]
    for line in block.splitlines():
        m = re.search(r'id:\s*"(\w+)".*?col:\s*(\d+),\s*row:\s*(\d+),\s*sprite:\s*"(\w+)"', line)
        if not m or "dy:" in line or "walk: true" in line:
            continue        # 책상 위 소품과, 사람이 올라서는 의자는 막지 않는다
        face = (re.search(r'face:\s*"(\w+)"', line) or [None, "_SE"])[1]
        scale = float((re.search(r'scale:\s*([\d.]+)', line) or [None, 1])[1])
        out.append((m[1], int(m[2]), int(m[3]), m[4], face, scale, 1.0))
    zones = re.findall(r'\{ name: "(\S+?)",\s*col:\s*(\d+),\s*row:\s*(\d+) \}', src)
    shelf = re.search(r'SHELF_SPRITE = "(\w+)"', src)[1]
    sx = float(re.search(r'SHELF_SCALE = \{ x: ([\d.]+)', src)[1])
    for name, c, r in zones:
        out.append((name, int(c), int(r), shelf, "_SE", sx, 1.0))
    return out


def main() -> None:
    blocked: set[tuple[int, int]] = set()
    for name, c, r, sprite, face, k, ky in parse_config():
        cells = covered(screen_rect(c, r, sprite, face, k, ky))
        blocked |= set(cells)
        print(f"  {name:<10} 앵커({c},{r}) → {cells}")
    cells = sorted(blocked, key=lambda t: (t[1], t[0]))
    print("\nconfig.js 에 넣을 값:")
    print("export const BLOCKED = [" + ", ".join(f"[{c},{r}]" for c, r in cells) + "];")
    print()
    for r in range(ROWS):
        print(f"  row{r} " + " ".join("■" if (c, r) in blocked else "·" for c in range(COLS)))


if __name__ == "__main__":
    main()
