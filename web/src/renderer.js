// 렌더러 — 바닥·벽·가구·캐릭터. 화면은 한 방향 고정이다.
import { GRID, PROPS, ZONES, SHELF_SPRITE, GAUGE_MAX, GAUGE_DY, GAUGE_DX, ZONE_COLOR, SHELF_SCALE,
         DESKS, DESK_SPRITE, WALL, CARPETS, ASSETS, FURN, FACE, LAYER, TILE } from "./config.js";
import { foot, spriteTopLeft, depth, sceneBox } from "./iso.js";
import { allParts, drawActor, CAST } from "./actors.js";

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

const got = (name, dir) => {
  const v = cache.get(`${dir}/${name}`);
  return v && !(v instanceof Promise) ? v : null;
};



/** 캐릭터 기본 자리 — 소장은 책상 곁, 조사관 r1~r4 는 원탁 둘레 */
export function actorSpots() {
  return [
    { role: "coord", col: 2, row: 1 },
    ...DESKS.map((d, i) => ({ role: `r${i + 1}`, col: d.col, row: d.row })),
  ];
}

/** 바닥·가구·서고 — reads = { 서고이름: 읽은횟수 } */
export function build(reads = {}) {
  const items = [];
  for (let row = 0; row < GRID.rows; row++)
    for (let col = 0; col < GRID.cols; col++)
      items.push({ col, row, base: "floorFull", layer: LAYER.FLOOR });
  for (const c of CARPETS)
    items.push({ ...c, base: c.sprite, layer: LAYER.RUG,
                 face: c.face, scale: c.scale ?? 1 });
  for (const p of PROPS)
    items.push({ ...p, base: p.sprite, layer: p.layer ?? LAYER.PROP,
                 dy: p.dy ?? 0, dx: p.dx ?? 0, face: p.face,
                 scale: p.scale ?? 1, scaleY: p.scaleY ?? 1 });
  for (const z of ZONES)
    items.push({ ...z, base: SHELF_SPRITE, layer: LAYER.PROP, zone: true,
                 read: reads[z.name] || 0,
                 scale: SHELF_SCALE.x, scaleY: SHELF_SCALE.y });
  if (DESK_SPRITE)
    for (const d of DESKS) items.push({ ...d, base: DESK_SPRITE, layer: LAYER.PROP });
  return items;
}

/**
 * 벽 — 격자 **바깥 한 줄**(-1)에 세운다. 0행·0열에 세우면 벽 앞으로 바닥이 한 줄 남는다.
 * 두 변 모두 같은 스프라이트를 쓰고 0열 쪽만 좌우로 뒤집는다 — 그래야 색이 같다.
 */
function wallItems(walls) {
  if (!walls) return [];
  const pick = i => (i === WALL.doorAt ? WALL.door : i === WALL.winAt ? WALL.win : WALL.wall);
  const out = [];
  for (let row = 0; row < GRID.rows; row++)
    out.push({ col: -1, row, layer: LAYER.WALL, flip: true, sprite: pick(row) });
  for (let col = 0; col < GRID.cols; col++)
    out.push({ col, row: -1, layer: LAYER.WALL, sprite: pick(col) });
  return out;
}

export async function preload() {
  const jobs = [];
  const bases = new Set(["floorFull"]);
  for (const it of build({})) bases.add(it.base);
  for (const b of bases) jobs.push(load(b + FACE, FURN));
  for (const it of build({})) if (it.face) jobs.push(load(it.base + it.face, FURN));
  for (const w of wallItems(true)) jobs.push(load(w.sprite, FURN));
  for (const n of allParts()) jobs.push(load(n, "characters"));
  const done = await Promise.all(jobs);
  return { total: jobs.length, missing: done.filter(x => !x).length };
}

function paint(ctx, reads, labels, walls, actors) {
  const box = sceneBox();
  // 바닥은 평면이라 서로 가리지 않는다. **먼저 전부 깔고** 나머지를 깊이순으로 올린다.
  // 깊이순에 섞으면 앞 타일이 뒤 오브젝트의 다리를 덮는다 (캐비닛 다리가 잘려 보이던 원인).
  const all = build(reads)
    .map(it => ({ ...it, sprite: it.base + (it.face || FACE) }))
    .concat(wallItems(walls));
  const floors = all.filter(it => it.layer === LAYER.FLOOR);
  const items = floors.concat(
    all.filter(it => it.layer !== LAYER.FLOOR)
       .sort((a, b) => depth(a.col, a.row, a.layer) - depth(b.col, b.row, b.layer)));

  const missing = new Set();
  for (const it of items) {
    const img = got(it.sprite, FURN);
    if (!img) { missing.add(it.sprite); continue; }
    const p = spriteTopLeft(it.col, it.row, box.origin);
    p.y += it.dy || 0;          // 책상 위에 올리는 소품은 상판 높이만큼 띄운다
    p.x += it.dx || 0;
    const k = it.scale || 1, ky = k * (it.scaleY || 1);
    // 키울 때도 발이 놓인 자리는 그대로 — 바닥 앵커를 기준으로 확대한다
    const ax = p.x + img.width / 2, ay = p.y + img.height - TILE.H / 2;
    const dx = ax - (img.width / 2) * k, dy = ay - (img.height - TILE.H / 2) * ky;
    const w = img.width * k, h = img.height * ky;
    if (it.flip) {
      ctx.save();
      ctx.translate(dx + w, dy);
      ctx.scale(-1, 1);
      ctx.drawImage(img, 0, 0, w, h);
      ctx.restore();
    } else {
      ctx.drawImage(img, dx, dy, w, h);
    }
  }

  // 캐릭터는 깊이순으로 가구 사이에 끼워 그린다 (앞뒤가 맞아야 방 안을 걷는 것처럼 보인다)
  const cast = [...actors].sort((a, b) => (a.col + a.row) - (b.col + b.row));
  for (const a of cast) {
    const f = foot(a.col, a.row, box.origin);
    drawActor(ctx, n => got(n, "characters"), a.role, a.state || "idle", f.x, f.y);
  }
  if (labels) drawLabels(ctx, items, actors, box.origin);
  return { box, missing: [...missing] };
}

/** 서고 위 게이지 — 읽은 횟수가 막대로 차오른다 */
function drawGauge(ctx, x, y, zone) {
  const W = 110, H = 14;
  const v = Math.min(zone.read / GAUGE_MAX, 1);
  const color = ZONE_COLOR[zone.name] || "#888";
  ctx.save();
  ctx.textAlign = "center";
  // 이름
  ctx.font = "bold 20px sans-serif";
  ctx.lineWidth = 5;
  ctx.strokeStyle = "rgba(255,255,255,.92)";
  ctx.strokeText(zone.name, x, y - 8);
  ctx.fillStyle = "#1a1a1a";
  ctx.fillText(zone.name, x, y - 8);
  // 막대
  ctx.fillStyle = "rgba(255,255,255,.85)";
  ctx.fillRect(x - W / 2 - 2, y - 2, W + 4, H + 4);
  ctx.fillStyle = "#ddd6c9";
  ctx.fillRect(x - W / 2, y, W, H);
  ctx.fillStyle = color;
  ctx.fillRect(x - W / 2, y, W * v, H);
  ctx.strokeStyle = "rgba(0,0,0,.25)";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(x - W / 2, y, W, H);
  // 횟수
  ctx.font = "bold 16px sans-serif";
  ctx.fillStyle = "#1a1a1a";
  ctx.fillText(String(zone.read), x + W / 2 + 16, y + H - 1);
  ctx.restore();
}

function drawLabels(ctx, items, actors, origin) {
  ctx.save();
  ctx.font = "bold 23px sans-serif";       // 이름표 — 멀리서도 읽히게
  ctx.textAlign = "center";
  const tag = (x, y, text) => {
    ctx.lineWidth = 6;
    ctx.strokeStyle = "rgba(255,255,255,.92)";
    ctx.strokeText(text, x, y);
    ctx.fillStyle = "#1a1a1a";
    ctx.fillText(text, x, y);
  };
  for (const it of items) {
    if (!it.name) continue;
    const f = foot(it.col, it.row, origin);
    if (it.zone) drawGauge(ctx, f.x + GAUGE_DX, f.y + GAUGE_DY, it);
    else tag(f.x, f.y - 150, it.name);
  }
  for (const a of actors) {
    const f = foot(a.col, a.row, origin);
    tag(f.x, f.y - 122, CAST[a.role]?.label || a.role);
    if (a.say) say(ctx, f.x, f.y - 152, a.say);
  }
  ctx.restore();
}

/** 격자 눈금 — 어느 칸에 무엇이 놓였는지 눈으로 재는 자 (개발용, G 키) */
function drawGrid(ctx, origin) {
  ctx.save();
  ctx.font = "bold 15px sans-serif";
  ctx.textAlign = "center";
  for (let row = 0; row < GRID.rows; row++)
    for (let col = 0; col < GRID.cols; col++) {
      const f = foot(col, row, origin);
      ctx.beginPath();
      ctx.moveTo(f.x, f.y - TILE.H / 2);
      ctx.lineTo(f.x + TILE.W / 2, f.y);
      ctx.lineTo(f.x, f.y + TILE.H / 2);
      ctx.lineTo(f.x - TILE.W / 2, f.y);
      ctx.closePath();
      ctx.strokeStyle = "rgba(200,40,40,.55)";
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.lineWidth = 4;
      ctx.strokeStyle = "rgba(255,255,255,.85)";
      ctx.strokeText(`${col},${row}`, f.x, f.y + 6);
      ctx.fillStyle = "#b02020";
      ctx.fillText(`${col},${row}`, f.x, f.y + 6);
    }
  ctx.restore();
}

/** 말풍선 — 지금 무엇을 하는지 한 줄 */
function say(ctx, x, y, text) {
  const t = text.length > 38 ? text.slice(0, 37) + "…" : text;
  ctx.save();
  ctx.font = "21px sans-serif";            // 말풍선
  ctx.textAlign = "center";
  const w = ctx.measureText(t).width + 22;
  ctx.fillStyle = "rgba(255,255,255,.93)";
  ctx.strokeStyle = "rgba(0,0,0,.18)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.roundRect(x - w / 2, y - 27, w, 33, 9);
  ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#1a1a1a";
  ctx.fillText(t, x, y - 5);
  ctx.restore();
}

export function draw(canvas, view) {
  const { scale = 0.45, pan = { x: 0, y: 0 },
          labels = true, reads = {}, walls = true, actors = [], grid = false } = view;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const vw = canvas.clientWidth, vh = canvas.clientHeight;
  if (canvas.width !== vw * dpr || canvas.height !== vh * dpr) {
    canvas.width = vw * dpr; canvas.height = vh * dpr;
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, vw, vh);
  ctx.imageSmoothingEnabled = true;
  ctx.save();
  ctx.translate(pan.x, pan.y);
  ctx.scale(scale, scale);
  const r = paint(ctx, reads, labels, walls, actors);
  if (grid) drawGrid(ctx, sceneBox().origin);
  ctx.restore();
  return r;
}

/** 장면이 뷰포트에 딱 들어오는 배율과 위치 */
export function fitView(canvas) {
  const box = sceneBox();
  const vw = canvas.clientWidth, vh = canvas.clientHeight;
  const scale = Math.min(vw / box.width, vh / box.height) * 0.995;
  return { scale, pan: { x: (vw - box.width * scale) / 2, y: (vh - box.height * scale) / 2 } };
}
