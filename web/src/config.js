// 좌표계·배치 — 계획서 5.6절. 숫자의 근거는 전부 에셋 실측이다.
export const TILE = { W: 256, H: 128 };      // floor_N 불투명 영역 256×129 실측
export const SPRITE = { W: 256, H: 512 };    // library·floor 88+28 파일 전부 동일
export const GRID = { cols: 10, rows: 8 };

// 층 — 같은 (col+row) 안에서의 그리기 순서
export const LAYER = { FLOOR: 0, PROP: 1, ACTOR: 2 };

// 배치표 (계획서 5.6). 스프라이트 이름은 파일 존재 확인을 마쳤다.
export const PROPS = [
  { id: "whiteboard", name: "화이트보드",  col: 1, row: 0, sprite: "displayCase_S" },
  { id: "coordDesk",  name: "소장 책상",   col: 1, row: 2, sprite: "longTableChairs_S" },
  { id: "reviewTable",name: "검토 테이블", col: 1, row: 4, sprite: "longTableDecoratedChairsBooks_S" },
  { id: "press",      name: "조판대",      col: 1, row: 6, sprite: "bookStand_S" },
  { id: "dashboard",  name: "계기판",      col: 4, row: 7, sprite: "displayCaseBooks_S" },
];

// 서고 6개 — 이름은 이벤트의 `서고` 값과 그대로 일치한다 (12편 실측 확인)
export const ZONES = [
  { name: "유형론",   col: 5, row: 0 },
  { name: "성격심리", col: 8, row: 0 },
  { name: "측정",     col: 5, row: 2 },
  { name: "편향",     col: 8, row: 2 },
  { name: "유사사례", col: 5, row: 4 },
  { name: "관계",     col: 8, row: 4 },
];

// 읽은 횟수 → 서가 스프라이트 (계획서 5.4)
export const SHELF = [
  { min: 0, sprite: "bookcaseEmpty_S" },
  { min: 1, sprite: "bookcaseHalfBooks_S" },
  { min: 3, sprite: "bookcaseBooks_S" },
];

// 조사관 책상 r1~r4
export const DESKS = [
  { col: 6, row: 7 }, { col: 7, row: 7 }, { col: 8, row: 7 }, { col: 9, row: 7 },
];

// 벽 — 회전과 무관하게 **화면 뒤쪽 두 변**에 세운다 (실측: _E 는 왼쪽 위 변, _S 는 오른쪽 위 변).
// 논리 좌표에 고정하면 돌렸을 때 벽이 앞을 가려 방 안이 안 보인다.
//
// 에셋은 Prototype 팩의 wall 계열을 연구소 색으로 바꾼 것이다(`tools/리컬러.py`).
// Library 팩의 벽은 wallBooks·wallDoorway 둘뿐이고 코너 조각이 없어서 모서리가 맞지 않는다.
// Prototype 팩에는 **wallCorner** 가 있어 한 장으로 두 변을 덮는다 — 겹침 문제가 사라진다.
export const WALL = {
  tones: ["gray", "beige", "cream"],   // web/assets/walls/<tone>/ · 첫째가 기본
  left:  "wall_E",                     // 화면 왼쪽 위로 뻗는 벽
  right: "wall_S",                     // 화면 오른쪽 위로 뻗는 벽
  corner: "wallCorner_S",              // 모서리 전용 — 두 변을 한 장에
  doorLeft: "doorway_E",  doorRight: "doorway_S",
  winLeft:  "window_E",   winRight:  "window_S",
  doorAt: 3,                           // 각 벽의 이 번째 칸을 문으로 (0부터)
  winAt: 6,                            // 이 번째 칸을 창문으로
};

// 카펫 — 소장 구역 바닥에 깔아 방 느낌을 낸다. 논리 좌표라 회전을 따라간다.
export const CARPETS = [
  { col: 1, row: 2, sprite: "floorCarpet_S" },
  { col: 1, row: 3, sprite: "floorCarpet_S" },
  { col: 1, row: 4, sprite: "floorCarpet_S" },
];

export const ASSETS = "assets";
