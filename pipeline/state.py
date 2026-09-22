"""그래프 상태 — 병렬 조사관이 동시에 쓰므로 리듀서가 핵심이다."""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class Settings(TypedDict):
    """절제 실험 스위치 (계획서 7.2). 끄면 무엇이 무너지는지 보려는 것."""
    sections: int      # 절 수
    budget: int        # 절당 읽을 문서 수
    assign: bool       # 배정 — 시작 문서를 코디네이터가 정해 준다
    zone: bool         # 구역 — 남의 시작 문서를 피한다
    role: bool         # 역할 — 조사관마다 다른 성격을 준다
    redelegate: bool   # 재위임 — 빈 절을 되돌려 보낸다
    max_rounds: int


DEFAULT_SETTINGS: Settings = {
    "sections": 4,
    "budget": 3,
    "assign": True,
    "zone": True,
    "role": True,
    "redelegate": True,
    "max_rounds": 2,
}


class Section(TypedDict):
    idx: int
    title: str       # 절 제목
    role: str        # 역할
    start_doc: str   # 시작 문서
    library: str     # 서고


class Read(TypedDict):
    section: int
    doc: str
    library: str
    source_chars: int  # 원문 자수 — 화면의 '두꺼운 책'
    memo_chars: int    # 메모 자수 — 화면의 '얇은 쪽지'
    memo: str          # 메모 본문 — 재위임 바퀴에 물려준다 (이벤트에는 싣지 않는다)
    relevant: bool


class Draft(TypedDict):
    section: int
    title: str
    text: str
    citations: list[str]  # 본문에 «문서명»으로 등장한 문서
    enough: bool          # 조사관 자기신고
    missing: str          # 무엇이 부족한가 (자기신고)


def merge_drafts(left: dict[int, Draft], right: dict[int, Draft]) -> dict[int, Draft]:
    """절 번호로 덮어쓴다. 재위임 바퀴에서 같은 절이 다시 오면 새 원고가 이긴다."""
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class State(TypedDict, total=False):
    question: str
    settings: Settings
    sections: list[Section]
    drafts: Annotated[dict[int, Draft], merge_drafts]
    reads: Annotated[list[Read], operator.add]   # 모든 바퀴 누적
    coord_chars: Annotated[int, operator.add]    # 코디네이터가 본 글자 (격리율 분자)
    round: int
    assigned: list[int]   # 이번 바퀴에 파견할 절 번호
    gaps: list[int]       # 점검이 되돌려 보낸 절 번호
    report: str
    metrics: dict


class ResearcherTask(TypedDict):
    """Send로 조사관에게 건네는 짐. 조사관은 이것 말고 아무것도 못 본다."""
    question: str
    settings: Settings
    section: Section
    avoid: list[str]
    round: int
    prev: str  # 재위임일 때 직전 원고 (없으면 "")
    missing: str
    read_done: list[str]         # 지난 바퀴에 이미 읽은 문서 — 두 번 읽지 않는다
    prev_memos: list[list[str]]  # 지난 바퀴의 메모 [[문서, 메모], …] — 인용 자격을 잃지 않게
