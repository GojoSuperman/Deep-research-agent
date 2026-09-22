"""개발 서버 — 정적 web/ + 라이브 API 한 프로세스.

  .venv/bin/python tools/dev_server.py [포트]

캐시를 끈다. 보통 http.server 로 띄우면 브라우저가 옛 모듈을 쥐고 있어 수정이 안 보인다.
/api/live 는 api/live.py 의 WSGI 앱을 그대로 부른다 — Vercel 과 같은 코드를 쓴다.
"""
from __future__ import annotations

import io
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import live  # noqa: E402
from pipeline import llm  # noqa: E402

WEB = ROOT / "web"


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/live":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        # 개발 편의 — 헤더에 키가 없으면 .env.local 키로 돈다.
        # 이 관대함은 이 파일에만 있다. 배포로 나가는 api/live.py 는 헤더 키만 받는다.
        # (.env.local 은 git 에 안 따라가므로 Vercel 에는 이 키 자체가 없다)
        key = self.headers.get("X-API-Key", "") or (llm.api_key() or "")
        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_LENGTH": str(length),
            "wsgi.input": io.BytesIO(self.rfile.read(length)),
            "HTTP_X_API_KEY": key,
        }
        started: dict = {}

        def start_response(status, headers):
            started["status"] = status
            started["headers"] = headers

        body = live.app(environ, start_response)
        code = int(started["status"].split()[0])
        self.send_response(code)
        for k, v in started["headers"]:
            self.send_header(k, v)
        # 스트리밍이라 길이를 모른다 — 청크 전송
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        try:
            for chunk in body:
                if not chunk:
                    continue
                self.wfile.write(f"{len(chunk):X}\r\n".encode() + chunk + b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
        except (BrokenPipeError, ConnectionResetError):
            pass   # 방문자가 탭을 닫았다. 파이프라인은 스스로 끝난다

    def log_message(self, fmt, *args):
        # 키가 로그에 남을 여지를 아예 없앤다 — 경로와 상태만 찍는다
        sys.stderr.write(f"  {self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}\n")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8732
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    has = bool(llm.api_key())
    print(f"딥리서치 연구소 → http://127.0.0.1:{port}  (Ctrl+C 로 종료)", flush=True)
    print(f"  라이브 키: {'.env.local 키로 대신 돈다 (키 칸을 비워 둬도 된다)' if has else '없다 — 화면에서 직접 넣어야 한다'}",
          flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
