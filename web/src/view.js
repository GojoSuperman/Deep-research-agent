// 카메라 — 끌어서 이동, 휠로 확대/축소. 회전은 없다.
// 연출이 부르는 focus() 가 있다. 목표값으로 매 프레임 당겨 간다(보간).
// 사람이 끌거나 휠을 굴리면 그 순간 목표를 버린다 — 조작이 연출에 지지 않아야 한다.
import { fitView } from "./renderer.js";
import { foot, sceneBox } from "./iso.js";
import { STEP } from "./config.js";

export function createView(canvas, onChange) {
  const v = { scale: 0.45, pan: { x: 0, y: 0 } };
  const emit = () => onChange(v);
  let goal = null;
  let touched = false;      // 사람이 끌거나 휠을 굴렸나 — 그러면 자동 맞춤을 멈춘다

  // 마지막으로 본 캔버스 크기와 그때의 맞춤 배율.
  // 창이 바뀌었을 때 "얼마나 커졌나"를 재는 기준이다.
  let seen = null;
  const note = () => { seen = { vw: canvas.clientWidth, vh: canvas.clientHeight,
                                fit: fitView(canvas).scale }; };

  function fit() {
    goal = null;
    touched = false;
    Object.assign(v, fitView(canvas));
    note();
    emit();
  }

  /**
   * 창 크기가 바뀌었을 때 — 사람이 잡아 둔 화면도 창을 따라 같이 커지고 작아진다.
   * 확대 비율과 보고 있던 지점은 그대로 두고, 창이 커진 비율만큼만 배율을 곱한다.
   * 이게 없으면 한 번 휠을 굴린 뒤로는 창을 늘려도 사무실이 그 크기에 머문다.
   */
  function rescale() {
    const vw = canvas.clientWidth, vh = canvas.clientHeight;
    if (!vw || !vh) return;
    if (!seen || !seen.vw || !seen.vh) { note(); return; }
    const k = fitView(canvas).scale / seen.fit;
    // 바뀌기 전 화면 한가운데에 있던 장면 지점 — 바뀐 뒤에도 가운데에 둔다
    const px = (seen.vw / 2 - v.pan.x) / v.scale;
    const py = (seen.vh / 2 - v.pan.y) / v.scale;
    v.scale *= k;
    v.pan.x = vw / 2 - px * v.scale;
    v.pan.y = vh / 2 - py * v.scale;
    note();
    emit();
  }

  /** 타일 한 자리를 화면 가운데 놓는다. span = 가로로 몇 칸이 보이게 할지 */
  function aim(col, row, span) {
    const box = sceneBox();
    const f = foot(col, row, box.origin);
    const vw = canvas.clientWidth, vh = canvas.clientHeight;
    const fitS = fitView(canvas).scale;
    const scale = Math.min(fitS * 2.2, Math.max(fitS, vw / (span * STEP.X * 2)));
    return { scale, pan: { x: vw / 2 - f.x * scale, y: vh / 2 - f.y * scale } };
  }

  /** 연출용 — null 이면 방 전체로 돌아간다 */
  function focus(spot) {
    touched = false;
    goal = spot ? aim(spot.col, spot.row, spot.span ?? 7) : fitView(canvas);
    note();
  }

  /** 매 프레임 목표로 당긴다 */
  function step(dt) {
    if (!goal) return false;
    const k = 1 - Math.exp(-dt * 2.6);
    v.scale += (goal.scale - v.scale) * k;
    v.pan.x += (goal.pan.x - v.pan.x) * k;
    v.pan.y += (goal.pan.y - v.pan.y) * k;
    if (Math.abs(goal.scale - v.scale) < 1e-4 &&
        Math.abs(goal.pan.x - v.pan.x) < 0.5 && Math.abs(goal.pan.y - v.pan.y) < 0.5) {
      Object.assign(v, goal, { pan: { ...goal.pan } });
      goal = null;
    }
    return true;
  }

  let drag = null;
  canvas.addEventListener("pointerdown", e => {
    goal = null; touched = true;      // 사람이 잡으면 연출은 손을 뗀다
    drag = { id: e.pointerId, x: e.clientX - v.pan.x, y: e.clientY - v.pan.y };
    canvas.setPointerCapture(e.pointerId);
    canvas.classList.add("drag");
  });
  canvas.addEventListener("pointermove", e => {
    if (!drag || e.pointerId !== drag.id) return;
    v.pan.x = e.clientX - drag.x;
    v.pan.y = e.clientY - drag.y;
    emit();
  });
  for (const ev of ["pointerup", "pointercancel"])
    canvas.addEventListener(ev, () => { drag = null; canvas.classList.remove("drag"); });

  canvas.addEventListener("wheel", e => {
    e.preventDefault();
    goal = null; touched = true;
    const r = canvas.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    const next = Math.min(2.5, Math.max(0.12, v.scale * Math.exp(-e.deltaY * 0.0012)));
    const f = next / v.scale;
    v.pan.x = mx - (mx - v.pan.x) * f;
    v.pan.y = my - (my - v.pan.y) * f;
    v.scale = next;
    emit();
  }, { passive: false });

  return { v, fit, focus, step, rescale, touched: () => touched };
}
