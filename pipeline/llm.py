"""LLM 접속 — 키는 .env.local 에서만 읽는다. 저장소에는 어떤 키도 없다.

라이브 모드(6단계)는 방문자 키를 헤더로 받아 client(key=...) 로 넘긴다.
그래서 키 출처를 여기 한 곳으로 모아 둔다.
"""
from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env.local"

DEFAULT_MODEL = "gpt-4o-mini"
CONTEXT_CHARS = 60_000  # 긴 문서는 앞부분 위주 (계획서 11장 리스크 대응)

# 토큰 사용량 — 병렬 조사관이 동시에 더하므로 락으로 보호한다
_usage_lock = threading.Lock()
USAGE = {"calls": 0, "prompt": 0, "completion": 0}


def reset_usage() -> None:
    with _usage_lock:
        USAGE.update(calls=0, prompt=0, completion=0)


def _track(r) -> None:
    u = getattr(r, "usage", None)
    with _usage_lock:
        USAGE["calls"] += 1
        if u:
            USAGE["prompt"] += u.prompt_tokens or 0
            USAGE["completion"] += u.completion_tokens or 0


def usage() -> dict:
    with _usage_lock:
        return dict(USAGE)


def load_env(path: Path = ENV_PATH) -> bool:
    """.env.local 을 환경에 얹는다. 이미 있는 환경 변수가 우선."""
    if path.exists():
        load_dotenv(path, override=False)
        return True
    return False


# 라이브 모드(6단계)에서 방문자 키를 담는 자리. 한 번에 한 실행만 허용한다.
# 노드들은 llm.ask(key=...) 를 쓰지 않으므로 키를 여기 한 곳에 얹어 전달한다.
_visitor_lock = threading.Lock()
_visitor_key: str | None = None


@contextmanager
def use_key(key: str | None):
    """이 블록 안의 모든 호출이 이 키를 쓴다. 빠져나가면 지운다.

    방문자 키는 메모리에만 두고 로그·파일 어디에도 남기지 않는다 (계획서 8.2).
    """
    global _visitor_key
    with _visitor_lock:
        _visitor_key = key or None
    try:
        yield
    finally:
        with _visitor_lock:
            _visitor_key = None
        if key:
            _client.cache_clear()   # 방문자 키를 캐시에 남기지 않는다


def api_key(explicit: str | None = None) -> str | None:
    if explicit:
        return explicit
    with _visitor_lock:
        if _visitor_key:
            return _visitor_key
    load_env()
    return os.getenv("OPENAI_API_KEY") or None


def model_name() -> str:
    load_env()
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL)


def mask(key: str | None) -> str:
    if not key:
        return "(없음)"
    return f"{key[:3]}…{key[-4:]} ({len(key)}자)"


@lru_cache(maxsize=4)
def _client(key: str, base_url: str | None):
    from openai import OpenAI

    return OpenAI(api_key=key, base_url=base_url or None)


def client(key: str | None = None):
    k = api_key(key)
    if not k:
        raise RuntimeError(
            "OPENAI_API_KEY 가 없다. `python -m pipeline.setkey` 로 넣어라."
        )
    return _client(k, os.getenv("OPENAI_BASE_URL"))


def ask(prompt: str, *, system: str = "", key: str | None = None,
        model: str | None = None, cap: int = CONTEXT_CHARS,
        temperature: float = 0.2) -> str:
    """한 번 묻고 한 번 받는다. cap 으로 입력 길이를 자른다."""
    msgs = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt[:cap]}
    ]
    r = client(key).chat.completions.create(
        model=model or model_name(), messages=msgs, temperature=temperature,
    )
    _track(r)
    return (r.choices[0].message.content or "").strip()


def ask_json(prompt: str, *, system: str = "", key: str | None = None,
             model: str | None = None, cap: int = CONTEXT_CHARS,
             temperature: float = 0.2, retries: int = 1) -> dict:
    """JSON 하나를 받아 온다. 깨지면 한 번 더 묻는다 (모델은 가끔 말을 덧붙인다)."""
    sys_msg = (system + "\n" if system else "") + "반드시 JSON 객체 하나만 출력한다."
    last = ""
    for attempt in range(retries + 1):
        msgs = [{"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt[:cap]}]
        if attempt:
            msgs.append({"role": "user",
                         "content": f"직전 응답이 JSON 으로 안 읽혔다: {last[:200]}\n다시, JSON 객체만."})
        r = client(key).chat.completions.create(
            model=model or model_name(), messages=msgs, temperature=temperature,
            response_format={"type": "json_object"},
        )
        _track(r)
        last = (r.choices[0].message.content or "").strip()
        try:
            return json.loads(last)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"JSON 파싱 실패: {last[:300]}")


def check(key: str | None = None) -> dict:
    """키가 실제로 먹는지 확인한다. 아주 짧은 호출 한 번."""
    k = api_key(key)
    if not k:
        return {"ok": False, "이유": "키 없음", "키": mask(None)}
    m = model_name()
    try:
        r = client(k).chat.completions.create(
            model=m, max_completion_tokens=5,
            messages=[{"role": "user", "content": "ping 이라고만 답해"}],
        )
        used = r.usage.total_tokens if r.usage else 0
        return {"ok": True, "키": mask(k), "모델": m, "응답": (r.choices[0].message.content or "").strip(), "토큰": used}
    except Exception as e:  # 네트워크·인증·모델명 문제를 그대로 보여준다
        return {"ok": False, "이유": f"{type(e).__name__}: {e}"[:300], "키": mask(k), "모델": m}
