// 좌표계·배치 — 숫자의 근거는 전부 에셋 실측이다 (계획서 5.6).
//
// 소품은 Kenney **Furniture Kit** 의 3D 원본을 Miniature 규격(2:1 · 256×512)으로 다시
// 렌더한 것이다 (tools/render_iso.py + tools/보정.py). 캐릭터는 Shape Characters 를 쓴다.
// 화면은 한 방향만 보여 준다 — 회전을 없앴으므로 스프라이트도 _SE 한 벌만 쓴다.

export const TILE = { W: 256, H: 128 };
export const STEP = { X: 128, Y: 64 };
// 스프라이트 캔버스 — 타일(256×128)보다 크게 잡아 가장자리가 잘리지 않게 한다.
// 256 폭으로 렌더하면 책장 같은 오브젝트가 프레임 밖으로 나가 다리가 잘린다 (실측).
export const SPRITE = { W: 384, H: 768 };
export const GRID = { cols: 12, rows: 7 };   // 서고 구역을 없앤 만큼 방을 줄여 소품을 키운다

// 책상 위에 올리는 소품의 높이 (px). 책상 상판 0.384유닛 × 157px/유닛 ≈ 60
export const DESK_TOP = -60;
// 코너 책상은 상판이 스프라이트 오른쪽(가로중심 162)에 있고 노트북은 왼쪽(32)에 렌더돼 있다.
// 그 차이만큼 가로로 밀어야 상판 위에 놓인다.
export const CORNER_DX = 130;

// 층 — 같은 (col+row) 안에서의 그리기 순서
export const LAYER = { FLOOR: 0, RUG: 0.4, WALL: 0.5, PROP: 1, ON_DESK: 1.2, ACTOR: 2 };

// 벽 — 격자 바깥 한 줄에 세운다. 두 변 모두 같은 _SE 를 쓰고 0열 쪽만 좌우로 뒤집는다.
export const WALL = {
  wall: "wall_SE",  door: "wallDoorway_SE",  win: "wallWindow_SE",
  doorAt: 2,
  winAt: 6,
};

// 서고 6개 — 오른쪽 벽(0행)을 따라 일렬로 붙인다.
// 1.5배로 키운다. **비율은 지킨다** — 가로만 늘리면 기둥이 두꺼워져 서로 겹치고
// 앞다리가 선반에 묻혀 잘린 것처럼 보인다 (탁자에서도 같은 일이 있었다).
export const SHELF_SCALE = { x: 1.5, y: 1 };
export const ZONES = [
  { name: "유형론",   col: 6,  row: 0 },
  { name: "성격심리", col: 7,  row: 0 },
  { name: "측정",     col: 8,  row: 0 },
  { name: "편향",     col: 9,  row: 0 },
  { name: "유사사례", col: 10, row: 0 },
  { name: "관계",     col: 11, row: 0 },
];

// 서고는 **계기가 달린 기계**다. 읽은 횟수는 가구 모양이 아니라 게이지로 보여 준다.
// 가구 모양을 바꾸는 방식(빈 선반 → 찬 선반, 책 얹기)은 변화가 작고 몇 권까지밖에 못 센다.
export const SHELF_SPRITE = "washerDryerStacked";
export const GAUGE_MAX = 6;        // 이 횟수면 게이지가 꽉 찬다
// 게이지를 기계 꼭대기 바로 위에 붙인다.
// 기계 스프라이트의 불투명 상단이 y=541, 앵커는 704 → 배율 1.5 에서 foot 기준 -244px.
export const GAUGE_DY = -244 - 30;
// 기계는 스프라이트 중앙이 아니라 왼쪽에 렌더돼 있다 (가로중심 111.5 vs 192).
// 게이지도 그만큼 왼쪽으로 옮겨야 기계 위에 온다.
export const GAUGE_DX = -121;
// 서고별 색 — 게이지와 이름표에 함께 쓴다
export const ZONE_COLOR = {
  "유형론": "#7c6cf0", "성격심리": "#3fae6e", "측정": "#e0a13c",
  "편향": "#d9566c", "유사사례": "#3fa7d6", "관계": "#c06ad9",
};

// 가구 — 실제 사무실처럼. 소장실 · 회의 구역 · 조사관 책상 섬.
// dy 를 준 소품은 책상 위에 올라간다.
export const PROPS = [
  // 소장실 (왼쪽 위)
  { id: "coordDesk", col: 1, row: 0, sprite: "deskCorner" },
  { id: "coordLap",  col: 1, row: 0, sprite: "laptop", layer: 1.2, dy: DESK_TOP, dx: CORNER_DX },

  // 회의 구역 (왼쪽 아래)
  // 긴 회의 탁자 — 세로 방향(_SW)으로 돌리고 두 배로 키운다
  // 낮은 탁자를 두 배로. 세로만 누르면 비율이 깨져 바닥에서 뜬 것처럼 보인다.
  { id: "round", col: 2, row: 4, sprite: "tableCoffee", face: "_SW", scale: 2 },
  { id: "coffee", col: 0, row: 6, sprite: "kitchenCoffeeMachine" },

  // 조사관 책상 섬 (가운데) — 책상 위에 모니터와 키보드
  { id: "d1", col: 4, row: 2, sprite: "desk" },
  { id: "s1", col: 4, row: 2, sprite: "computerScreen", layer: 1.2, dy: DESK_TOP },
  { id: "d2", col: 6, row: 2, sprite: "desk" },
  { id: "s2", col: 6, row: 2, sprite: "computerScreen", layer: 1.2, dy: DESK_TOP },
  { id: "d3", col: 4, row: 4, sprite: "desk" },
  { id: "s3", col: 4, row: 4, sprite: "computerScreen", layer: 1.2, dy: DESK_TOP },
  { id: "d4", col: 6, row: 4, sprite: "desk" },
  { id: "s4", col: 6, row: 4, sprite: "computerScreen", layer: 1.2, dy: DESK_TOP },

];

// 조사관 의자 — 각자 책상 앞. 캐릭터도 여기에 선다.
export const DESKS = [
  { col: 4, row: 3 }, { col: 6, row: 3 }, { col: 4, row: 5 }, { col: 6, row: 5 },
];
export const DESK_SPRITE = null;   // 책상 의자는 두지 않는다

export const CARPETS = [];

export const ASSETS = "assets";
export const FURN = "furniture";
export const FACE = "_SE";        // 회전이 없으므로 한 방향만 쓴다
