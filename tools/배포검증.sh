#!/usr/bin/env bash
# 배포본 실측 — 정적 · SSE · 시간 · 키 취급
#
#   bash tools/배포검증.sh https://<배포>.vercel.app "$(grep -m1 '^OPENAI_API_KEY=' .env.local | cut -d= -f2-)"
#
# 정적 4종이 200 인지가 관문이다. 405 가 나오면 프로젝트가 framework:python 으로 잡혀
# 모든 요청이 단일 함수로 가고 있다는 뜻이다 (7단계에서 한 번 밟았다).
BASE="$1"; KEY="$2"
echo "=== 대상: $BASE"
echo "--- 정적"
for p in "/" "/src/player.js" "/assets/furniture/desk_SE.png" "/runs/%EB%8B%A4%EA%B0%88%EB%9E%98-%EA%B8%B0%EB%B3%B8.json"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "$BASE$p")
  size=$(curl -s -o /dev/null -w "%{size_download}" --max-time 20 "$BASE$p")
  printf "  %-46s %s (%s bytes)\n" "$p" "$code" "$size"
done
echo "--- API 오류 경로"
printf "  키 없음:   "; curl -sN --max-time 30 -X POST "$BASE/api/live" -H 'Content-Type: application/json' -d '{"question":"테스트"}' | head -2 | tail -1
printf "  빈 질문:   "; curl -s --max-time 30 -X POST "$BASE/api/live" -H 'Content-Type: application/json' -d '{"question":""}' -w " (%{http_code})\n"
printf "  GET:       "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 20 "$BASE/api/live"
if [ -n "$KEY" ]; then
  echo "--- 라이브 한 바퀴 (간단)"
  OUT=$(mktemp)
  START=$(date +%s.%N)
  curl -sN --max-time 300 -X POST "$BASE/api/live" -H 'Content-Type: application/json' \
    -H "X-API-Key: $KEY" -d '{"question":"MBTI 궁합론은 어떤 근거로 제시되는가?","preset":"간단"}' > "$OUT"
  END=$(date +%s.%N)
  echo "  걸린 시간: $(echo "$END - $START" | bc)초"
  echo "  이벤트: $(grep -c '^event:' "$OUT")개"
  grep '^event:' "$OUT" | sort | uniq -c | sed 's/^/    /'
  echo "  키 유출: $(grep -c "$KEY" "$OUT")건"
  python3 - "$OUT" <<'PY'
import json,sys
for b in open(sys.argv[1],encoding="utf-8").read().split("\n\n"):
    if "event: result" in b:
        d=json.loads([l for l in b.split("\n") if l.startswith("data:")][0][5:])
        m=d.get("metrics",{})
        print(f"  보고서 {len(d.get('report',''))}자 · 호출 {d['usage']['calls']}회 · ₩{d['cost_krw']}")
        print(f"  근거율 {m.get('근거율')} · 허위 {m.get('허위인용')} · 그물 {m.get('그물',{}).get('통과')}")
    if "event: error" in b:
        print("  오류:", b.split("data:")[-1].strip()[:160])
PY
  rm -f "$OUT"
fi
