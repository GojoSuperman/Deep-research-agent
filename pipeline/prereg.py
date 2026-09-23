"""사전 등록 실험 — 핵심 문서를 **먼저 적어 둔** 질문으로 팀과 혼자를 붙인다.

녹화 3편의 핵심 문서 목록은 녹화 **다음 날** 적었다. 결과를 본 사람이 쓴 목록으로 결과를
채점하는 순환이 될 수 있다(REPORT 4.2). data/questions.json 의 나머지 7건은 한 번도 돌린 적이
없고, 목록은 커밋 ea2fab8(2026-09-23 11:32)에 이미 들어 있다 — 그래서 이 7건이 사전 등록이다.

    python -m pipeline.prereg              # 없는 것만 돌린다
    python -m pipeline.prereg --only 추적  # id 에 '추적'이 든 것만

한 질문마다 팀(기본 설정) 한 편, 혼자 한 편. 혼자의 읽기 예산은 **그 질문에서 팀이 실제로
읽은 횟수**에 맞춘다 — 팀은 재위임 때문에 절수×절예산보다 더 읽는다(대조군과 같은 공정성 규칙).
저장: runs/사전등록/{id}-팀.json · {id}-혼자.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from . import baseline, events, graph
from .record import BASE

OUT = Path("runs/사전등록")
QFILE = Path("data/questions.json")


def list_commit() -> str:
    """질문 목록이 마지막으로 바뀐 커밋 — 녹화보다 먼저였다는 증거로 결과에 남긴다"""
    return subprocess.run(["git", "log", "-1", "--format=%h %ad", "--date=iso", "--", str(QFILE)],
                          capture_output=True, text=True).stdout.strip()


def main() -> None:
    p = argparse.ArgumentParser(description="사전 등록 질문으로 팀 vs 혼자")
    p.add_argument("--only", help="이 문자열이 든 id 만")
    a = p.parse_args()

    qs = [q for q in json.loads(QFILE.read_text(encoding="utf-8"))["질문"] if not q.get("녹화")]
    if a.only:
        qs = [q for q in qs if a.only in q["id"]]
    commit = list_commit()
    print(f"질문 {len(qs)}건 · 목록 커밋 {commit}\n")

    total = 0
    for i, q in enumerate(qs, 1):
        team_path, solo_path = OUT / f"{q['id']}-팀.json", OUT / f"{q['id']}-혼자.json"
        head = f"[{i}/{len(qs)}] {q['id']}"
        if team_path.exists() and solo_path.exists():
            print(f"{head}  건너뜀 (이미 있음)")
            continue
        try:
            t0 = time.time()
            out = graph.run(q["질문"], BASE, console=False)
            st, u = out["state"], out["usage"]
            team_reads = len(st.get("reads") or [])
            team_cost = (u["prompt"] * 0.15 + u["completion"] * 0.6) / 1e6 * 1400
            events.save(team_path, question=q["질문"], settings=BASE, metrics=st["metrics"],
                        report=st["report"], usage=u, 질문id=q["id"], 목록커밋=commit)

            solo = baseline.run(q["질문"], sections=BASE["sections"], budget=BASE["budget"],
                                reads_budget=team_reads, console=False)
            solo |= {"질문id": q["id"], "목록커밋": commit}
            solo_path.write_text(json.dumps(solo, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:  # 한 건이 깨져도 나머지는 이어서 간다
            print(f"{head}  ❌ {type(e).__name__}: {e}")
            continue
        total += team_cost + solo["cost_krw"]
        tm, sm = st["metrics"], solo["metrics"]
        print(f"{head}  {time.time() - t0:5.1f}초 · 팀 읽기 {team_reads} · "
              f"근거율 팀 {tm['근거율']} / 혼자 {sm['근거율']} · ₩{team_cost + solo['cost_krw']:.0f}")

    print(f"\n합계 약 ₩{total:.0f}")


if __name__ == "__main__":
    main()
