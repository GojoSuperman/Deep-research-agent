"""녹화 생성기 — 질문 3 × 설정 4 = 12편 (계획서 7장).

    python -m pipeline.record              # 없는 것만 돌린다
    python -m pipeline.record --force      # 전부 다시 돌린다
    python -m pipeline.record --only 관계  # 이름에 '관계'가 든 것만

이벤트 버퍼가 프로세스 전역이라 병렬로 돌리지 못한다. 한 편씩 순서대로 간다.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from . import events, graph

BUILT = "2026-09-22"
OUT = Path("runs")

# 질문은 data/questions.json 이 단일 출처다. 두 군데 적으면 갈라진다.
# 그중 "녹화": true 인 것만 녹화한다 (계획서 7.1 — 성격이 다른 질문 셋).
def load_questions() -> dict[str, str]:
    data = json.loads(Path("data/questions.json").read_text(encoding="utf-8"))
    picked = {q["녹화이름"]: q["질문"] for q in data["질문"] if q.get("녹화")}
    if not picked:
        raise SystemExit("data/questions.json 에 녹화할 질문이 없다")
    return picked


QUESTIONS = load_questions()

# 계획서 7.2 — 끄는 것만 적는다. 나머지는 켠 상태
SETTINGS = {
    "기본": {},
    "배정구역끔": {"assign": False, "zone": False},
    "역할끔": {"role": False},
    "재위임끔": {"redelegate": False},
}

BASE = {"sections": 4, "budget": 3, "assign": True, "zone": True, "role": True, "redelegate": True}


def record_one(qname: str, sname: str, path: Path) -> dict:
    question, settings = QUESTIONS[qname], {**BASE, **SETTINGS[sname]}
    out = graph.run(question, settings, console=False)
    state = out["state"]
    events.save(path, question=question, settings=settings, metrics=state["metrics"],
                report=state["report"], usage=out["usage"], built=BUILT,
                label={"질문": qname, "설정": sname})
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="녹화 12편 생성")
    p.add_argument("--force", action="store_true", help="이미 있는 것도 다시 돌린다")
    p.add_argument("--only", help="이 문자열이 든 이름만 돌린다")
    a = p.parse_args()

    plan = [(q, s) for q in QUESTIONS for s in SETTINGS]
    if a.only:
        plan = [x for x in plan if a.only in f"{x[0]}-{x[1]}"]

    total_cost, done, skipped = 0.0, 0, 0
    for i, (qname, sname) in enumerate(plan, 1):
        path = OUT / f"{qname}-{sname}.json"
        head = f"[{i}/{len(plan)}] {path.name}"
        if path.exists() and not a.force:
            print(f"{head}  건너뜀 (이미 있음)")
            skipped += 1
            continue
        t0 = time.time()
        try:
            out = record_one(qname, sname, path)
        except Exception as e:  # 한 편이 깨져도 나머지는 이어서 간다
            print(f"{head}  ❌ {type(e).__name__}: {e}")
            continue
        m, u = out["state"]["metrics"], out["usage"]
        cost = u["prompt"] / 1e6 * 0.15 + u["completion"] / 1e6 * 0.6
        total_cost += cost
        done += 1
        net = m["그물"]
        print(f"{head}  {time.time() - t0:5.1f}초 · 이벤트 {len(out['events']):3d} · "
              f"근거율 {m.get('근거율')} · 그물 {'통과' if net['통과'] else '탈락(' + ', '.join(net['사유']) + ')'} "
              f"· ₩{cost * 1400:.0f}")

    print(f"\n녹화 {done}편 · 건너뜀 {skipped}편 · 합계 약 ₩{total_cost * 1400:.0f}")


if __name__ == "__main__":
    main()
