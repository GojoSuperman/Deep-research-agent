"""혼자 하는 대조군 — 팀과 붙여 보려고 만든 것 (과제 4단계 「결과물을 직접 비교하기」).

공정성이 이 실험의 전부다. 팀에게만 유리한 조건을 주면 이긴 것이 아니라
상대를 묶어 둔 것이다. 그래서 다음 넷을 **코드로** 같게 맞춘다.

  같은 자료   data/corpus.json 52건 그대로
  같은 모델   llm.model_name() — 팀이 쓰는 바로 그 모델
  같은 도구   corpus.cards() · corpus.neighbors() — 팀의 조사관이 쓰는 것과 같은 함수
  같은 예산   절수 × 절예산 = 12건. 팀이 읽는 총 문서 수와 같다

다른 것은 하나뿐이다: **분업이 없다.** 한 사람이 12건을 다 읽고, 읽은 것이 전부
한 창에 쌓인 채로 보고서 전체를 쓴다. 이것이 측정하려는 차이다.

인용 규칙(prompts.CITE_RULES)은 **같은 문자열**을 쓴다. 따로 쓰면
"프롬프트가 달라서 진 것"이라는 반론이 성립한다.

    python -m pipeline.baseline                      # 기본 질문 한 편
    python -m pipeline.baseline -q "질문" --save runs/대조군.json
"""
from __future__ import annotations

import argparse
import json
import time

from . import llm, metrics, prompts
from .corpus import Corpus, load
from .nodes import _resolve
from .state import DEFAULT_SETTINGS

QUESTION = "MBTI 궁합론은 어떤 근거로 제시되며, 심리학계는 이를 어떻게 평가하는가?"


def run(question: str, *, sections: int, budget: int, reads_budget: int | None = None,
        corpus: Corpus | None = None, console: bool = True) -> dict:
    corpus = corpus or load()
    llm.reset_usage()
    t0 = time.time()
    seen_chars = 0          # 혼자 하는 쪽이 자기 창에 넣은 글자 — 격리율의 분자

    # ── ① 목차 — 팀의 기획 노드와 같은 도구(문서 카드 52장)를 준다
    cards = corpus.cards()
    prompt = prompts.plan_user(question, sections, cards, role=False)
    seen_chars += len(prompt)
    data = llm.ask_json(prompt, system=prompts.PLAN_SYS)
    plan = data.get("목차") or []
    outline = [str(p.get("절") or f"{i + 1}절") for i, p in enumerate(plan)][:sections]
    while len(outline) < sections:
        outline.append(f"{len(outline) + 1}절")
    start = next((d for d in (_resolve(str(p.get("시작문서") or ""), corpus) for p in plan) if d), None)
    start = start or corpus.titles[0]
    if console:
        print(f"  목차 {outline}")
        print(f"  시작 문서 «{start}»")

    # ── ② 읽기 — 예산 12건. 팀의 조사관과 같은 탐색 규칙
    # 팀은 재위임 바퀴 때문에 절수×절예산보다 **더 많이** 읽는다.
    # 그 실측치를 --reads 로 넘겨 대조군 예산을 맞춘다. 적게 주면 실험이 아니다.
    budget_total = reads_budget or sections * budget
    frontier, seen, memos, reads = [start], set(), [], []
    for step in range(budget_total):
        doc = next((t for t in frontier if t not in seen), None)
        if not doc:
            break
        frontier.remove(doc)
        seen.add(doc)
        body = corpus.text(doc)
        neighbors = [t for t in corpus.neighbors(doc) if t not in seen]
        p = prompts.solo_read_user(question, outline, doc, corpus.group(doc),
                                   body[: llm.CONTEXT_CHARS], corpus.cards(neighbors[:12]),
                                   budget_total - step - 1)
        seen_chars += len(p)            # 혼자이므로 원문이 그대로 자기 창에 들어간다
        # 한 건이 깨져도 한 편을 통째로 잃지 않는다. 모델이 이따금 JSON 대신 다른 모양을 낸다.
        try:
            out = llm.ask_json(p, system=prompts.SOLO_READ_SYS, retries=2)
        except (ValueError, KeyError) as e:
            if console:
                print(f"  [{step + 1}/{budget_total}] «{doc}» 읽기 실패 — 건너뛴다 ({type(e).__name__})")
            reads.append({"doc": doc, "library": corpus.group(doc), "source_chars": len(body),
                          "memo_chars": 0, "relevant": False, "실패": True})
            continue
        relevant = bool(out.get("관련"))
        memo = str(out.get("메모") or "").strip() if relevant else ""
        if memo:
            memos.append((doc, memo))
        reads.append({"doc": doc, "library": corpus.group(doc), "source_chars": len(body),
                      "memo_chars": len(memo), "relevant": relevant})
        if console:
            print(f"  [{step + 1}/{budget_total}] «{doc}» {len(body):,}자 → 메모 {len(memo)}자"
                  f"{'' if relevant else '  (관련 없음)'}")
        frontier += [t for t in neighbors if t not in frontier]
        pick = _resolve(str(out.get("다음") or ""), corpus)
        if pick and pick not in seen:
            frontier = [pick] + [t for t in frontier if t != pick]

    used = len(reads)

    # ── ③ 쓰기 — 12건 메모가 전부 한 창에 쌓인 채로 보고서 전체를 쓴다
    w = llm.ask_json(prompts.solo_write_user(question, outline, memos),
                     system=prompts.SOLO_WRITE_SYS, retries=2)
    parts = w.get("절들") or []
    drafts = {
        i: {"section": i, "title": str(p.get("제목") or outline[i] if i < len(outline) else f"{i+1}절"),
            "text": str(p.get("원고") or "").strip(), "citations": [],
            "enough": True, "missing": ""}
        for i, p in enumerate(parts)
    }
    report = "\n\n".join(f"## {d['title']}\n\n{d['text']}" for d in drafts.values())

    # ── ④ 지표 — 팀과 **같은 metrics.compute** 로 잰다
    # 혼자는 읽은 12건을 어느 절에나 인용할 자격이 있다. 그래서 절마다 같은 목록을 준다
    # (팀은 자기가 읽은 것만 인용할 수 있다 — 이 차이는 대조군에 유리한 쪽이다).
    read_rows = [{**r, "section": i, "memo": "", "source_chars": 0}
                 for i in drafts for r in reads]
    m = metrics.compute(drafts, read_rows, report, seen_chars, corpus=corpus)
    m["격리율"] = 1.0          # 혼자가 전부 봤다 — 정의상 100%
    m["중복률"] = None         # 나눌 사람이 없으니 겹칠 일이 없다 (해당 없음)
    m["읽은문서수"] = len({r["doc"] for r in reads})
    m["그물"] = metrics.net_verdict(m)

    u = llm.usage()
    return {
        "종류": "대조군(혼자)", "question": question, "목차": outline, "시작문서": start,
        "예산": budget_total, "실제로읽은건수": used,
        "reads": reads, "drafts": list(drafts.values()), "report": report,
        "metrics": m, "usage": u,
        "cost_krw": round((u["prompt"] / 1e6 * 0.15 + u["completion"] / 1e6 * 0.6) * 1400),
        "초": round(time.time() - t0, 1),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="혼자 하는 대조군 한 편")
    p.add_argument("-q", "--question", default=QUESTION)
    p.add_argument("--sections", type=int, default=DEFAULT_SETTINGS["sections"])
    p.add_argument("--budget", type=int, default=DEFAULT_SETTINGS["budget"])
    p.add_argument("--reads", type=int,
                   help="총 읽기 예산을 직접 지정한다 (팀의 실측 읽기 횟수에 맞출 때)")
    p.add_argument("--save", help="결과를 저장할 경로 (runs/*.json)")
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args()

    out = run(a.question, sections=a.sections, budget=a.budget,
              reads_budget=a.reads, console=not a.quiet)
    m = out["metrics"]

    print("\n── 대조군(혼자) 계기판 ─────────────────")
    print(f"  예산 {out['예산']}건 중 실제로 읽음  {out['실제로읽은건수']}건"
          f"{'  ⚠ 예산을 다 쓰지 않았다' if out['실제로읽은건수'] < out['예산'] else '  ✅ 예산 소진'}")
    for k in ("근거율", "인용0곳절수", "허위인용", "출처불일치", "최다문서편중",
              "중복률", "격리율", "보고서자수", "읽은문서수"):
        v = m.get(k)
        print(f"  {k:<12} {'해당 없음' if v is None else v}")
    net = m["그물"]
    print(f"  그물         {'통과' if net['통과'] else '탈락 — ' + ' · '.join(net['사유'])}")
    print(f"  {out['초']}초 · 호출 {out['usage']['calls']}회 · ₩{out['cost_krw']}")

    if a.save:
        with open(a.save, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(f"\n  저장: {a.save}")


if __name__ == "__main__":
    main()
