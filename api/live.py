"""라이브 모드 — 방문자 본인 키로 한 바퀴 돌리고 이벤트를 SSE 로 흘린다 (계획서 3.3 · 8장).

여기 있는 stream() 은 프레임워크를 모른다. 로컬 개발 서버(tools/dev_server.py)와
Vercel 함수가 같은 함수를 부른다. 7단계에서 배포 껍데기만 덧씌운다.

키 취급 (계획서 8.2):
  - 인자로만 받는다. 파일·로그·응답 어디에도 쓰지 않는다.
  - 예외 메시지에 섞여 나올 경우를 대비해 내보내기 직전에 한 번 더 지운다.
"""
from __future__ import annotations

import asyncio
import json
import queue
import threading
import traceback

from pipeline import events, graph, llm
from pipeline.corpus import Corpus, load as load_corpus
from pipeline.state import DEFAULT_SETTINGS

# 방문자가 고를 수 있는 규모 두 가지. 이름은 화면에 그대로 뜬다.
PRESETS = {
    "간단": {"sections": 2, "budget": 2},
    "정식": {"sections": 4, "budget": 3},
}
MAX_QUESTION = 200

# 동시 실행 1회 제한 (계획서 11장 — 방문자가 반복 실행해 비용이 터지는 것을 막는다).
# 파이프라인 전역 상태(events._events · llm.USAGE · 방문자 키)를 한 실행이 독점해야 하는
# 이유도 같다. 두 요청이 겹치면 두 번째는 429.
_run_lock = threading.Lock()

_corpus: Corpus | None = None
_corpus_lock = threading.Lock()


def corpus() -> Corpus:
    """52건을 한 번만 읽어 둔다 (함수가 따뜻할 때 재사용)."""
    global _corpus
    with _corpus_lock:
        if _corpus is None:
            _corpus = load_corpus()
        return _corpus


class Busy(Exception):
    """이미 한 편이 돌고 있다."""


def parse(body: dict) -> tuple[str, dict]:
    """요청 본문을 질문과 설정으로 푼다. 값은 전부 여기서 조인다."""
    question = str(body.get("question") or "").strip()
    if not question:
        raise ValueError("질문이 비었다")
    question = question[:MAX_QUESTION]

    preset = PRESETS.get(str(body.get("preset") or "간단"), PRESETS["간단"])
    settings = {**DEFAULT_SETTINGS, **preset}
    for k in ("assign", "zone", "role", "redelegate"):
        if k in body:
            settings[k] = bool(body[k])
    settings["sections"] = max(1, min(4, int(body.get("sections", settings["sections"]))))
    settings["budget"] = max(1, min(3, int(body.get("budget", settings["budget"]))))
    return question, settings


def _sse(type: str, payload: dict, secret: str | None = None) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    if secret and secret in text:      # 키가 섞여 나가는 일은 없어야 한다
        text = text.replace(secret, "…")
    return f"event: {type}\ndata: {text}\n\n"


def stream(question: str, settings: dict, key: str):
    """SSE 본문을 조각조각 내놓는다. 호출자는 그대로 write 하면 된다.

    이벤트 타입은 계획서 4.1 스펙 그대로 `event: 의미이벤트타입` 에 실린다.
    끝에 서버만 아는 두 가지를 덧붙인다 — `result`(보고서·비용)와 `error`.
    """
    if not key:
        yield _sse("error", {"message": "API 키가 없다"})
        return
    if not _run_lock.acquire(blocking=False):
        yield _sse("error", {"message": "지금 다른 실행이 돌고 있다. 끝나면 다시 눌러라", "code": 429})
        return

    q: queue.Queue = queue.Queue()
    done = object()
    result: dict = {}

    def worker():
        try:
            with llm.use_key(key):
                out = graph.run(question, settings, corpus=corpus())
            state = out["state"]
            u = out["usage"]
            cost = u["prompt"] / 1e6 * 0.15 + u["completion"] / 1e6 * 0.6   # gpt-4o-mini
            result.update(report=state.get("report", ""), metrics=state.get("metrics"),
                          usage=u, cost_krw=round(cost * 1400))
        except Exception as e:
            name = type(e).__name__
            friendly = {
                "AuthenticationError": "키가 거부됐다 (401). 키를 다시 확인해라",
                "RateLimitError": "키의 사용 한도에 걸렸다 (429). 잔액·한도를 확인해라",
                "PermissionDeniedError": "이 키로는 이 모델을 못 쓴다 (403)",
            }.get(name)
            result["error"] = friendly or f"{name}: {e}"[:300]
            traceback.print_exc()
        finally:
            q.put(done)

    try:
        events.subscribe(q.put)
        threading.Thread(target=worker, daemon=True).start()
        while True:
            try:
                item = q.get(timeout=10)
            except queue.Empty:
                yield ": ping\n\n"          # 프록시가 끊지 않게 (기획 노드는 10초 넘게 조용하다)
                continue
            if item is done:
                break
            yield _sse(item["type"], item, key)
        if "error" in result:
            yield _sse("error", {"message": result["error"]}, key)
        else:
            yield _sse("result", result, key)
    finally:
        events.subscribe(None)
        _run_lock.release()


HEADERS = [
    ("Content-Type", "text/event-stream; charset=utf-8"),
    ("Cache-Control", "no-cache, no-transform"),
    ("Connection", "keep-alive"),
    ("X-Accel-Buffering", "no"),
]


def wsgi_app(environ, start_response):
    """WSGI 껍데기 — 로컬 개발 서버(tools/dev_server.py)가 쓴다."""
    if environ.get("REQUEST_METHOD") != "POST":
        start_response("405 Method Not Allowed", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"POST only"]
    try:
        size = int(environ.get("CONTENT_LENGTH") or 0)
        body = json.loads(environ["wsgi.input"].read(size) or b"{}")
        question, settings = parse(body)
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"message": str(e)[:200]}, ensure_ascii=False).encode()]

    key = environ.get("HTTP_X_API_KEY", "")
    start_response("200 OK", HEADERS)
    return (chunk.encode("utf-8") for chunk in stream(question, settings, key))


# ── Vercel 용 ASGI ────────────────────────────────────────
# Vercel 의 Python 런타임은 모듈의 `app` 을 찾는다. WSGI 로 내보내면 스트리밍이
# 버퍼링될 수 있어, SSE 는 ASGI 로 내보낸다 (프레임워크 없이 프로토콜만 따른다).
async def app(scope, receive, send):
    if scope["type"] != "http":
        return
    if scope.get("method") != "POST":
        await _send_json(send, 405, {"message": "POST only"})
        return

    body = b""
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            return
        body += message.get("body", b"")
        if not message.get("more_body"):
            break

    try:
        question, settings = parse(json.loads(body or b"{}"))
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        await _send_json(send, 400, {"message": str(e)[:200]})
        return

    headers = {k.lower(): v for k, v in
               ((h.decode(), v.decode()) for h, v in scope.get("headers", []))}
    key = headers.get("x-api-key", "")

    await send({"type": "http.response.start", "status": 200,
                "headers": [(k.encode(), v.encode()) for k, v in HEADERS]})
    # 블로킹 제너레이터를 스레드에서 돌려 이벤트 루프를 막지 않는다
    loop = asyncio.get_running_loop()
    gen = stream(question, settings, key)
    sentinel = object()
    while True:
        chunk = await loop.run_in_executor(None, lambda: next(gen, sentinel))
        if chunk is sentinel:
            break
        await send({"type": "http.response.body", "body": chunk.encode("utf-8"),
                    "more_body": True})
    await send({"type": "http.response.body", "body": b"", "more_body": False})


async def _send_json(send, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8")]})
    await send({"type": "http.response.body", "body": body})
