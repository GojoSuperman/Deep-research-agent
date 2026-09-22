"""키 입력기 — python -m pipeline.setkey

입력한 키는 화면에 찍히지 않고 .env.local (권한 600) 에만 들어간다.
--check 만 주면 입력 없이 지금 키가 먹는지만 본다.
"""
from __future__ import annotations

import argparse
import getpass
import os
import re
import subprocess
import sys
from pathlib import Path

from . import llm

PREFIXES = ("sk-",)  # OpenAI. 게이트웨이 키면 경고만 하고 받는다


def from_clipboard() -> str:
    """윈도우 클립보드에서 가져온다. 키가 화면·기록 어디에도 안 남는 경로."""
    cmds = [
        ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard"],  # WSL
        ["pbpaste"], ["xclip", "-selection", "clipboard", "-o"], ["wl-paste"],
    ]
    for cmd in cmds:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if r.returncode == 0:
            return r.stdout.strip()
    raise RuntimeError("클립보드를 읽을 수 없다 (powershell.exe/pbpaste/xclip 모두 실패)")


def from_file(path: str) -> str:
    """파일에서 가져온다. 메모장이 남기는 BOM·CRLF·따옴표·# 주석줄을 걷어낸다."""
    raw = Path(path).expanduser().read_text(encoding="utf-8-sig")  # utf-8-sig = BOM 제거
    for line in raw.splitlines():
        line = line.strip().strip('"').strip("'")
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith("OPENAI_API_KEY="):
            line = line.split("=", 1)[1].strip().strip('"').strip("'")
        return line
    return ""


def read_env(path=llm.ENV_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def write_env(values: dict[str, str], path=llm.ENV_PATH) -> None:
    body = ["# 딥리서치 에이전트 — 로컬 전용. 절대 커밋하지 않는다.",
            "# 만든 곳: python -m pipeline.setkey", ""]
    body += [f"{k}={v}" for k, v in values.items() if v]
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def main() -> int:
    p = argparse.ArgumentParser(description="OPENAI_API_KEY 를 .env.local 에 넣는다")
    p.add_argument("--check", action="store_true", help="입력 없이 지금 키만 확인")
    p.add_argument("--model", help="모델 이름 지정 (기본 gpt-4o-mini)")
    p.add_argument("--show", action="store_true", help="현재 설정을 가린 채 보여준다")
    p.add_argument("--from-clipboard", action="store_true",
                   help="윈도우 클립보드에서 키를 가져온다 (tty 불필요)")
    p.add_argument("--from-file", metavar="경로",
                   help="파일 첫 줄에서 키를 가져온다")
    p.add_argument("--wipe", action="store_true",
                   help="--from-file 로 읽은 뒤 그 파일을 지운다")
    a = p.parse_args()

    current = read_env()

    if a.show or a.check:
        print(f"  파일   {llm.ENV_PATH} {'있음' if llm.ENV_PATH.exists() else '없음'}")
        print(f"  키     {llm.mask(current.get('OPENAI_API_KEY') or llm.api_key())}")
        print(f"  모델   {llm.model_name()}")
    if a.check:
        print("  확인 중…")
        r = llm.check()
        print("  결과   " + ("✅ 먹는다" if r["ok"] else "❌ " + r["이유"]))
        if r["ok"]:
            print(f"         모델 {r['모델']} · 응답 {r['응답']!r} · 토큰 {r['토큰']}")
        return 0 if r["ok"] else 1
    if a.show:
        return 0

    if a.from_clipboard:
        try:
            key = from_clipboard()
        except RuntimeError as e:
            print(f"  ❌ {e}")
            return 2
        print(f"  클립보드에서 {len(key)}자 읽었다.")
    elif a.from_file:
        key = from_file(a.from_file)
        print(f"  {a.from_file} 에서 {len(key)}자 읽었다.")
    elif sys.stdin.isatty():
        print("OPENAI_API_KEY 를 붙여넣어라. 화면에 찍히지 않는다. (취소: 빈 줄 + Enter)")
        key = getpass.getpass("  키: ").strip()
    else:
        print("❌ 여기서는 가려 받을 수 없다 (tty 없음). 둘 중 하나를 써라:")
        print("   ① 키를 복사해 두고:  ! .venv/bin/python -m pipeline.setkey --from-clipboard")
        print("   ② 파일에 적어 두고:  ! .venv/bin/python -m pipeline.setkey --from-file ~/key.txt --wipe")
        return 2

    key = key.strip()
    if not key:
        print("  비어 있다. 아무것도 쓰지 않았다.")
        return 1
    if not key.startswith(PREFIXES):
        print(f"  ⚠ {PREFIXES[0]} 로 시작하지 않는다. 그래도 저장한다.")
    if re.search(r"\s", key):
        print("  ❌ 키에 공백이 들어 있다. 붙여넣기를 다시 확인해라.")
        return 1

    model = a.model or current.get("OPENAI_MODEL") or llm.DEFAULT_MODEL
    values = {**current, "OPENAI_API_KEY": key, "OPENAI_MODEL": model}
    write_env(values)
    print(f"  저장 → {llm.ENV_PATH} (권한 600) · 키 {llm.mask(key)} · 모델 {model}")

    if a.wipe and a.from_file:
        Path(a.from_file).expanduser().unlink(missing_ok=True)
        print(f"  지움 → {a.from_file}")

    os.environ["OPENAI_API_KEY"] = key
    os.environ["OPENAI_MODEL"] = model
    print("  확인 중…")
    r = llm.check(key)
    print("  결과   " + ("✅ 먹는다" if r["ok"] else "❌ " + r["이유"]))
    if r["ok"]:
        print(f"         모델 {r['모델']} · 응답 {r['응답']!r} · 토큰 {r['토큰']}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
