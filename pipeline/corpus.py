"""코퍼스 적재 — data/corpus.json 하나만 본다."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT / "data" / "corpus.json"

CARD_CHARS = 250  # 4강 결정: 제목만이 아니라 제목+앞 250자 카드를 보여준다


@dataclass
class Corpus:
    docs: dict[str, str]
    links: dict[str, list[str]]
    groups: dict[str, str]
    meta: dict

    @cached_property
    def titles(self) -> list[str]:
        return sorted(self.docs)

    def text(self, title: str) -> str:
        return self.docs.get(title, "")

    def group(self, title: str) -> str:
        return self.groups.get(title, "미분류")

    def neighbors(self, title: str) -> list[str]:
        return [t for t in self.links.get(title, []) if t in self.docs]

    def card(self, title: str) -> str:
        """제목 + 앞 250자. 링크로 못 닿는 문서에 닿는 유일한 통로."""
        body = " ".join(self.text(title).split())[:CARD_CHARS]
        return f"«{title}» ({self.group(title)}) — {body}"

    def cards(self, titles: list[str] | None = None) -> list[str]:
        return [self.card(t) for t in (titles or self.titles)]

    def by_group(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for title in self.titles:
            out.setdefault(self.group(title), []).append(title)
        return out

    @property
    def orphans(self) -> list[str]:
        """어떤 문서도 링크하지 않는 문서 — 배정으로만 닿는다."""
        linked = {t for targets in self.links.values() for t in targets}
        return [t for t in self.titles if t not in linked]


def load(path: Path = CORPUS_PATH) -> Corpus:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Corpus(
        docs=raw["docs"],
        links=raw.get("links", {}),
        groups=raw.get("groups", {}),
        meta=raw.get("meta", {}),
    )
