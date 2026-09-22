"""6노드 — 1단계에서는 전부 빈 껍데기다.

각 노드는 지금 '자리와 계약'만 갖는다. 들어오는 상태, 나가는 상태, 쏘는 이벤트.
2단계에서 몸통(LLM 호출)을 채운다. 채울 자리는 TODO(2단계)로 표시했다.
"""
from __future__ import annotations

from . import events, llm, metrics, prompts
from .corpus import Corpus
from .state import Draft, Read, ResearcherTask, Section, State

ROLES = ["큰그림 담당", "시간순 담당", "인물 담당", "비교 담당"]


# ── ① 기획 ────────────────────────────────────────────────
def _resolve(title: str, corpus: Corpus) -> str | None:
    """모델이 적은 제목을 실제 문서에 맞춘다. 못 맞추면 None — 환각으로 본다."""
    if not title:
        return None
    t = title.strip().strip("«»\"'")
    if t in corpus.docs:
        return t
    low = {k.lower(): k for k in corpus.titles}
    return low.get(t.lower())


def plan(state: State, corpus: Corpus) -> State:
    """목차·역할·시작 문서를 정한다. 제목만이 아니라 문서 카드를 보고 정한다."""
    s = state["settings"]
    cards = corpus.cards()                      # 52장. 고립 문서에 닿는 유일한 통로
    prompt = prompts.plan_user(state["question"], s["sections"], cards, role=s["role"])
    data = llm.ask_json(prompt, system=prompts.PLAN_SYS)
    coord_chars = len(prompt)                   # 코디네이터가 본 글자 (격리율 분자)

    rows = data.get("목차") or data.get("sections") or []
    used: set[str] = set()
    fixes: list[dict] = []
    picks: list[Section] = []

    for i, row in enumerate(rows[: s["sections"]]):
        raw = str(row.get("시작문서", ""))
        doc = _resolve(raw, corpus)
        if doc is None or doc in used:
            # 환각이거나 겹친다 → 아직 안 쓴 문서 중 가장 긴 것으로 메운다
            pool = [t for t in corpus.titles if t not in used] or corpus.titles
            doc = max(pool, key=lambda t: len(corpus.text(t)))
            fixes.append({"모델": raw, "교정": doc,
                          "사유": "겹침" if _resolve(raw, corpus) else "코퍼스에 없음"})
        used.add(doc)
        picks.append({
            "idx": i,
            "title": str(row.get("절", f"{i + 1}절")).strip(),
            "role": str(row.get("역할", "담당")).strip() if s["role"] else "담당",
            "start_doc": doc,
            "library": corpus.group(doc),
        })

    if not s["assign"]:
        # 배정 끔 — 코디네이터가 시작점을 주지 않는다. 목록 앞에서부터 기계적으로 집는다
        for i, p in enumerate(picks):
            p["start_doc"] = corpus.titles[i % len(corpus.titles)]
            p["library"] = corpus.group(p["start_doc"])

    events.emit(
        "plan.done",
        목차=[{"절": p["title"], "역할": p["role"], "시작문서": p["start_doc"], "서고": p["library"]}
             for p in picks],
        교정=fixes,   # 모델이 지어낸 문서명을 몇 번 고쳤나 — 카드 품질의 계기
    )
    return {"sections": picks, "coord_chars": coord_chars, "round": 0,
            "drafts": {}, "reads": [], "gaps": []}


# ── ② 배치 ────────────────────────────────────────────────
def dispatch(state: State) -> State:
    """이번 바퀴에 누구를 내보낼지 정한다. 1바퀴는 전원, 2바퀴부터는 빈 절만."""
    rnd = state.get("round", 0) + 1
    gaps = state.get("gaps") or []
    assigned = gaps if rnd > 1 else [s["idx"] for s in state["sections"]]

    events.emit("dispatch", 바퀴=rnd, 인원=len(assigned), 배치=assigned)
    return {"round": rnd, "assigned": assigned}


def fan_out(state: State):
    """Send 팬아웃 — 조사관 n명이 동시에 흩어지는 지점."""
    from langgraph.types import Send

    sections = {s["idx"]: s for s in state["sections"]}
    drafts = state.get("drafts") or {}
    read_done: dict[int, list[str]] = {}
    prev_memos: dict[int, list[list[str]]] = {}
    for r in state.get("reads") or []:
        read_done.setdefault(r["section"], []).append(r["doc"])
        if r.get("memo"):
            prev_memos.setdefault(r["section"], []).append([r["doc"], r["memo"]])
    zone = state["settings"]["zone"]
    sends = []
    for idx in state.get("assigned", []):
        sec = sections[idx]
        prev = drafts.get(idx)
        avoid = [o["start_doc"] for j, o in sections.items() if j != idx] if zone else []
        task: ResearcherTask = {
            "question": state["question"],
            "settings": state["settings"],
            "section": sec,
            "avoid": avoid,
            "round": state["round"],
            "prev": prev["text"] if prev else "",
            "missing": prev["missing"] if prev else "",
            "read_done": read_done.get(idx, []),
            "prev_memos": prev_memos.get(idx, []),
        }
        sends.append(Send("researcher", task))
    return sends


# ── ③ 조사관 (병렬) ───────────────────────────────────────
def researcher(task: ResearcherTask, corpus: Corpus) -> State:
    """배정 문서에서 출발해 링크를 타며 읽고, 요약이 아니라 '절 원고'를 써 온다."""
    sec: Section = task["section"]
    s = task["settings"]
    events.emit(
        "researcher.start",
        절=sec["title"], 역할=sec["role"], 시작문서=sec["start_doc"], 피하기=task["avoid"],
    )

    avoid = set(task["avoid"])
    seen: set[str] = set(task.get("read_done") or [])   # 지난 바퀴에 이미 읽은 문서
    reads: list[Read] = []
    # 지난 바퀴에 읽은 메모를 물려받는다. 그래야 그 문서를 계속 인용할 자격이 있다.
    memos: list[tuple[str, str]] = [tuple(m) for m in (task.get("prev_memos") or [])]

    # 프런티어 — 재위임 바퀴면 시작 문서는 이미 읽었으므로 그 이웃부터 이어 간다
    frontier: list[str] = []
    if sec["start_doc"] not in seen:
        frontier.append(sec["start_doc"])
    else:
        for d in task.get("read_done") or []:
            frontier += corpus.neighbors(d)
        if not frontier:   # 링크가 마른 경우 같은 서고에서 고른다
            frontier = [t for t in corpus.titles if corpus.group(t) == sec["library"]]
    frontier = [t for t in dict.fromkeys(frontier) if t not in seen and t not in avoid]

    for step in range(s["budget"]):
        doc = next((t for t in frontier if t not in seen), None)
        if not doc:
            break
        frontier.remove(doc)
        seen.add(doc)
        body = corpus.text(doc)
        neighbors = [t for t in corpus.neighbors(doc) if t not in seen and t not in avoid]

        out = llm.ask_json(prompts.read_one_user(
            task["question"], sec["title"], sec["role"], doc, corpus.group(doc),
            body[: llm.CONTEXT_CHARS], corpus.cards(neighbors[:12]),
            s["budget"] - step - 1,
        ), system=prompts.READ_SYS)

        relevant = bool(out.get("관련"))
        memo = str(out.get("메모") or "").strip() if relevant else ""
        if memo:
            memos.append((doc, memo))

        events.emit(
            "researcher.read", 절=sec["title"], 문서=doc, 서고=corpus.group(doc),
            원문자수=len(body), 메모자수=len(memo), 관련=relevant,
        )
        reads.append({"section": sec["idx"], "doc": doc, "library": corpus.group(doc),
                      "source_chars": len(body), "memo_chars": len(memo),
                      "memo": memo, "relevant": relevant})

        # 읽은 내용이 다음 선택을 만든다 (9강). 모델이 고른 것을 맨 앞에 둔다.
        frontier += [t for t in neighbors if t not in frontier]
        pick = _resolve(str(out.get("다음") or ""), corpus)
        if pick and pick not in seen and pick not in avoid:
            frontier = [pick] + [t for t in frontier if t != pick]

    prev = task.get("prev", "")
    fresh = len(memos) - len(task.get("prev_memos") or [])
    if memos and (fresh or not prev):
        w = llm.ask_json(prompts.write_user(
            task["question"], sec["title"], sec["role"], memos,
            prev=prev, missing=task.get("missing", ""),
        ), system=prompts.WRITE_SYS)
        text = str(w.get("원고") or "").strip()
        enough = bool(w.get("충분"))
        missing = str(w.get("부족") or "").strip()

        # 규칙을 어겼으면 딱 한 번 다시 시킨다. ①인용 0곳 ②읽지 않은 문서 인용
        allowed = {t for t, _ in memos}
        fake = sorted({d for d in metrics.citations(text) if d not in allowed})
        if text and (not metrics.citations(text) or fake):
            w = llm.ask_json(prompts.write_user(
                task["question"], sec["title"], sec["role"], memos,
                prev=prev, missing=task.get("missing", ""),
                strict=not metrics.citations(text), fabricated=fake,
            ), system=prompts.WRITE_SYS)
            retry = str(w.get("원고") or "").strip()
            retry_fake = [d for d in metrics.citations(retry) if d not in allowed]
            # 고쳐 온 것이 더 나을 때만 받는다 (인용이 있고, 허위가 줄었을 때)
            if metrics.citations(retry) and len(retry_fake) < max(len(fake), 1):
                text = retry
                enough = bool(w.get("충분"))
                missing = str(w.get("부족") or "").strip()
            events.emit("researcher.fix", 절=sec["title"],
                        허위=fake, 남은허위=retry_fake, 채택=text == retry)
    elif prev:
        # 재위임 바퀴에서 새로 읽을 것이 없었다. 직전 원고를 지킨다 — 되돌리면 손해다.
        text, enough = prev, False
        missing = "재위임했으나 새로 읽을 문서를 찾지 못했다 (직전 원고 유지)."
    else:
        text, enough = "", False
        missing = "읽은 문서가 모두 이 절과 관련이 없었다."

    draft: Draft = {
        "section": sec["idx"], "title": sec["title"], "text": text,
        "citations": metrics.citations(text), "enough": enough, "missing": missing,
    }
    events.emit(
        "researcher.done",
        절=sec["title"], 자수=len(text), 인용=len(draft["citations"]),
        충분=enough, 부족=missing,
    )
    return {"drafts": {sec["idx"]: draft}, "reads": reads}


# ── ④ 점검 ────────────────────────────────────────────────
def review(state: State) -> State:
    """빈 칸을 찾는다. 조사관의 자기신고 + 인용 0곳을 함께 본다."""
    drafts = state.get("drafts") or {}
    s = state["settings"]
    gaps = [
        i for i in sorted(drafts)
        if not metrics.citations(drafts[i]["text"]) or not drafts[i]["enough"]
    ]
    exhausted = state["round"] >= s["max_rounds"]
    stop = (not gaps) or exhausted or (not s["redelegate"])
    reason = None if not stop else ("빈 칸 없음" if not gaps
                                    else "재위임 끔" if not s["redelegate"]
                                    else f"{s['max_rounds']}바퀴 소진")

    events.emit(
        "review", 절수=len(drafts),
        빈칸=[drafts[i]["title"] for i in gaps], 종료=reason,
    )
    return {"gaps": [] if stop else gaps}


def after_review(state: State) -> str:
    return "done" if not state.get("gaps") else "more"


# ── ⑤ 종합 ────────────────────────────────────────────────
PEEK_CHARS = 300  # 코디네이터가 절에서 엿보는 분량. 격리를 지키려고 앞머리만 본다


def synthesize(state: State) -> State:
    """절을 다시 쓰지 않는다. 문체를 포기하고 인용을 지킨다 (12강 결정)."""
    drafts = state.get("drafts") or {}
    order = sorted(drafts)
    peeks = [(drafts[i]["title"], drafts[i]["text"][:PEEK_CHARS]) for i in order
             if drafts[i]["text"]]

    head, seen = "", 0
    if peeks:
        prompt = prompts.head_user(state["question"], peeks)
        seen = len(prompt)
        head = str(llm.ask_json(prompt, system=prompts.HEAD_SYS).get("머리말") or "").strip()

    parts = [f"## {drafts[i]['title']}\n\n{drafts[i]['text']}".rstrip() for i in order]
    report = f"# {state['question']}\n\n{head}\n\n" + "\n\n".join(parts) + "\n"

    events.emit("synthesize", 절수=len(parts), 보고서자수=len(report), 머리말자수=len(head))
    return {"report": report, "coord_chars": seen}


# ── ⑥ 평가 ────────────────────────────────────────────────
def evaluate(state: State, corpus: Corpus) -> State:
    """정답표도 판정 모델도 쓰지 않는다. 쓴 글과 읽은 문서만 본다."""
    m = metrics.compute(
        drafts=state.get("drafts") or {},
        reads=state.get("reads") or [],
        report=state.get("report", ""),
        coord_chars=state.get("coord_chars", 0),
        corpus=corpus,
    )
    m["그물"] = metrics.net_verdict(m)
    events.emit("evaluate", metrics=m)
    events.emit("run.end")
    return {"metrics": m}
