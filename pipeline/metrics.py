"""계기판 — 정답표도 판정 모델도 쓰지 않는다 (계획서 6장).

만들어진 글(drafts)과 실제로 읽은 문서(reads), 그 둘만 본다.
그래서 코퍼스를 갈아 끼워도 그대로 돈다.
"""
from __future__ import annotations

import re
from collections import Counter

from .state import Draft, Read

# 줄바꿈·« 는 인용 안에 못 들어온다 — 닫는 표시가 깨진 인용(«…" )이 다음 절의 «…» 까지
# 한 덩어리로 삼키던 것을 막는다 (대조군-다갈래 보고서에서 2건 실측. 원고에는 없어 지표는 그대로였다)
CITE = re.compile(r"«([^»«\n]{1,120})»")
# 오귀속 검사용 — 문장 속 영문 고유명사와 연도. 한국어 표기만 있으면 못 잡는다 (한계)
PROPER = re.compile(r"[A-Z][a-zA-Z]{3,}")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
# 어느 문서에나 나오는 말은 대조에서 뺀다
COMMON = {"MBTI", "Myers", "Briggs", "Type", "Indicator", "Jung", "Psychology", "Personality"}
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

# 그물 — 하나라도 걸리면 자동 탈락 (6.1절)
NET_KEYS = ("허위인용", "인용0곳절수")
SKEW_LIMIT = 0.50


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text or "") if s.strip()]


def citations(text: str) -> list[str]:
    return CITE.findall(text or "")


def _ratio(num: float, den: float) -> float:
    return round(num / den, 4) if den else 0.0


def misattributed(drafts: dict[int, Draft], corpus=None) -> list[dict]:
    """붙은 근거가 실제 그 문서의 내용인가. 인용의 존재가 아니라 인용의 타당성을 본다.

    판정 모델을 쓰지 않는다. 문장 속 영문 고유명사·연도가 인용된 문서 원문에
    글자 그대로 있는지 대조할 뿐이다. 한국어 표기만 있는 이름은 놓친다.
    """
    if corpus is None:
        return []
    out = []
    for i in sorted(drafts):
        for sent in sentences(drafts[i]["text"]):
            cites = citations(sent)
            if not cites:
                continue
            toks = (set(PROPER.findall(sent)) | set(YEAR.findall(sent))) - COMMON
            toks -= {w for cite in cites for w in re.findall(r"[A-Za-z]{4,}", cite)}
            if not toks:
                continue
            src = " ".join(corpus.text(d) for d in cites if d in corpus.docs)
            missing = sorted(t for t in toks if t not in src)
            if missing:
                out.append({"절": drafts[i]["title"], "문장": sent[:120],
                            "인용": cites, "원문에없음": missing})
    return out


def compute(
    drafts: dict[int, Draft],
    reads: list[Read],
    report: str,
    coord_chars: int,
    corpus=None,
) -> dict:
    drafts = drafts or {}
    reads = reads or []
    ordered = [drafts[i] for i in sorted(drafts)]

    # 근거율 — 문장 중 «문서명»이 붙은 비율
    all_sents = [s for d in ordered for s in sentences(d["text"])]
    cited_sents = [s for s in all_sents if CITE.search(s)]

    # 인용 0곳 절 수 — 전체 평균에 묻히는 절 단위 구멍을 잡는 그물
    empty_sections = [d["title"] for d in ordered if not citations(d["text"])]

    # 허위 인용 — 그 절이 읽지 않은 문서를 인용했나
    read_by_section: dict[int, set[str]] = {}
    for r in reads:
        read_by_section.setdefault(r["section"], set()).add(r["doc"])
    fabricated = sorted({
        doc
        for d in ordered
        for doc in citations(d["text"])
        if doc not in read_by_section.get(d["section"], set())
    })

    cited_all = Counter(doc for d in ordered for doc in citations(d["text"]))
    read_all = {r["doc"] for r in reads}

    # 읽고 안 쓴 문서 — 배정 품질
    unused = sorted(read_all - set(cited_all))

    # 최다 문서 편중 — 인용이 한 문서에 몰린 비율
    skew = _ratio(max(cited_all.values()), sum(cited_all.values())) if cited_all else 0.0

    # 중복률 — 같은 문서를 두 절 이상이 읽음
    doc_sections = Counter()
    for doc in read_all:
        doc_sections[doc] = sum(1 for s in read_by_section.values() if doc in s)
    overlap = _ratio(sum(1 for n in doc_sections.values() if n >= 2), len(read_all))

    # 격리율 — 코디네이터가 본 글자 ÷ 팀 전체. 한 자릿수여야 정상
    team_chars = sum(r["source_chars"] for r in reads)
    isolation = _ratio(coord_chars, team_chars + coord_chars)

    mis = misattributed(drafts, corpus)

    # 인용 서고 — 근거를 몇 개 서고에서 가져왔나. 정답표 없이 코퍼스 분류만 본다.
    # 근거율은 한 문서만 되풀이 인용해도 오른다 — 어디서 가져왔는지는 이것으로 본다.
    # 서고는 코퍼스가 있으면 코퍼스에서, 없으면 읽은 기록에 적힌 서고에서 찾는다.
    shelf_of = {r["doc"]: r.get("library") for r in reads}
    if corpus is not None:
        shelf_of.update({doc: corpus.group(doc) for doc in cited_all})
    shelves: Counter = Counter()
    for doc, n in cited_all.items():
        shelves[shelf_of.get(doc) or "미분류"] += n

    return {
        "근거율": _ratio(len(cited_sents), len(all_sents)),
        "출처불일치": len(mis),
        "출처불일치문장": mis,
        "인용0곳절수": len(empty_sections),
        "인용0곳절": empty_sections,
        "허위인용": len(fabricated),
        "허위인용문서": fabricated,
        "읽고안쓴문서": len(unused),
        "최다문서편중": skew,
        "중복률": overlap,
        "격리율": isolation,
        "인용서고수": len([s for s in shelves if s != "미분류"]),
        "서고분포": dict(shelves.most_common()),
        "문장수": len(all_sents),
        "인용수": sum(cited_all.values()),
        "읽은문서수": len(read_all),
        "보고서자수": len(report or ""),
    }


def net_verdict(m: dict) -> dict:
    """그물 판정 — 통과한 것만 사람이 읽고 고른다 (16강)."""
    fails = []
    if m.get("허위인용", 0) > 0:
        fails.append("허위 인용")
    if m.get("인용0곳절수", 0) > 0:
        fails.append("인용 0곳 절")
    if m.get("최다문서편중", 0) > SKEW_LIMIT:
        fails.append("편중 50% 초과")
    return {"통과": not fails, "사유": fails}
