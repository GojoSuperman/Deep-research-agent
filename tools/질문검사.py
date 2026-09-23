"""질문 세트가 코퍼스·기록과 어긋나지 않는지 검사한다.

모델만 문서 제목을 지어내는 것이 아니다. 사람도 질문을 적다가 지어낸다.
    .venv/bin/python tools/질문검사.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.corpus import load  # noqa: E402

TYPES = {"단일", "다갈래", "추적"}


def main() -> int:
    c = load()
    titles, groups = set(c.titles), set(c.by_group())
    qs = json.loads(Path("data/questions.json").read_text(encoding="utf-8"))["질문"]
    bad = 0

    for q in qs:
        why = []
        why += [f"없는 문서 {d!r}" for d in q["핵심 문서"] if d not in titles]
        why += [f"없는 서고 {g!r}" for g in q["닿아야 할 서고"] if g not in groups]
        if q["유형"] not in TYPES:
            why.append(f"모르는 유형 {q['유형']!r}")
        if not q["왜 나눌 만한가"].strip():
            why.append("'왜 나눌 만한가' 가 비었다")
        if q.get("녹화") and not q.get("녹화이름"):
            why.append("녹화 대상인데 녹화이름이 없다")

        # 적어 둔 실측값이 실제 기록과 같은가 — 문서만 고치고 숫자를 안 고치는 일을 막는다
        m = q.get("실측")
        if m:
            for path, key in zip(m["기록"], ("팀 근거율", "혼자 근거율")):
                p = Path(path)
                if not p.exists():
                    why.append(f"기록 없음 {path}")
                    continue
                got = json.loads(p.read_text(encoding="utf-8"))["metrics"]["근거율"]
                if abs(got - m[key]) > 1e-4:
                    why.append(f"{key} 적힌 값 {m[key]} ≠ 기록 {got:.4f} ({path})")

        if why:
            bad += 1
            print(f"❌ {q['id']}")
            for w in why:
                print(f"     {w}")

    kinds: dict[str, int] = {}
    for q in qs:
        kinds[q["유형"]] = kinds.get(q["유형"], 0) + 1
    print(f"\n질문 {len(qs)}건 · 유형 {kinds} · 녹화 {sum(1 for q in qs if q.get('녹화'))}편")
    if len(qs) < 8:
        print("❌ 과제 요구는 8건 이상이다")
        bad += 1
    if not any(q["유형"] == "단일" for q in qs):
        print("❌ 한 건으로 답이 나오는 질문이 하나는 있어야 한다")
        bad += 1
    print("문제 없음 ✅" if not bad else f"문제 {bad}건 ❌")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
