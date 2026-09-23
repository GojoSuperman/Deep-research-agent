"""서고를 고르게 밟았는가 — 녹화 15편(팀 12 · 혼자 3)을 보고서 본문으로 다시 잰다.

근거율은 한 문서만 되풀이 인용해도 오른다. 그래서 **어디서** 근거를 가져왔는지를 본다.
    .venv/bin/python tools/서고커버리지.py

재는 것 넷 — 앞의 둘은 정답표가 없고, 뒤의 둘은 질문 목록(data/questions.json)에 기댄다.
  인용 서고 수   보고서가 인용한 문서가 몇 개 서고에 걸치나 (metrics.compute 에도 있다)
  서고 분포      서고별 인용 수
  필수 서고 누락 질문의 「닿아야 할 서고」 중 인용이 한 곳도 없는 서고
  핵심 문서 도달 질문의 「핵심 문서」 중 실제로 인용된 비율

⚠ 뒤의 둘은 **순환 위험**이 있다. questions.json 은 녹화(2026-09-22) 다음 날 적었다 —
  결과를 본 사람이 쓴 목록으로 결과를 채점하는 셈이 될 수 있다. 그래서 metrics.py 에 넣지 않고
  (지표는 정답표를 쓰지 않는다), 여기서 참고로만 잰다. 새 질문으로 녹화하기 **전에** 목록을 적어야
  이 둘을 믿을 수 있다.

사전 등록 7건(runs/사전등록/, python -m pipeline.prereg)은 목록을 녹화 **전에** 적은 질문이라
순환이 없다 — 이 도구의 뒤 표가 그것이다. 팀/혼자를 가르는 결론은 이 표로 낸다.

팀 녹화는 절별 원고를 저장하지 않았다. 보고서 본문의 인용 수가 15편 모두 지표의 인용 수와
같은 것을 확인하고(2026-09-23) 보고서로 잰다.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.corpus import load  # noqa: E402
from pipeline.metrics import citations  # noqa: E402


def question_of(name: str) -> str:
    """녹화 이름 → 질문 녹화이름. 「다갈래-기본」 → 다갈래, 「대조군-관계」 → 관계"""
    head, tail = name.split("-", 1)
    return tail if head == "대조군" else head


def measure(report: str, q: dict, corpus) -> dict:
    cites = citations(report)
    shelves = Counter(corpus.group(d) for d in cites)
    shelves.pop("미분류", None)
    cited = set(cites)
    core = q["핵심 문서"]
    return {
        "인용수": len(cites),
        "인용서고수": len(shelves),
        "서고분포": dict(shelves.most_common()),
        "필수서고누락": [s for s in q["닿아야 할 서고"] if not shelves.get(s)],
        "핵심문서도달": round(sum(d in cited for d in core) / len(core), 2),
    }


def main() -> int:
    corpus = load()
    qs = {q["녹화이름"]: q for q in json.loads((ROOT / "data/questions.json").read_text(encoding="utf-8"))["질문"]
          if q.get("녹화이름")}
    rows = {}
    for f in sorted((ROOT / "runs").glob("*.json")):
        run = json.loads(f.read_text(encoding="utf-8"))
        rows[f.stem] = measure(run["report"], qs[question_of(f.stem)], corpus)

    print(f"{'녹화':14} {'서고수':>4} {'핵심문서':>6}  필수 서고 누락 · 서고 분포")
    for name, m in rows.items():
        miss = ",".join(m["필수서고누락"]) or "-"
        dist = " ".join(f"{k}{v}" for k, v in m["서고분포"].items())
        print(f"{name:14} {m['인용서고수']:>4} {m['핵심문서도달']:>6.2f}  {miss:12} {dist}")

    print("\n팀(기본) vs 혼자 — 같은 질문, 같은 읽기 예산")
    for qn in ("단일", "다갈래", "관계"):
        t, s = rows[f"{qn}-기본"], rows[f"대조군-{qn}"]
        print(f"  {qn:4} 서고수 {t['인용서고수']} / {s['인용서고수']} · "
              f"핵심문서 {t['핵심문서도달']:.2f} / {s['핵심문서도달']:.2f} · "
              f"누락 {','.join(t['필수서고누락']) or '-'} / {','.join(s['필수서고누락']) or '-'}")
    print("\n⚠ 위 표의 핵심문서·필수서고는 녹화 다음 날 적은 목록이다 — 참고로만 본다 (이 파일 첫머리)")

    prereg(corpus)
    return 0


def prereg(corpus) -> None:
    """사전 등록 — 목록을 녹화보다 먼저 적은 질문. 팀과 혼자를 같은 읽기 예산으로 붙였다."""
    folder = ROOT / "runs" / "사전등록"
    by_id = {q["id"]: q for q in json.loads((ROOT / "data/questions.json").read_text(encoding="utf-8"))["질문"]}
    pairs = sorted({f.stem.rsplit("-", 1)[0] for f in folder.glob("*-팀.json")}) if folder.exists() else []
    if not pairs:
        return
    commit = json.loads((folder / f"{pairs[0]}-팀.json").read_text(encoding="utf-8")).get("목록커밋", "?")
    print(f"\n── 사전 등록 {len(pairs)}건 — 목록 커밋 {commit} · 순환 없음 ──")
    print(f"{'질문':14} {'근거율':>11} {'서고수':>7} {'핵심문서':>11}  필수 서고 누락 (팀 / 혼자)")
    tally = {"근거율": [0, 0], "서고수": [0, 0], "핵심문서": [0, 0]}
    for qid in pairs:
        solo_f = folder / f"{qid}-혼자.json"
        if not solo_f.exists():
            continue
        q = by_id[qid]
        runs = [json.loads((folder / f"{qid}-{w}.json").read_text(encoding="utf-8")) for w in ("팀", "혼자")]
        (t, s) = (measure(r["report"], q, corpus) | {"근거율": r["metrics"]["근거율"]} for r in runs)
        for key, a, b in (("근거율", t["근거율"], s["근거율"]), ("서고수", t["인용서고수"], s["인용서고수"]),
                          ("핵심문서", t["핵심문서도달"], s["핵심문서도달"])):
            if a > b: tally[key][0] += 1
            elif b > a: tally[key][1] += 1
        miss = f"{','.join(t['필수서고누락']) or '-'} / {','.join(s['필수서고누락']) or '-'}"
        print(f"{qid:14} {t['근거율']:>5.2f}/{s['근거율']:<5.2f} {t['인용서고수']:>3}/{s['인용서고수']:<3} "
              f"{t['핵심문서도달']:>5.2f}/{s['핵심문서도달']:<5.2f}  {miss}")
    print("팀 승 / 혼자 승 (동점 제외): " + " · ".join(f"{k} {v[0]}/{v[1]}" for k, v in tally.items()))


if __name__ == "__main__":
    raise SystemExit(main())
