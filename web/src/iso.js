// 아이소메트릭 투영 — 계획서 5.6절의 식. 회전(4방향)은 격자 좌표를 돌려서 처리한다.
import { TILE, SPRITE, GRID } from "./config.js";

// 스프라이트 접미사 — 격자를 시계방향으로 돌리면 보는 면이 바뀐다
const FACES = ["S", "W", "N", "E"];

/** 회전 rot(0~3) 적용 후의 격자 크기 */
export function gridSize(rot) {
  return rot % 2 === 0
    ? { cols: GRID.cols, rows: GRID.rows }
    : { cols: GRID.rows, rows: GRID.cols };
}

/** 논리 좌표 (col,row) → 회전된 격자 좌표 */
export function rotate(col, row, rot) {
  const { cols, rows } = GRID;
  switch (rot & 3) {
    case 1: return { col: rows - 1 - row, row: col };
    case 2: return { col: cols - 1 - col, row: rows - 1 - row };
    case 3: return { col: row, row: cols - 1 - col };
    default: return { col, row };
  }
}

/** `bookcase_S` 같은 이름의 방향 접미사를 회전에 맞춰 바꾼다 */
export function faceSprite(sprite, rot) {
  const m = sprite.match(/^(.*)_([NESW])$/);
  if (!m) return sprite;
  const i = FACES.indexOf(m[2]);
  if (i < 0) return sprite;
  return `${m[1]}_${FACES[(i + rot) & 3]}`;
}

/** 회전된 타일 좌표 → 다이아몬드 바닥 중심의 화면 좌표 */
export function toScreen(col, row, origin) {
  return {
    x: origin.x + (col - row) * (TILE.W / 2),
    y: origin.y + (col + row) * (TILE.H / 2),
  };
}

/** 256×512 스프라이트를 그릴 좌상단 — 바닥 꼭짓점을 타일에 맞춘다 */
export function spriteTopLeft(col, row, origin) {
  const s = toScreen(col, row, origin);
  return { x: s.x - TILE.W / 2, y: s.y + TILE.H / 2 - SPRITE.H };
}

/** 그리기 순서: col+row 오름차순, 같으면 층 순 */
export function depth(col, row, layer) {
  return (col + row) * 10 + layer;
}

/** 회전 상태에서 장면 전체가 차지하는 크기와, (0,0)이 놓일 원점 */
export function sceneBox(rot, pad = 24) {
  const { cols, rows } = gridSize(rot);
  // (0,0) 스프라이트의 좌상단은 바닥 꼭짓점보다 SPRITE.H - TILE.H/2 만큼 위다.
  // TILE.H 로 잡으면 위가 40px 잘린다 (구현 중 검산으로 잡음).
  const top = SPRITE.H - TILE.H / 2;
  return {
    width: (cols + rows) * (TILE.W / 2) + pad * 2,
    height: (cols + rows) * (TILE.H / 2) + top + pad * 2,
    origin: { x: pad + rows * (TILE.W / 2), y: pad + top },
  };
}
