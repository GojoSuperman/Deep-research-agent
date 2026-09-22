// 카메라 조작 — 끌어서 이동, 휠로 확대/축소. 회전은 없다.
import { fitView } from "./renderer.js";

export function createView(canvas, onChange) {
  const v = { scale: 0.45, pan: { x: 0, y: 0 } };
  const emit = () => onChange(v);

  function fit() {
    Object.assign(v, fitView(canvas));
    emit();
  }

  let drag = null;
  canvas.addEventListener("pointerdown", e => {
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
    const r = canvas.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    const next = Math.min(2.5, Math.max(0.12, v.scale * Math.exp(-e.deltaY * 0.0012)));
    const f = next / v.scale;
    v.pan.x = mx - (mx - v.pan.x) * f;
    v.pan.y = my - (my - v.pan.y) * f;
    v.scale = next;
    emit();
  }, { passive: false });

  return { v, fit };
}
