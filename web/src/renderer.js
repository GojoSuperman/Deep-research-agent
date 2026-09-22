// 렌더러 — 지금은 바닥·가구까지. 캐릭터는 좌표를 눈으로 확인한 뒤에 붙인다.
//
// 회전은 4방향 스프라이트라 중간 각도가 없다. 그대로 끊어 바꾸면 툭 튄다.
// 그래서 두 방향을 각각 그려 크로스페이드로 섞는다 (계획서 5.6 보강).
import { GRID, PROPS, ZONES, SHELF, DESKS, WALL, CARPETS, ASSETS } from "./config.js";
import { toScreen, spriteTopLeft, depth, sceneBox, rotate, faceSprite, gridSize } from "./iso.js";

const cache = new Map();

function load(name, dir) {
  const key = `${dir}/${name}`;
  if (cache.has(key)) return cache.get(key);
  const img = new Image();
  const p = new Promise(ok => {
    img.onload = () => ok(img);
    img.onerror = () => ok(null);      // 없는 스프라이트는 null 로 남겨 화면에 보고한다
  }).then(v => (cache.set(key, v), v));
  cache.set(key, p);
  img.src = `${ASSETS}/${dir}/${name}.png`;   // 이 줄이 없으면 onload 가 영영 오지 않는다
  return p;
}

export function shelfSprite(readCount) {
  let s = SHELF[0].sprite;
  for (const r of SHELF) if (readCount >= r.min) s = r.sprite;
  return s;
}

/** 논리 배치 — 회전과 무관한 원본 좌표. reads = { 서고이름: 읽은횟수 } */
export function build(reads = {}) {
  const items = [];
  for (let row = 0; row < GRID.rows; row++)
    for (let col = 0; col < GRID.cols; col++)
      items.push({ col, row, dir: "floor", sprite: "floor_S", layer: 0 });
  for (const c of CARPETS) items.push({ ...c, dir: "library", layer: 0.4 });
  for (const p of PROPS) items.push({ ...p, dir: "library", layer: 1 });
  for (const z of ZONES)
    items.push({ ...z, dir: "library", sprite: shelfSprite(reads[z.name] || 0), layer: 1, zone: true });
  DESKS.forEach((d, i) =>
    items.push({ ...d, dir: "library", sprite: "libraryChair_S", layer: 1, name: `r${i + 1}` }));
  return items;
}

/**
 * 벽 — 회전된 격자의 rc=0 · rr=0 두 변에 세운다. 늘 화면 뒤쪽이라 방 안을 가리지 않는다.
 * 스프라이트는 회전을 따라가지 않는다(화면 기준 방향이 고정이므로 faceSprite 를 쓰지 않는다).
 * 모서리는 wallCorner 한 장이 두 변을 덮는다 — 두 벽을 겹쳐 세우던 때의 어긋남이 없다.
 */
function wallItems(rot, walls, tone) {
  if (!walls) return [];
  const { cols, rows } = gridSize(rot);
  const dir = `walls/${tone}`;
  const out = [{ rc: 0, rr: 0, dir, layer: 0.5, sprite: WALL.corner }];
  const pick = (i, door, win, plain) =>
    i === WALL.doorAt ? door : i === WALL.winAt ? win : plain;
  for (let rr = 1; rr < rows; rr++)
    out.push({ rc: 0, rr, dir, layer: 0.5,
               sprite: pick(rr, WALL.doorLeft, WALL.winLeft, WALL.left) });
  for (let rc = 1; rc < cols; rc++)
    out.push({ rc, rr: 0, dir, layer: 0.5,
               sprite: pick(rc, WALL.doorRight, WALL.winRight, WALL.right) });
  return out;
}

/** 쓰일 수 있는 스프라이트를 4방향 전부 미리 읽는다. 회전이 끊기지 않으려면 필요하다. */
export async function preload() {
  const names = new Set();
  for (const it of build({})) names.add(`${it.dir}|${it.sprite}`);
  for (const r of SHELF) names.add(`library|${r.sprite}`);
  for (const tone of WALL.tones)
    for (const w of wallItems(0, true, tone)) names.add(`${w.dir}|${w.sprite}`);
  const jobs = [];
  for (const n of names) {
    const [dir, sprite] = n.split("|");
    for (let rot = 0; rot < 4; rot++) jobs.push(load(faceSprite(sprite, rot), dir));
  }
  const done = await Promise.all(jobs);
  return { total: jobs.length, missing: done.filter(x => !x).length };
}

/** 한 방향의 장면을 ctx 에 그린다 (동기 — 이미지는 preload 되어 있다) */
function paint(ctx, rot, reads, labels, walls, tone) {
  const box = sceneBox(rot);
  const items = build(reads)
    .map(it => {
      const r = rotate(it.col, it.row, rot);
      return { ...it, rc: r.col, rr: r.row, sprite: faceSprite(it.sprite, rot) };
    })
    .concat(wallItems(rot, walls, tone))
    .sort((a, b) => depth(a.rc, a.rr, a.layer) - depth(b.rc, b.rr, b.layer));

  const missing = new Set();
  for (const it of items) {
    const img = cache.get(`${it.dir}/${it.sprite}`);
    if (!img || img instanceof Promise) { missing.add(it.sprite); continue; }
    const p = spriteTopLeft(it.rc, it.rr, box.origin);
    ctx.drawImage(img, p.x, p.y);
  }
  if (labels) drawLabels(ctx, items, box.origin);
  return { box, missing: [...missing] };
}

function drawLabels(ctx, items, origin) {
  // 격자 좌표 — 겹침과 여백을 눈으로 재려고 띄운다. 라벨은 논리 좌표를 보여 준다.
  ctx.save();
  ctx.font = "16px monospace";
  ctx.textAlign = "center";
  for (const it of items) {
    if (it.layer !== 0) continue;
    const s = toScreen(it.rc, it.rr, origin);
    ctx.fillStyle = "rgba(0,0,0,.30)";
    ctx.fillText(`${it.col},${it.row}`, s.x, s.y + 4);
  }
  ctx.font = "bold 20px sans-serif";
  for (const it of items) {
    if (!it.name) continue;
    const s = toScreen(it.rc, it.rr, origin);
    const text = it.zone ? `📚 ${it.name}` : it.name;
    ctx.lineWidth = 5;
    ctx.strokeStyle = "rgba(255,255,255,.92)";
    ctx.strokeText(text, s.x, s.y - 150);
    ctx.fillStyle = "#1a1a1a";
    ctx.fillText(text, s.x, s.y - 150);
  }
  ctx.restore();
}

/**
 * view = { rot, turn, scale, pan }
 *   turn: -1~1. 지금 방향에서 다음 방향으로 넘어가는 중인 정도. 0이면 정지.
 */
export function draw(canvas, view) {
  const { rot = 0, turn = 0, scale = 0.45, pan = { x: 0, y: 0 },
          labels = true, reads = {}, walls = true, tone = WALL.tones[0] } = view;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const vw = canvas.clientWidth, vh = canvas.clientHeight;
  if (canvas.width !== vw * dpr || canvas.height !== vh * dpr) {
    canvas.width = vw * dpr; canvas.height = vh * dpr;
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, vw, vh);
  ctx.imageSmoothingEnabled = false;

  const t = Math.abs(turn);
  const dir = Math.sign(turn) || 1;
  const next = (rot + dir + 4) & 3;

  // 도는 동안 좌우로 살짝 흘려 준다 — 면이 바뀌는 순간을 눈이 덜 느낀다
  const SLIDE = 26;
  const layers = t > 0.001
    ? [{ r: rot, a: 1 - t, dx: -SLIDE * t * dir }, { r: next, a: t, dx: SLIDE * (1 - t) * dir }]
    : [{ r: rot, a: 1, dx: 0 }];

  let out = null;
  for (const L of layers) {
    ctx.save();
    ctx.globalAlpha = L.a;
    ctx.translate(pan.x + L.dx, pan.y);
    ctx.scale(scale, scale);
    const r = paint(ctx, L.r, reads, labels, walls, tone);
    ctx.restore();
    if (!out || L.a >= 0.5) out = r;
  }
  return out;
}

/** 장면이 뷰포트에 딱 들어오는 배율과 위치 */
export function fitView(canvas, rot) {
  const box = sceneBox(rot);
  const vw = canvas.clientWidth, vh = canvas.clientHeight;
  const scale = Math.min(vw / box.width, vh / box.height) * 0.96;
  return { scale, pan: { x: (vw - box.width * scale) / 2, y: (vh - box.height * scale) / 2 } };
}
