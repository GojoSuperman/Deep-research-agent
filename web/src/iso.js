// 아이소메트릭 투영 — 계획서 5.6. 화면은 한 방향만 보여 준다(회전 없음).
import { TILE, STEP, SPRITE, GRID } from "./config.js";

/** 타일 (col,row) → 다이아몬드 중심 */
export function foot(col, row, origin) {
  return {
    x: origin.x + (col - row) * STEP.X,
    y: origin.y + (col + row) * STEP.Y,
  };
}

/**
 * 256×512 스프라이트의 좌상단. 모든 소품이 같은 캔버스에 렌더돼 있어
 * 셀에 얹기만 하면 맞는다 — 오브젝트별 앵커가 필요 없다.
 */
export function spriteTopLeft(col, row, origin) {
  const f = foot(col, row, origin);
  return { x: f.x - SPRITE.W / 2, y: f.y + TILE.H / 2 - SPRITE.H };
}

/** 그리기 순서: col+row 오름차순, 같으면 층 순 */
export function depth(col, row, layer) {
  return (col + row) * 10 + layer;
}

/** 장면 전체 크기와 (0,0) 원점. 벽이 격자 바깥 한 줄에 서므로 그만큼 여유를 둔다. */
export function sceneBox(pad = 32) {
  const { cols, rows } = GRID;
  const top = SPRITE.H - TILE.H / 2;
  return {
    width: (cols + rows) * STEP.X + SPRITE.W + pad * 2,
    height: (cols + rows) * STEP.Y + top + TILE.H + pad * 2,
    origin: { x: pad + rows * STEP.X + SPRITE.W / 2, y: pad + top },
  };
}
