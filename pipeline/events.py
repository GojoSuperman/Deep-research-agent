"""이벤트 스트림 — 프런트/백 사이의 유일한 계약 (계획서 4장).

조사관 노드가 병렬로 돌기 때문에 emit()은 락으로 보호한다.
백엔드는 '무슨 일이 있었나'만 싣는다. '어느 서고로 걸어가나'는 프런트 몫.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

PROTOCOL_VERSION = 1

_lock = threading.Lock()
_events: list[dict] = []
_console = False
_t0 = 0.0
_sink = None   # 라이브 모드(6단계)가 꽂는 구독자. 없으면 기록만 한다.


def reset(console: bool = False) -> None:
    global _console, _t0
    with _lock:
        _events.clear()
        _console = console
        _t0 = time.time()


def subscribe(fn) -> None:
    """이벤트가 생길 때마다 fn(event) 를 부른다. None 이면 끊는다.

    라이브 모드는 이걸로 SSE 에 흘려보낸다. 녹화·재생은 이 함수를 쓰지 않는다 —
    emit() 이 하는 일(기록)은 그대로다.
    """
    global _sink
    with _lock:
        _sink = fn


def emit(type: str, **payload) -> dict:
    """의미 이벤트 하나를 기록한다. 키는 계획서 4.1절의 한국어 스펙 그대로."""
    event = {"v": PROTOCOL_VERSION, "type": type, "ts": round(time.time() - _t0, 3)}
    event.update(payload)
    with _lock:
        _events.append(event)
        if _console:
            print("  " + json.dumps(event, ensure_ascii=False)[:220], flush=True)
        sink = _sink
    if sink:
        # 구독자 쪽 예외가 파이프라인을 죽이지 않게 한다 (끊긴 SSE 연결 등)
        try:
            sink(event)
        except Exception:
            pass
    return event


def dump() -> list[dict]:
    with _lock:
        return list(_events)


def save(path: Path, **head) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {**head, "events": dump()}
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
