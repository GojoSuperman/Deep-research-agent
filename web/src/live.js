// 라이브 모드 — 방문자 본인 키로 서버에 한 바퀴를 부탁하고 SSE 를 받는다 (계획서 3.3 · 8.2).
//
// EventSource 를 못 쓴다. POST 도 헤더도 안 되기 때문이다. fetch + ReadableStream 으로 직접 읽는다.
// 키는 localStorage 와 요청 헤더에만 있다. 쿼리스트링에 싣지 않는다 — 주소창·서버 로그에 남는다.

const KEY_STORE = "딥리서치.키";

export const keyStore = {
  load: () => { try { return localStorage.getItem(KEY_STORE) || ""; } catch { return ""; } },
  save: k => { try { localStorage.setItem(KEY_STORE, k); } catch { /* 사생활 모드 */ } },
  clear: () => { try { localStorage.removeItem(KEY_STORE); } catch { /* 무시 */ } },
};

export const mask = k => (!k ? "(없음)" : `${k.slice(0, 3)}…${k.slice(-4)}`);

/** SSE 본문 한 덩어리를 프레임으로 쪼갠다. `event:`/`data:` 두 줄만 쓴다. */
function* frames(buffer) {
  for (const block of buffer.split("\n\n")) {
    if (!block.trim() || block.startsWith(":")) continue;   // 하트비트(: ping)
    let type = "message", data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) type = line.slice(6).trim();
      else if (line.startsWith("data:")) data += line.slice(5).trim();
    }
    if (data) yield { type, data };
  }
}

/**
 * 한 편을 실행한다. 이벤트가 올 때마다 onEvent(의미이벤트) 를 부른다.
 * 되돌려 주는 것은 { stop } — 방문자가 멈추면 연결을 끊는다.
 */
export function run({ question, preset, key, onEvent, onResult, onError, onClose }) {
  const ctrl = new AbortController();

  (async () => {
    let closedBy = "end";
    try {
      const res = await fetch("api/live", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": key },
        body: JSON.stringify({ question, preset }),
        signal: ctrl.signal,
      });
      if (!res.ok && res.headers.get("Content-Type")?.includes("json")) {
        onError?.((await res.json()).message || `서버 오류 ${res.status}`);
        return;
      }
      if (!res.body) { onError?.("이 브라우저가 스트리밍을 못 읽는다"); return; }

      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const cut = buf.lastIndexOf("\n\n");
        if (cut < 0) continue;
        const ready = buf.slice(0, cut + 2);
        buf = buf.slice(cut + 2);
        for (const f of frames(ready)) {
          let payload;
          try { payload = JSON.parse(f.data); } catch { continue; }
          if (f.type === "error") { closedBy = "error"; onError?.(payload.message || "알 수 없는 오류"); }
          else if (f.type === "result") onResult?.(payload);
          else onEvent?.(payload);
        }
      }
    } catch (e) {
      if (e.name === "AbortError") closedBy = "stop";
      else { closedBy = "error"; onError?.(`연결이 끊겼다: ${e.message}`); }
    } finally {
      onClose?.(closedBy);
    }
  })();

  return { stop: () => ctrl.abort() };
}
