"""반복 녹화 — 절제 실험 12칸을 칸마다 3회로 (REPORT 7장 「n을 늘려 재기」).

녹화 12편(runs/*.json)이 1회차다. 여기서 2·3회차를 만든다.
    python -m pipeline.repeat              # 없는 것만 돌린다
    python -m pipeline.repeat --only 관계  # 이름에 '관계'가 든 것만
    python -m pipeline.repeat --solo       # 혼자 대조군 2·3회차 (runs/반복/대조군-{질문}-{k}.json)

저장: runs/반복/{질문}-{설정}-{회차}.json — 화면 재생용(web/runs/)과 1회차는 건드리지 않는다.
교육용 키라 잔액을 볼 수 없다. **잔액 부족(insufficient_quota)이 나오면 그 자리에서 멈춘다** —
남은 칸을 계속 두드려 봐야 전부 실패한다. 다시 돌리면 없는 것부터 이어 간다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import time
from pathlib import Path

import json

from . import baseline, events, graph
from .record import BASE, QUESTIONS, SETTINGS

OUT = Path("runs/반복")
ROUNDS = (2, 3)          # 1회차는 runs/{질문}-{설정}.json


def main() -> None:
    p = argparse.ArgumentParser(description="절제 실험 반복 녹화")
    p.add_argument("--only", help="이 문자열이 든 이름만")
    p.add_argument("--solo", action="store_true", help="혼자 대조군을 반복한다")
    a = p.parse_args()
    if a.solo:
        return solo(a.only)

    plan = [(q, s, k) for k in ROUNDS for q in QUESTIONS for s in SETTINGS]
    if a.only:
        plan = [x for x in plan if a.only in f"{x[0]}-{x[1]}"]
    today = dt.date.today().isoformat()
    total, done = 0.0, 0
    for i, (q, s, k) in enumerate(plan, 1):
        path = OUT / f"{q}-{s}-{k}.json"
        head = f"[{i}/{len(plan)}] {path.name}"
        if path.exists():
            print(f"{head}  건너뜀 (이미 있음)", flush=True)
            continue
        t0 = time.time()
        settings = {**BASE, **SETTINGS[s]}
        try:
            out = graph.run(QUESTIONS[q], settings, console=False)
        except Exception as e:
            if "insufficient_quota" in str(e) or "quota" in str(e).lower():
                print(f"{head}  ⛔ 잔액 부족 — 여기서 멈춘다 ({type(e).__name__})", flush=True)
                break
            print(f"{head}  ❌ {type(e).__name__}: {str(e)[:120]}", flush=True)
            continue
        st, u = out["state"], out["usage"]
        events.save(path, question=QUESTIONS[q], settings=settings, metrics=st["metrics"],
                    report=st["report"], usage=u, built=today,
                    label={"질문": q, "설정": s, "회차": k})
        cost = (u["prompt"] * 0.15 + u["completion"] * 0.6) / 1e6 * 1400
        total += cost
        done += 1
        m = st["metrics"]
        print(f"{head}  {time.time() - t0:5.1f}초 · 근거율 {m['근거율']} · "
              f"그물 {'통과' if m['그물']['통과'] else '탈락'} · ₩{cost:.0f} (누적 ₩{total:.0f})", flush=True)

    print(f"\n녹화 {done}편 · 합계 약 ₩{total:.0f}")


def solo(only: str | None) -> None:
    """혼자 대조군 반복 — 팀의 흔들림은 3회로 알았는데 혼자의 흔들림은 모른다(REPORT 4.2).
    읽기 예산은 1회차(runs/대조군-{질문}.json)에 적힌 값을 그대로 쓴다 — 조건은 두고 흔들림만 잰다."""
    plan = [(q, k) for k in ROUNDS for q in QUESTIONS if not only or only in q]
    total = 0.0
    for i, (q, k) in enumerate(plan, 1):
        path = OUT / f"대조군-{q}-{k}.json"
        head = f"[{i}/{len(plan)}] {path.name}"
        if path.exists():
            print(f"{head}  건너뜀 (이미 있음)", flush=True)
            continue
        first = json.loads(Path(f"runs/대조군-{q}.json").read_text(encoding="utf-8"))
        t0 = time.time()
        try:
            out = baseline.run(QUESTIONS[q], sections=BASE["sections"], budget=BASE["budget"],
                               reads_budget=first["예산"], console=False)
        except Exception as e:
            if "quota" in str(e).lower():
                print(f"{head}  ⛔ 잔액 부족 — 여기서 멈춘다 ({type(e).__name__})", flush=True)
                break
            print(f"{head}  ❌ {type(e).__name__}: {str(e)[:120]}", flush=True)
            continue
        out |= {"회차": k}
        OUT.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        total += out["cost_krw"]
        print(f"{head}  {time.time() - t0:5.1f}초 · 예산 {first['예산']} · 근거율 {out['metrics']['근거율']} · "
              f"₩{out['cost_krw']} (누적 ₩{total:.0f})", flush=True)
    print(f"\n합계 약 ₩{total:.0f}")


if __name__ == "__main__":
    main()
