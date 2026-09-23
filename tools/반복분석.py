"""반복 녹화 분석 — 절제 실험 12칸을 칸마다 3회로 보고, 「지표 ← 장치」 매핑을 다시 판정한다.

    .venv/bin/python tools/반복분석.py

1회차 runs/{질문}-{설정}.json + 2·3회차 runs/반복/{질문}-{설정}-{k}.json (python -m pipeline.repeat).
판정은 셋 중 하나 — 기본 설정과 견준다.
  분명  질문 셋 모두 같은 방향이고, 적어도 둘에서 3회 범위가 기본과 겹치지 않는다
  기울  질문 셋 모두 같은 방향이지만 범위가 겹친다
  없음  질문마다 방향이 다르다
n=3 이라 「분명」도 통계적 검정이 아니다 — 범위가 안 겹쳤다는 관찰일 뿐이다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.corpus import load  # noqa: E402
from pipeline.metrics import citations  # noqa: E402
from pipeline.record import QUESTIONS, SETTINGS  # noqa: E402

corpus = load()


def runs_of(q: str, s: str) -> list[dict]:
    files = [ROOT / "runs" / f"{q}-{s}.json"] + sorted((ROOT / "runs" / "반복").glob(f"{q}-{s}-*.json"))
    return [json.loads(f.read_text(encoding="utf-8")) for f in files if f.exists()]


def shelves(run: dict) -> int:
    """1회차 녹화는 인용서고수가 생기기 전이라 보고서로 잰다 (보고서 인용 = 지표 인용, 확인함)"""
    m = run["metrics"]
    if "인용서고수" in m:
        return m["인용서고수"]
    return len({corpus.group(d) for d in citations(run["report"])} - {"미분류"})


PICK = {
    "근거율": lambda r: r["metrics"]["근거율"],
    "중복률": lambda r: r["metrics"]["중복률"],
    "편중": lambda r: r["metrics"]["최다문서편중"],
    "인용서고수": shelves,
    "인용0곳절": lambda r: r["metrics"]["인용0곳절수"],
    "허위인용": lambda r: r["metrics"]["허위인용"],
    "그물통과": lambda r: 1 if r["metrics"]["그물"]["통과"] else 0,
}

# 보고서 3장의 매핑 — (지표, 끄는 설정, 끄면 기대하는 방향 +1/-1)
MAPPINGS = [
    ("중복률", "배정구역끔", +1, "중복률 ← 구역"),
    ("인용서고수", "배정구역끔", -1, "인용 서고 ← 배정"),
    ("인용0곳절", "재위임끔", +1, "인용 0곳 절 ← 재위임"),
    ("허위인용", "배정구역끔", +1, "허위 인용 ← 허용 목록(배정)"),
    ("근거율", "역할끔", -1, "근거율 ← 역할 (메모리: n=1 에선 끄는 쪽이 2/3 나음)"),
    ("근거율", "배정구역끔", -1, "근거율 ← 배정·구역"),
]


def cell(vals: list[float]) -> str:
    return f"{mean(vals):.2f} [{min(vals):.2f}–{max(vals):.2f}]" if vals else "—"


def main() -> int:
    table = {(q, s): runs_of(q, s) for q in QUESTIONS for s in SETTINGS}
    ns = {len(v) for v in table.values()}
    print(f"칸 {len(table)}개 · 칸당 회차 {sorted(ns)}\n")

    for key in ("근거율", "중복률", "편중", "인용서고수"):
        print(f"── {key} — 평균 [최소–최대]")
        print(f"{'':6}" + "".join(f"{s:>22}" for s in SETTINGS))
        for q in QUESTIONS:
            print(f"{q:6}" + "".join(f"{cell([PICK[key](r) for r in table[(q, s)]]):>22}" for s in SETTINGS))
        print()

    print("── 경보가 울린 회차 수 (칸당 3회 중)")
    for key in ("인용0곳절", "허위인용"):
        row = {s: sum(1 for q in QUESTIONS for r in table[(q, s)] if PICK[key](r) > 0) for s in SETTINGS}
        print(f"  {key:8} " + " · ".join(f"{s} {v}/{sum(len(table[(q, s)]) for q in QUESTIONS)}" for s, v in row.items()))
    row = {s: sum(PICK["그물통과"](r) for q in QUESTIONS for r in table[(q, s)]) for s in SETTINGS}
    print(f"  그물 통과 " + " · ".join(f"{s} {v}/{sum(len(table[(q, s)]) for q in QUESTIONS)}" for s, v in row.items()))

    print("\n── 매핑 판정 (끈 설정 vs 기본)")
    for key, off, want, label in MAPPINGS:
        signs, apart = [], 0
        for q in QUESTIONS:
            base = [PICK[key](r) for r in table[(q, "기본")]]
            test = [PICK[key](r) for r in table[(q, off)]]
            d = mean(test) - mean(base)
            signs.append(0 if abs(d) < 1e-9 else (1 if d > 0 else -1))
            if min(test) > max(base) or max(test) < min(base):
                apart += 1
        same = len(set(signs)) == 1 and signs[0] != 0
        verdict = ("분명" if same and apart >= 2 else "기울" if same else "없음")
        agree = "기대대로" if same and signs[0] == want else ("기대와 반대" if same else "")
        arrows = " ".join({1: "↑", -1: "↓", 0: "="}[x] for x in signs)
        print(f"  {label:42} 질문별 {arrows} · 범위 분리 {apart}/3 → {verdict} {agree}")
    team_vs_solo()
    return 0


def team_vs_solo() -> None:
    """팀(기본) 3회 vs 혼자 3회 — 혼자는 runs/대조군-{질문}.json + runs/반복/대조군-{질문}-{k}.json"""
    print("\n── 팀(기본) vs 혼자 — 근거율 3회씩, 흔들림 폭, 그물 통과")
    for q in QUESTIONS:
        solo_files = [ROOT / "runs" / f"대조군-{q}.json"] + sorted((ROOT / "runs" / "반복").glob(f"대조군-{q}-*.json"))
        solo = [json.loads(f.read_text(encoding="utf-8")) for f in solo_files if f.exists()]
        team = runs_of(q, "기본")
        if len(solo) < 2:
            continue
        t = [r["metrics"]["근거율"] for r in team]
        s_ = [r["metrics"]["근거율"] for r in solo]
        passed = lambda rs: sum(1 for r in rs if r["metrics"]["그물"]["통과"])
        who = "팀" if mean(t) > mean(s_) else "혼자"
        overlap = "겹침" if min(t) <= max(s_) and min(s_) <= max(t) else "분리"
        print(f"  {q:4} 팀 {cell(t)} · 혼자 {cell(s_)} → 평균 {who} 쪽, 범위 {overlap} · "
              f"폭 {max(t) - min(t):.2f}/{max(s_) - min(s_):.2f} · 그물 {passed(team)}/{len(team)} vs {passed(solo)}/{len(solo)}")


if __name__ == "__main__":
    raise SystemExit(main())
