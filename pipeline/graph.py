"""6노드 배선 — 팬아웃(Send) 하나, 재위임 루프 하나."""
from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from . import events, llm, nodes
from .corpus import Corpus, load
from .state import DEFAULT_SETTINGS, Settings, State


def build(corpus: Corpus):
    g = StateGraph(State)
    g.add_node("plan", partial(nodes.plan, corpus=corpus))
    g.add_node("dispatch", nodes.dispatch)
    g.add_node("researcher", partial(nodes.researcher, corpus=corpus))
    g.add_node("review", nodes.review)
    g.add_node("synthesize", nodes.synthesize)
    g.add_node("evaluate", partial(nodes.evaluate, corpus=corpus))

    g.add_edge(START, "plan")
    g.add_edge("plan", "dispatch")
    g.add_conditional_edges("dispatch", nodes.fan_out, ["researcher"])  # 팬아웃
    g.add_edge("researcher", "review")
    g.add_conditional_edges("review", nodes.after_review,
                            {"more": "dispatch", "done": "synthesize"})  # 재위임 루프
    g.add_edge("synthesize", "evaluate")
    g.add_edge("evaluate", END)
    return g.compile()


def run(question: str, settings: Settings | None = None, *, console: bool = False,
        corpus: Corpus | None = None) -> dict:
    corpus = corpus or load()
    cfg: Settings = {**DEFAULT_SETTINGS, **(settings or {})}

    events.reset(console=console)
    llm.reset_usage()
    events.emit("run.start", question=question, 설정={
        "절수": cfg["sections"], "절예산": cfg["budget"], "배정": cfg["assign"],
        "구역": cfg["zone"], "역할": cfg["role"], "재위임": cfg["redelegate"],
    })

    app = build(corpus)
    # 재위임 루프가 있으므로 상한을 넉넉히 둔다 (바퀴당 노드 수 × 최대 바퀴 + 여유)
    limit = 10 + (cfg["sections"] + 3) * cfg["max_rounds"]
    final = app.invoke({"question": question, "settings": cfg},
                       {"recursion_limit": limit})
    return {"state": final, "events": events.dump(), "usage": llm.usage()}
