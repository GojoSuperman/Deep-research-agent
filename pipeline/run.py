"""한 번 돌려 보는 실행기 — python -m pipeline.run"""
from __future__ import annotations

import argparse
import json

from . import graph
from .state import DEFAULT_SETTINGS

QUESTION = "MBTI 궁합론은 어떤 근거로 제시되며, 심리학계는 이를 어떻게 평가하는가?"


def main() -> None:
    p = argparse.ArgumentParser(description="딥리서치 에이전트 한 바퀴")
    p.add_argument("-q", "--question", default=QUESTION)
    p.add_argument("--sections", type=int, default=DEFAULT_SETTINGS["sections"])
    p.add_argument("--budget", type=int, default=DEFAULT_SETTINGS["budget"])
    p.add_argument("--no-assign", action="store_true")
    p.add_argument("--no-zone", action="store_true")
    p.add_argument("--no-role", action="store_true")
    p.add_argument("--no-redelegate", action="store_true")
    p.add_argument("--quiet", action="store_true", help="이벤트를 찍지 않는다")
    p.add_argument("--save", help="이벤트 스트림을 저장할 경로 (runs/*.json)")
    a = p.parse_args()

    settings = {
        "sections": a.sections, "budget": a.budget,
        "assign": not a.no_assign, "zone": not a.no_zone,
        "role": not a.no_role, "redelegate": not a.no_redelegate,
    }
    out = graph.run(a.question, settings, console=not a.quiet)
    state = out["state"]

    print("\n── 계기판 ─────────────────────────────")
    m = dict(state["metrics"])
    net = m.pop("그물")
    detail = m.pop("출처불일치문장", [])
    for k, v in m.items():
        print(f"  {k:<12} {v}")
    for x in detail:
        print(f"    ⚠ {x['인용']} 에 없는 말 {x['원문에없음']}: {x['문장'][:70]}")
    print(f"  {'그물':<12} {'통과' if net['통과'] else '탈락: ' + ', '.join(net['사유'])}")
    u = out["usage"]
    cost = u["prompt"] / 1e6 * 0.15 + u["completion"] / 1e6 * 0.6  # gpt-4o-mini 기준
    print(f"\n  이벤트 {len(out['events'])}개 · 보고서 {len(state['report'])}자")
    print(f"  호출 {u['calls']}회 · 입력 {u['prompt']:,} 출력 {u['completion']:,} 토큰 "
          f"· 약 ${cost:.3f} (₩{cost * 1400:.0f})")

    if a.save:
        from pathlib import Path
        from . import events
        path = events.save(Path(a.save), question=a.question, settings=settings,
                           metrics=state["metrics"], report=state["report"],
                           usage=u, built="2026-09-22")
        print(f"  저장 → {path}")


if __name__ == "__main__":
    main()
