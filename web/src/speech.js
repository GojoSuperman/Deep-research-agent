// 말풍선 대사 — 이벤트 하나를 사람의 말로 옮긴다.
//
// 지키는 것 셋:
//  1. **녹화에 실린 사실만 말한다.** 배정을 끈 실험에서 "이 서고로 가세요"라고 하면 거짓말이다.
//  2. 조사(은/는·이/가…)는 받침을 보고 붙인다. 절 제목과 문서명은 녹화마다 달라 손으로 못 맞춘다.
//  3. 같은 상황에도 말을 몇 가지 돌려 쓰되, **같은 녹화는 늘 같은 대사**가 나오게 한다 (seed 로 고른다).
//
// 조사관 대사는 짧게 — 연출 시간(DUR) 안에 다 쳐져야 한다. 회의 대사는 길어도 되지만
// 한 줄이 늘면 재생 전체가 늘어난다 (배리어가 말이 끝나길 기다린다).
import { name } from "./actors.js";
import { docKo } from "./docs.js";

const num = n => (n ?? 0).toLocaleString("ko-KR");

/** 3만 1천 → "3만", 15660 → "1만 6천" 처럼 말로 읽기 좋은 어림수 */
function roughly(n) {
  if (n >= 10000) {
    const man = Math.floor(n / 10000), cheon = Math.round((n % 10000) / 1000);
    return cheon === 10 ? `${man + 1}만` : cheon ? `${man}만 ${cheon}천` : `${man}만`;
  }
  if (n >= 1000) return `${Math.round(n / 1000)}천`;
  return num(n);
}

// ── 조사 ──────────────────────────────────────────────────
// 끝 글자의 받침을 본다. 닫는 괄호·공백·마침표는 건너뛴다 (「…」 뒤에 붙는 조사).
// 한글이 아니면 소리 나는 대로 어림한다 — 숫자와 영문 끝 글자.
const DIGIT = { 0: 1, 1: 1, 2: 0, 3: 1, 4: 0, 5: 0, 6: 1, 7: 1, 8: 1, 9: 0 };   // 영·일·삼·육·칠·팔 = 받침
const LATIN_JONG = /[lmnr]$/i;             // 엘·엠·엔·알 — 받침 소리로 읽히는 끝 글자
function tail(word) {
  const s = String(word).replace(/[\s」』)\]'".…·]+$/u, "");
  const ch = s.at(-1) || "";
  const code = ch.charCodeAt(0) - 0xac00;
  if (code >= 0 && code < 11172) {
    const jong = code % 28;
    return { jong: jong > 0, rieul: jong === 8 };
  }
  if (/\d/.test(ch)) return { jong: !!DIGIT[ch], rieul: ch === "1" || ch === "7" || ch === "8" };
  return { jong: LATIN_JONG.test(ch), rieul: /[lr]$/i.test(ch) };
}
/** 조사를 붙여 돌려준다. pair = "은/는" 처럼 받침 있을 때/없을 때 */
export function josa(word, pair) {
  const [withJ, noJ] = pair.split("/");
  const t = tail(word);
  if (pair === "으로/로") return word + (t.jong && !t.rieul ? "으로" : "로");
  return word + (t.jong ? withJ : noJ);
}

// ── 고르기 ────────────────────────────────────────────────
function hash(s) {
  let h = 2166136261;
  for (const ch of String(s)) h = Math.imul(h ^ ch.codePointAt(0), 16777619);
  return h >>> 0;
}
/** 같은 seed 면 늘 같은 것을 고른다 — 재생할 때마다 대사가 바뀌면 캡처·리뷰가 어긋난다 */
const pick = (seed, list) => list[hash(seed) % list.length];

/** 역할이 무엇을 보라는 것인지 — 조사관이 첫마디에 제 역할을 풀어 말한다 */
const ROLE_LEAD = {
  "큰그림": "전체 흐름을 잡아 볼게요",
  "비교": "견줘 볼 거리를 찾아볼게요",
  "원인": "왜 그런지 파 볼게요",
  "인물": "사람 이야기를 따라가 볼게요",
  "시간순": "시간 순서대로 짚어 볼게요",
};
const roleKey = r => (r || "").replace(/\s*담당$/, "");

// ── 회의 ──────────────────────────────────────────────────

/** 소장이 회의에서 할 말. [누구, 할 말] 목록 — 누구 = "coord" 또는 조사관 인덱스 */
export function planTalk(ev, cfg = {}, question = "") {
  const 목차 = ev.목차 || [];
  const 배정 = cfg.배정 !== false, 역할 = cfg.역할 !== false;
  const n = 목차.length;
  const lines = [];
  lines.push(["coord", question
    ? `오늘 질문은 이겁니다 — “${question}”`
    : "오늘 질문을 같이 보겠습니다"]);
  lines.push(["coord", pick(question + "split", [
    `혼자 보기엔 넓으니 ${n}갈래로 나눠 보죠`,
    `이걸 ${n}개의 절로 쪼개서 나눠 맡겠습니다`,
  ])]);
  목차.forEach((s, i) => {
    const who = name(i);
    const 절 = `「${s.절}」`;
    // 배정을 끄면 소장이 시작 문서를 고르지 않는다 — 서고를 말하면 거짓말이 된다 (실측: 절과 서고가 따로 논다)
    if (!배정) { lines.push(["coord", `${josa(who, "은/는")} ${josa(절, "을/를")} 맡아 주세요`]); return; }
    const 역할말 = 역할 && roleKey(s.역할) && ROLE_LEAD[roleKey(s.역할)] ? `${josa(s.역할, "으로/로")} ` : "";
    lines.push(["coord", pick(s.절 + i, [
      `${josa(who, "은/는")} ${역할말}${josa(절, "을/를")} 맡아 주세요. ${s.서고} 서고부터 보면 됩니다`,
      `${who}, ${역할말}${josa(절, "을/를")} 부탁해요. ${s.서고} 서고에서 시작하세요`,
    ])]);
  });
  if (!배정) {
    lines.push(["coord", "이번엔 어디서 시작할지 제가 정해 주지 않습니다"]);
    lines.push(["coord", "목록에 있는 순서대로 집어 가세요. 어디에 닿을지는 저도 모릅니다"]);
  } else if (!역할) {
    lines.push(["coord", "이번엔 따로 보는 눈을 정해 주지 않을게요. 각자 알아서 봐 주세요"]);
  }
  lines.push(["coord", "서로 무엇을 읽는지는 모르는 채로 각자 다녀옵니다"]);
  lines.push([0, pick(question + "ok", ["네, 다녀오겠습니다!", "알겠습니다, 다녀올게요", "좋아요, 금방 다녀오겠습니다"])]);
  return lines;
}

// ── 조사관 ────────────────────────────────────────────────

export function startLine(ev, cfg = {}) {
  const doc = docKo(ev.시작문서);
  if (cfg.배정 === false)
    return pick(ev.절, [`목록에서 집은 ${doc}부터 볼게요`, `일단 ${josa(doc, "을/를")} 펼쳐 볼게요`]);
  const lead = ROLE_LEAD[roleKey(ev.역할)];
  if (lead && cfg.역할 !== false) return `${doc}부터 보면서 ${lead}`;
  return pick(ev.절, [`${doc}부터 펼쳐 볼게요`, `먼저 ${josa(doc, "을/를")} 훑어보겠습니다`,
                      `${doc}에서 실마리를 찾아볼게요`]);
}

export function readLine(ev) {
  const doc = docKo(ev.문서);
  const seed = ev.절 + ev.문서;
  if (!ev.관련) return pick(seed, [`${josa(doc, "은/는")} 우리 절이랑 거리가 머네요`,
                                   `${doc}… 여긴 아니에요`, `${josa(doc, "은/는")} 건너뛸게요`]);
  if (ev.원문자수 && ev.메모자수)
    return pick(seed, [`${doc} ${roughly(ev.원문자수)} 자 중에 ${num(ev.메모자수)}자만 적어 갈게요`,
                       `${doc}에서 쓸 만한 걸 찾았어요`,
                       `${doc} 읽는 중… 필요한 데만 적고 있어요`]);
  return `${doc} 읽는 중…`;
}

export function fixLine(ev) {
  const 허위 = ev.허위 || [];
  const what = 허위.length === 1 ? `안 읽은 ${josa(docKo(허위[0]), "을/를")} 출처로 적었네요`
             : 허위.length ? "안 읽은 문서를 출처로 적었네요"
             : "출처를 하나도 안 달았네요";
  // 채택 = 고쳐 쓴 원고를 받았나. 못 받았으면 처음 원고로 간다 — "고쳤다"고 하면 거짓말이다
  return ev.채택 === false ? `앗, ${what}. 다시 써 봤는데 처음 게 나아요` : `앗, ${what}. 고쳐 쓸게요`;
}

export function doneLine(ev) {
  if (!ev.인용) return pick(ev.절, ["근거를 하나도 못 찾았어요…", "빈손이에요. 붙일 근거가 없었어요"]);
  if (ev.충분) return pick(ev.절, [`다 썼어요! 출처 ${ev.인용}곳 달았습니다`, `원고 끝 — 출처 ${ev.인용}곳이에요`]);
  return `출처 ${ev.인용}곳… 그래도 좀 모자라요`;
}

// ── 점검 회의 ─────────────────────────────────────────────

/** 조사관 보고 한 줄 */
export function reportLine(d) {
  const 절 = `「${d.절}」`;
  if (!d.인용) return pick(d.절 + "r", [`${josa(절, "은/는")} 근거를 못 찾았습니다. 죄송해요`,
                                        `저는 빈손입니다 — ${절}에 붙일 근거가 없었어요`]);
  return pick(d.절 + "r", [`${josa(절, "은/는")} ${num(d.자수)}자 썼고, 출처는 ${d.인용}곳입니다`,
                           `저는 ${절} ${num(d.자수)}자요. 출처 ${d.인용}곳 달았습니다`]);
}

/**
 * 소장의 정리 — 종료 사유를 봐야 한다.
 * 빈칸이 있어도 바퀴를 다 썼거나 재위임을 끈 실험이면 **되돌려 보내지 않는다**.
 * who(절) = 그 절을 맡은 조사관 인덱스
 */
export function reviewClose(ev, who, cites = () => 0) {
  const 빈칸 = ev.빈칸 || [];
  const 목록 = 빈칸.map(t => `「${t}」`).join(" ");
  // 빈칸 = 인용 0곳 **또는** 조사관이 스스로 모자라다고 신고한 절 (pipeline/nodes.py review).
  // 출처를 8곳 단 절에 "비었네요"라고 하면 방금 들은 보고와 어긋난다.
  const 없음 = 빈칸.filter(t => !cites(t)).length;
  const 상태 = 없음 === 빈칸.length ? `${목록}에 근거가 없네요`
             : 없음 === 0 ? `${josa(목록, "은/는")} 아직 모자라다고 했죠`
             : `${josa(목록, "이/가")} 비었거나 아직 모자라요`;
  if (!빈칸.length)
    return [["coord", pick(String(ev.절수), ["좋습니다. 모든 절에 근거가 붙었네요",
                                             "훌륭해요. 빈 절이 하나도 없습니다"])],
            ["coord", "이제 제가 한 편으로 엮겠습니다"]];
  if (!ev.종료) {
    const back = 빈칸.map(who).filter(i => i != null);
    const names = back.map(name).join(", ");
    return [["coord", 상태],
            ["coord", names ? `${names}, 한 번만 더 다녀와 주세요` : "한 번만 더 다녀와 주세요"],
            ...(back.length ? [[back[0], "네, 다시 찾아보겠습니다"]] : [])];
  }
  if (ev.종료 === "재위임 끔")
    return [["coord", 상태],
            ["coord", "그래도 이번엔 다시 보내지 않는 실험이에요"],
            ["coord", "있는 그대로 정리하겠습니다"]];
  const 바퀴 = /(\d+)바퀴/.exec(ev.종료)?.[1];
  return [["coord", `${josa(목록, "은/는")} 끝내 다 채우지 못했네요`],
          ["coord", 바퀴 ? `정해 둔 ${바퀴}바퀴를 다 돌았으니 이대로 정리할게요` : `${ev.종료} — 이대로 정리할게요`]];
}

// ── 마무리 ────────────────────────────────────────────────

export function synthTalk(ev) {
  return [["coord", `${ev.절수}개 절을 한 편으로 엮었습니다 — ${num(ev.보고서자수)}자예요`],
          ["coord", "참고로 저는 원문을 직접 안 봤어요. 여러분이 쓴 원고만 받아서 묶었죠"]];
}

export function evalTalk(m = {}) {
  const net = m.그물 || {};
  const pct = Math.round((m.근거율 || 0) * 100);
  return [["coord", `채점해 볼까요. 근거가 달린 문장 ${pct}%, 지어낸 출처 ${m.허위인용 ?? 0}곳`],
          ["coord", net.통과 ? "읽어 볼 만한 보고서라는 판정이에요"
                             : `아쉽게도 탈락이에요 — ${(net.사유 || []).join(" · ")}`]];
}

export const endLine = seed => pick(seed, ["다들 수고 많았어요. 보고서 띄워 드릴게요",
                                           "수고했어요! 보고서 펼쳐 드릴게요"]);
