// 카메라 조작 — 마우스로 돌리고, 끌고, 확대한다.
//
// 왼쪽 드래그: 가로로 끌면 회전, 세로로 끌면 이동. 처음 몇 픽셀의 방향으로 정한다.
// 오른쪽·가운데 드래그: 항상 회전. 휠: 커서 기준 확대/축소.
import { fitView } from "./renderer.js";

const TURN_PX = 220;      // 이만큼 끌면 한 면이 넘어간다
const DEADZONE = 6;       // 드래그 의도를 가르는 최소 거리
const FLICK = 0.55;       // 튕김으로 볼 속도 (px/ms)

export function createView(canvas, onChange) {
  const v = { rot: 0, turn: 0, scale: 0.45, pan: { x: 0, y: 0 } };
  let drag = null, anim = null;

  const emit = () => onChange(v);

  function fit() {
    cancel();
    Object.assign(v, fitView(canvas, v.rot));
    v.turn = 0;
    emit();
  }

  function cancel() { if (anim) { cancelAnimationFrame(anim); anim = null; } }

  /** turn 을 목표까지 부드럽게 굴린다. 1 또는 -1 이면 면이 바뀐다. */
  function settle(to) {
    cancel();
    const from = v.turn, t0 = performance.now();
    const dur = 260 * Math.max(0.35, Math.abs(to - from));
    const step = now => {
      const k = Math.min(1, (now - t0) / dur);
      const e = 1 - Math.pow(1 - k, 3);          // ease-out-cubic
      v.turn = from + (to - from) * e;
      if (k < 1) { anim = requestAnimationFrame(step); emit(); return; }
      if (Math.abs(to) === 1) {
        // 면이 넘어갔다. 회전을 확정하고 카메라를 새 방향에 맞춘다.
        const keep = v.scale;
        v.rot = (v.rot + Math.sign(to) + 4) & 3;
        const f = fitView(canvas, v.rot);
        v.pan = f.pan; v.scale = keep;
      }
      v.turn = 0; anim = null; emit();
    };
    anim = requestAnimationFrame(step);
  }

  function turnBy(d) { if (!anim) settle(d); }

  canvas.addEventListener("contextmenu", e => e.preventDefault());

  canvas.addEventListener("pointerdown", e => {
    cancel();
    drag = {
      id: e.pointerId, x0: e.clientX, y0: e.clientY, t0: performance.now(),
      px: v.pan.x, py: v.pan.y,
      mode: e.button === 0 ? null : "turn",   // 왼쪽은 아직 정하지 않는다
      lastX: e.clientX, lastT: performance.now(), vx: 0,
    };
    canvas.setPointerCapture(e.pointerId);
    canvas.classList.add("drag");
  });

  canvas.addEventListener("pointermove", e => {
    if (!drag || e.pointerId !== drag.id) return;
    const dx = e.clientX - drag.x0, dy = e.clientY - drag.y0;

    if (drag.mode === null) {
      if (Math.hypot(dx, dy) < DEADZONE) return;
      drag.mode = Math.abs(dx) > Math.abs(dy) ? "turn" : "pan";
      canvas.classList.toggle("turning", drag.mode === "turn");
    }

    if (drag.mode === "pan") {
      v.pan.x = drag.px + dx; v.pan.y = drag.py + dy;
    } else {
      // 오른쪽으로 끌면 장면이 오른쪽으로 도는 느낌이 나도록 부호를 맞춘다
      v.turn = Math.max(-1, Math.min(1, -dx / TURN_PX));
      const now = performance.now(), dt = now - drag.lastT;
      if (dt > 0) drag.vx = (e.clientX - drag.lastX) / dt;
      drag.lastX = e.clientX; drag.lastT = now;
    }
    emit();
  });

  function release(e) {
    if (!drag || (e && e.pointerId !== drag.id)) return;
    const mode = drag.mode, vx = drag.vx;
    drag = null;
    canvas.classList.remove("drag", "turning");
    if (mode !== "turn") return;
    // 반 넘게 끌었거나 빠르게 튕겼으면 넘긴다. 아니면 제자리로 돌아온다.
    const flick = Math.abs(vx) > FLICK ? -Math.sign(vx) : 0;
    const to = Math.abs(v.turn) > 0.5 ? Math.sign(v.turn)
             : flick && Math.sign(flick) === Math.sign(v.turn || flick) ? flick : 0;
    settle(to);
  }
  for (const ev of ["pointerup", "pointercancel"]) canvas.addEventListener(ev, release);

  canvas.addEventListener("wheel", e => {
    e.preventDefault();
    const r = canvas.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    const next = Math.min(2.5, Math.max(0.12, v.scale * Math.exp(-e.deltaY * 0.0012)));
    const f = next / v.scale;
    v.pan.x = mx - (mx - v.pan.x) * f;
    v.pan.y = my - (my - v.pan.y) * f;
    v.scale = next;
    emit();
  }, { passive: false });

  return { v, fit, turnBy };
}
