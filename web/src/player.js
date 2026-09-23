// 녹화 재생 — 계획서 5.5절.
//
// ts 는 순서 판정에만 쓰고 시간은 연출이 정한다. 이벤트 간격은 중앙값 0.18초인데
// 연출은 초 단위라 ts 를 그대로 재생하면 끝없이 밀린다.
// 큐를 **에이전트별로** 나눠 조사관끼리는 동시에 흐르게 하고, 전역 이벤트만 배리어로 모두를 기다린다.
// 전역 큐 하나로 직렬화하면 팬아웃이 화면에서 사라진다.
import { ZONES, DESKS, MEETING, COORD_SEAT, COORD_HOME, BLOCKED, GRID } from "./config.js";
import { name } from "./actors.js";
import { docKo } from "./docs.js";

// ── 길찾기 ────────────────────────────────────────────────
// 소품이 덮은 칸(BLOCKED, 실측)을 피해 돌아간다. 직선으로 가면 탁자와 책상을 관통한다.
const wall = new Set(BLOCKED.map(([c, r]) => `${c},${r}`));
const free = (c, r) => c >= 0 && r >= 0 && c < GRID.cols && r < GRID.rows && !wall.has(`${c},${r}`);

/** 너비 우선 탐색 — 격자가 12×7 이라 이 정도로 충분하다. 못 찾으면 직선으로 간다. */
function route(from, to) {
  const key = (c, r) => `${c},${r}`;
  const start = key(Math.round(from.col), Math.round(from.row));
  const goal = key(to.col, to.row);
  if (start === goal) return [to];
  const prev = new Map([[start, null]]);
  const q = [[Math.round(from.col), Math.round(from.row)]];
  while (q.length) {
    const [c, r] = q.shift();
    for (const [dc, dr] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nc = c + dc, nr = r + dr, k = key(nc, nr);
      if (prev.has(k)) continue;
      // 목적지는 막힌 칸이어도 들어간다 (책상 앞자리처럼 가장자리에 서는 경우)
      if (!free(nc, nr) && k !== goal) continue;
      prev.set(k, key(c, r));
      if (k === goal) {
        const path = [];
        for (let at = k; at && at !== start; at = prev.get(at)) {
          const [pc, pr] = at.split(",").map(Number);
          path.unshift({ col: pc, row: pr });
        }
        return path;
      }
      q.push([nc, nr]);
    }
  }
  return [to];   // 길이 없으면 곧장 (갇히는 것보다 낫다)
}

// 이벤트별 연출 지속시간 (초)
export const DUR = {
  "run.start": 2.4,     // 회의 탁자로 모이는 시간
  "plan.done": 5.4,     // 소장이 목차를 설명하는 시간 — 짧으면 회의로 안 보인다
  "dispatch": 2.3,
  "researcher.start": 2.6,   // 각자 무엇을 맡았는지 읽을 시간
  "researcher.read": 2.8,
  "researcher.read.skip": 1.6,   // 관련 없음 — 짧게
  "researcher.fix": 2.3,
  "researcher.done": 2.1,
  "review": 4.2,        // 다시 모여 보고하는 시간
  "synthesize": 2.3,
  "evaluate": 2.8,
  "run.end": 1.0,
};

const GLOBAL = new Set(["run.start", "plan.done", "dispatch", "review", "synthesize",
                        "evaluate", "run.end"]);

const zoneSpot = name => ZONES.find(z => z.name === name);

const num = n => (n ?? 0).toLocaleString("ko-KR");

// 말풍선 타자 — 초당 글자 수와, 한 줄을 다 친 뒤 머무는 시간
const CPS = 26;
const HOLD = 0.75;

/** 소장이 회의에서 할 말. 목차를 한 줄씩 읽어 준다. */
export function planLines(ev, cfg = {}) {
  const 목차 = ev.목차 || [];
  const 배정 = cfg.배정 !== false, 역할 = cfg.역할 !== false;
  // 배정을 끄면 소장이 시작 문서를 고르지 않는다 — 목록 앞에서부터 기계적으로 집힌다.
  // 그런데도 "이 서고로 가세요"라고 말하면 거짓말이 된다 (실측: 절 주제와 서고가 따로 논다).
  if (!배정) {
    return [
      `질문을 ${목차.length}갈래로 나눴습니다`,
      ...목차.map((s, i) => `${name(i)} — 「${s.절}」`),
      "이번엔 시작 문서를 정해 주지 않습니다",
      "목록에 있는 대로 집어 가세요 — 어디에 닿을지는 모릅니다",
    ];
  }
  // 한 절에 한 줄. 이름을 앞에 불러 주면 흩어진 뒤에도 누가 무엇을 맡았는지 따라갈 수 있다.
  // 조사(은/는)를 붙이지 않는 어순으로 쓴다 — 이름마다 받침이 달라 틀리기 쉽다.
  return [
    `질문을 ${목차.length}갈래로 나눴습니다`,
    ...목차.map((s, i) => `${name(i)} — 「${s.절}」 (${s.서고} 서고)`),
    역할 ? "맡은 눈으로 보세요 — 큰그림·비교·원인·시간순"
         : "이번엔 따로 역할을 주지 않습니다. 각자 알아서 보세요",
    "서로 무엇을 읽는지 모른 채 각자 다녀옵니다",
  ];
}



/**
 * 자막 — 의미 이벤트 한 개를 방문자의 말로 옮긴다 (계획서 4.2 번역 규칙의 말 버전).
 * 백엔드는 이 문장을 모른다. 여기서만 만든다.
 */
export function caption(ev) {
  switch (ev.type) {
    case "run.start": {
      const c = ev.설정 || {};
      const off = [c.배정 === false && "시작 문서 배정", c.역할 === false && "조사관 역할",
                   c.재위임 === false && "빈 절 재위임"].filter(Boolean);
      return "질문을 받았습니다. 소장이 서고 52건의 목록을 훑습니다."
        + (off.length ? ` (이번 실험은 ${off.join("·")}을 껐습니다)` : "");
    }
    case "plan.done":
      return `소장이 질문을 ${ev.목차.length}개의 절로 나눴습니다.`
        + (ev.목차?.[0]?.역할 && ev.목차[0].역할 !== "담당"
           ? " 절마다 역할과 시작 문서를 붙입니다." : "");
    case "dispatch":
      return `조사관 ${ev.인원}명이 동시에 출발합니다 — 서로 무엇을 읽는지 모릅니다.`;
    case "researcher.start":
      return `「${ev.절}」 담당이 ${docKo(ev.시작문서)}부터 시작합니다.`
        + (ev.피하기?.length ? "" : " (남의 문서를 피하지 않습니다)");
    case "researcher.read":
      return ev.관련
        ? `${docKo(ev.문서)} ${num(ev.원문자수)}자를 읽고 ${num(ev.메모자수)}자 메모만 들고 나왔습니다.`
        : `${docKo(ev.문서)} — 이 절과 관련이 없어 빈손으로 나왔습니다.`;
    case "researcher.fix":
      return `읽지 않은 문서를 출처로 적었습니다 (${ev.허위.map(docKo).join(", ")}) — 다시 쓰게 합니다.`;
    case "researcher.done":
      return ev.인용
        ? `「${ev.절}」 원고 ${num(ev.자수)}자를 썼습니다 · 출처 ${ev.인용}곳.`
        : `「${ev.절}」은 근거를 한 곳도 못 찾았습니다.`;
    case "review":
      if (!ev.빈칸?.length) return "점검 통과 — 근거 없는 절이 없습니다.";
      if (!ev.종료) return `「${ev.빈칸.join("」 「")}」에 근거가 없습니다 — 서고로 되돌려 보냅니다.`;
      if (ev.종료 === "재위임 끔")
        return `「${ev.빈칸.join("」 「")}」이 비었지만 되돌려 보내지 않습니다 — 재위임을 끈 실험입니다.`;
      return `「${ev.빈칸.join("」 「")}」은 ${ev.종료} — 빈 채로 종합합니다.`;
    case "synthesize":
      return `소장이 절들을 모아 보고서 ${num(ev.보고서자수)}자를 썼습니다 — 원문은 보지 않고 앞머리만 봅니다.`;
    case "evaluate":
      return "LLM이 아니라 프로그램이 보고서를 서고와 대조합니다 — 지어낸 출처가 없는지, 근거가 정말 그 문서에 있는지.";
    case "run.end":
      return "끝났습니다.";
    default:
      return "";
  }
}

/**
 * 녹화 한 편을 재생 가능한 형태로 푼다. (라이브는 이걸 거치지 않고 push() 로 한 개씩 넣는다)
 */
export function load(run) {
  return { run, events: run.events, plan: run.events.find(e => e.type === "plan.done") };
}

/** 한 단계의 지속시간 */
function durOf(ev) {
  if (ev.type === "researcher.read" && ev.관련 === false) return DUR["researcher.read.skip"];
  return DUR[ev.type] ?? 1.0;
}

/**
 * 재생기 — tick(dt) 를 받아 상태를 굴린다.
 * 상태는 renderer 가 그대로 쓸 수 있는 모양이다.
 */
export function createPlayer(loaded, onEvent) {
  const steps = [];          // [{ kind:"global"|"agent", who, ev }] — 라이브에서는 자란다
  const titles = [];
  const index = new Map();   // 절 제목 → 조사관 인덱스 (계획서 5.7: 인덱스가 ID다)
  let streamEnded = false;   // 재생은 곧바로, 라이브는 스트림이 닫힐 때 true
  let cursor = 0;            // 다음에 꺼낼 step
  const lanes = [[], [], [], []];   // 조사관별 대기열
  let barrier = null;        // 실행 중인 전역 단계
  let convo = [];            // 남은 대사 [[누구, 할 말], …]
  let homeTimer = null;      // 소장의 마지막 말 뒤 귀가까지 남은 시간(초). -1 = 말이 끝나길 기다림
  let speaker = null;        // 지금 말하는 사람
  const lastDone = {};       // 조사관 인덱스 → 마지막 researcher.done 이벤트 (보고 대사에 쓴다)
  const busy = [null, null, null, null];   // 조사관별 실행 중 단계
  let done = false;

  /** 목차가 오면 그때 절↔조사관 대응표를 만든다. 라이브는 plan.done 전엔 알 수 없다. */
  function setTitles(list) {
    titles.length = 0; index.clear();
    list.forEach((t, i) => {
      titles.push(t);
      if (index.has(t)) console.warn(`절 제목이 겹친다: ${t} — 먼저 나온 것에 붙인다`);
      else index.set(t, i);
    });
  }

  /** 의미 이벤트 한 개를 큐에 넣는다. 재생·라이브의 유일한 입구다. */
  function push(ev) {
    if (ev.type === "plan.done") setTitles((ev.목차 || []).map(s => s.절));
    if (GLOBAL.has(ev.type)) { steps.push({ kind: "global", ev }); return; }
    const i = index.get(ev.절);
    steps.push({ kind: "agent", who: i == null ? 0 : Math.min(i, lanes.length - 1), ev });
  }

  /** 더 올 이벤트가 없다고 알린다. 이걸 받아야 done 이 될 수 있다. */
  function endStream() { streamEnded = true; }

  const state = {
    actors: DESKS.map((d, i) => ({
      role: `r${i + 1}`, col: d.col, row: d.row, home: { ...d },
      seat: { ...MEETING[i] },
      state: "idle", target: null, path: [], t: 0, dur: 0,
      say: "", sayFull: "", sayT: 0, lines: [],
      walkT: 0, walkDur: 1,
    })),
    coord: { role: "coord", col: COORD_HOME.col, row: COORD_HOME.row,
             home: { ...COORD_HOME }, seat: { ...COORD_SEAT },
             state: "idle", say: "", sayFull: "", sayT: 0, lines: [],
             target: null, path: [], walkT: 0, walkDur: 1 },
    // 카메라 목표 — 연출이 "어디를 보여 줄까"만 정하고, 움직이는 일은 view.js 가 한다.
    // null 이면 방 전체. 회의 탁자는 (0,2)(1,2)(1,3)(2,3) 네 칸이라 그 한가운데를 본다.
    focus: null,
    settings: {},            // run.start 가 알려 준 이번 실험 설정
    node: null,              // 지금 돌고 있는 6노드 중 하나 (화면 왼쪽 파이프라인 표시기용)
    round: 1,                // 몇 바퀴째인가 (재위임 루프)
    sentBack: false,         // 점검이 되돌려 보냈나
    finished: false,         // 귀가까지 끝났나 — 화면이 보고서를 띄우는 신호
    reads: {},               // 서고 이름 → 읽은 횟수
    phase: "",
    metrics: null,
    report: "",
    elapsed: 0,
  };
  state.actors.forEach(a => { a.from = { col: a.col, row: a.row }; });
  state.coord.from = { col: state.coord.col, row: state.coord.row };

  const everyone = () => [...state.actors, state.coord];

  /** 한 줄을 타자로 친다 */
  function setSay(a, text) {
    a.sayFull = text || "";
    a.say = "";
    a.sayT = 0;
  }
  /**
   * 대화 — [[누구, 할 말], …] 을 **한 사람씩 차례로** 친다.
   * 각자 자기 큐를 돌리면 넷이 동시에 떠들어서 회의로 안 보인다.
   * 누구: 조사관 인덱스(0~3) 또는 "coord".
   */
  function talk(list) {
    convo = list.filter(([, t]) => t);
    speaker = null;
    nextLine();
  }

  function nextLine() {
    const item = convo.shift();
    if (!item) { speaker = null; return; }
    const [who, text] = item;
    const a = who === "coord" ? state.coord : state.actors[who];
    everyone().forEach(x => { if (x !== a) setSay(x, ""); });   // 말하는 사람만 말풍선
    setSay(a, text);
    speaker = a;
  }

  /** 아직 할 말이 남았나 — 배리어가 이걸 기다린다 */
  const talking = () => !!speaker || convo.length > 0;

  /** 타자 진행 */
  function type(a, dt) {
    if (!a.sayFull) return;
    a.sayT += dt;
    a.say = a.sayFull.slice(0, Math.floor(a.sayT * CPS));
  }

  /** 지금 말하는 사람이 다 쳤고 잠깐 머물렀으면 다음 차례로 */
  function turn() {
    if (!speaker) return;
    const done = speaker.sayT >= speaker.sayFull.length / CPS + HOLD;
    if (done) nextLine();
  }
  /** 회의 탁자로 모은다 — 소장은 상석, 조사관은 양옆. */
  const gather = dur => everyone().forEach(a => moveTo(a, a.seat.col, a.seat.row, dur));

  const walking = () => everyone().some(a => a.target);
  const lanesIdle = () => busy.every(b => b === null) && lanes.every(l => l.length === 0);

  /** 다음 step 들을 큐에 채운다. 전역을 만나면 멈춘다(배리어). */
  function fill() {
    // 돌고 있는 전역 연출이 끝나기 전에는 다음 전역을 시작하지 않는다.
    // 이 줄이 없으면 plan.done 이 뜨자마자 dispatch 가 배리어를 덮어써서,
    // 소장이 목차를 설명하는 시간이 통째로 사라진다 (회의가 눈 깜짝할 새 끝났다).
    if (barrier) return;
    while (cursor < steps.length) {
      const s = steps[cursor];
      if (s.kind === "global") {
        if (!lanesIdle() || walking()) return;   // 앞의 연출과 걸음이 끝나길 기다린다
        barrier = { ev: s.ev, t: 0, dur: durOf(s.ev) };
        begin(s.ev, null);
        cursor++;
        return;
      }
      lanes[s.who].push(s.ev);
      cursor++;
    }
  }

  /** 연출 시작 — 상태를 바꾼다 */
  function begin(ev, who) {
    onEvent?.(ev);
    const a = who == null ? null : state.actors[who];
    switch (ev.type) {
      case "run.start":
        state.node = "start";
        state.settings = ev.설정 || {};
        state.phase = "질문을 받았다";
        state.coord.state = "point";
        gather(DUR["run.start"] * 0.8);          // 다 같이 회의 탁자로
        state.focus = { col: 1, row: 2.5, span: 4.6 };
        state.actors.forEach(x => { x.state = "idle"; x.say = ""; });
        break;
      case "plan.done":
        state.node = "plan";
        state.phase = `목차 ${ev.목차.length}절`;
        state.coord.state = "point";
        talk(planLines(ev, state.settings).map(t => ["coord", t]));
        break;
      case "dispatch":
        state.node = "dispatch";
        state.phase = `배치 — ${ev.인원}명`;
        state.round = ev.바퀴 || state.round;
        state.sentBack = false;
        state.coord.state = "enough";
        setSay(state.coord, "");
        // 조사관은 자기 책상으로 흩어지고, 소장은 자기 자리로 돌아간다
        // 흩어지고 나면 카메라가 조사관들을 따라다닌다 (책상에 모이면 당기고, 서고로 흩어지면 물러선다)
        state.focus = { follow: true };
        state.actors.forEach(x => moveTo(x, x.home.col, x.home.row, DUR["dispatch"] * 0.8));
        moveTo(state.coord, state.coord.home.col, state.coord.home.row, DUR["dispatch"] * 0.8);
        break;
      case "researcher.start":
        state.node = "research";
        if (a) {
          a.state = "idle";
          const 역할 = ev.역할 && ev.역할 !== "담당" ? `${ev.역할} · ` : "";
          // 배정이 꺼지면 시작 문서는 소장이 고른 것이 아니다. 말도 그렇게 해야 한다.
          setSay(a, state.settings?.배정 === false
            ? `목록에서 집었습니다 — ${docKo(ev.시작문서)}`
            : `${역할}${docKo(ev.시작문서)}부터 봅니다`);
        }
        break;
      case "researcher.read": {
        state.node = "research";
        if (!a) break;
        const z = zoneSpot(ev.서고);
        if (z) moveTo(a, z.col, z.row + 1, durOf(ev) * 0.55);   // 기계 앞에 선다
        a.state = ev.관련 ? "reading" : "skip";
        setSay(a, ev.관련 ? `${docKo(ev.문서)} 읽는 중` : `${docKo(ev.문서)} — 관련 없음`);
        if (ev.관련) state.reads[ev.서고] = (state.reads[ev.서고] || 0) + 1;
        break;
      }
      case "researcher.fix":
        if (a) { a.state = "alarm"; setSay(a, "안 읽은 문서를 인용했습니다 — 다시 씁니다"); }
        break;
      case "researcher.done":
        if (who != null) lastDone[who] = ev;
        if (a) {
          moveTo(a, a.home.col, a.home.row, DUR["researcher.done"] * 0.55);
          a.state = ev.충분 ? "done" : "short";
          setSay(a, ev.충분 ? `출처 ${ev.인용}곳` : ev.부족 || "부족합니다");
          if (ev.인용 === 0) a.state = "alarm";
        }
        break;
      case "review": {
        state.node = "review";
        state.phase = ev.빈칸?.length ? `점검 — 빈칸 ${ev.빈칸.length}` : "점검 — 통과";
        state.coord.state = ev.빈칸?.length ? "short" : "enough";
        state.sentBack = !!(ev.빈칸?.length && !ev.종료);
        gather(DUR["review"] * 0.75);            // 탁자에 다시 모여 소장에게 보고한다
        state.focus = { col: 1, row: 2.5, span: 4.6 };
        // 조사관이 한 사람씩 보고하고, 소장이 마지막에 정리한다
        const 빈칸 = new Set(ev.빈칸 || []);
        const lines = Object.keys(lastDone).map(Number).sort().map(i => {
          const d = lastDone[i];
          return [i, d.인용
            ? `「${d.절}」 ${num(d.자수)}자 · 출처 ${d.인용}곳 찾았습니다`
            : `「${d.절}」 근거를 못 찾았습니다`];
        });
        // 종료 사유를 봐야 한다. 빈칸이 있어도 바퀴를 다 썼거나 재위임을 끈 실험이면
        // **되돌려 보내지 않는다** — 그런데도 "다시 다녀오세요"라고 말하면 거짓말이 된다.
        const 빈칸목록 = [...빈칸].map(t => `「${t}」`).join(" ");
        if (!ev.빈칸?.length) {
          lines.push(["coord", "모든 절에 근거가 붙었습니다. 제가 정리하겠습니다"]);
        } else if (!ev.종료) {
          lines.push(["coord", `${빈칸목록} 가 비었습니다`]);
          lines.push(["coord", "다시 다녀와 주세요"]);
        } else if (ev.종료 === "재위임 끔") {
          lines.push(["coord", `${빈칸목록} 가 비었습니다`]);
          lines.push(["coord", "이번엔 다시 보내지 않는 실험입니다. 이대로 정리합니다"]);
        } else {
          lines.push(["coord", `${빈칸목록} 는 끝내 못 채웠습니다`]);
          lines.push(["coord", `${ev.종료} — 이대로 정리하겠습니다`]);
        }
        talk(lines);
        break;
      }
      case "synthesize":
        state.node = "synth";
        state.phase = `종합 — ${ev.보고서자수}자`;
        state.coord.state = "point";
        talk([["coord", `${ev.절수}개 절을 한 편으로 묶었습니다 — ${num(ev.보고서자수)}자`],
              ["coord", "저는 원문을 안 봤습니다. 각자 요약만 받았습니다"]]);
        break;
      case "evaluate": {
        state.node = "evaluate";
        state.phase = "계기판";
        state.metrics = ev.metrics;
        const m = ev.metrics || {}, net = m.그물 || {};
        state.coord.state = net.통과 ? "done" : "alarm";
        talk([
          ["coord", `근거가 달린 문장 ${Math.round((m.근거율 || 0) * 100)}% · 지어낸 출처 ${m.허위인용 ?? 0}곳`],
          ["coord", net.통과 ? "읽어 볼 가치: 통과입니다" : `읽어 볼 가치: 탈락 — ${(net.사유 || []).join(" · ")}`],
        ]);
        break;
      }
      case "run.end":
        state.node = "end";
        state.phase = "끝";
        state.coord.state = "idle";
        talk([["coord", "수고하셨습니다. 보고서를 띄우겠습니다"]]);
        homeTimer = -1;        // 말이 끝나면 1.5초 뒤 각자 자리로
        break;
    }
  }

  /** 목적지가 소수 좌표일 때, 길찾기는 가까운 **빈 칸**까지만 하고 마지막 한 걸음을 붙인다. */
  function landing(col, row) {
    let best = null, bd = Infinity;
    for (const [c, r] of [[Math.round(col), Math.round(row)], [Math.floor(col), Math.floor(row)],
                          [Math.ceil(col), Math.floor(row)], [Math.floor(col), Math.ceil(row)],
                          [Math.ceil(col), Math.ceil(row)]]) {
      if (!free(c, r)) continue;
      const d = (c - col) ** 2 + (r - row) ** 2;
      if (d < bd) { bd = d; best = { col: c, row: r }; }
    }
    return best || { col: Math.round(col), row: Math.round(row) };
  }

  function moveTo(a, col, row, dur = 1.2) {
    if (a.col === col && a.row === row && !a.target) return;
    const near = landing(col, row);
    const path = route(a, near);
    if (near.col !== col || near.row !== row) path.push({ col, row });   // 마지막 한 걸음
    if (!path.length) { a.target = null; return; }
    // 경로 전체를 한 줄(꺾은선)로 — 칸마다 따로 걸으면 칸 경계에서 멈칫한다
    const pts = [{ col: a.col, row: a.row }, ...path];
    const cum = [0];
    for (let i = 1; i < pts.length; i++)
      cum.push(cum[i - 1] + Math.hypot(pts[i].col - pts[i - 1].col, pts[i].row - pts[i - 1].row));
    a.walk = { pts, cum, len: cum[cum.length - 1],
               // 남은 칸 수로 시간을 정한다 — 멀리 가는 사람이 더 오래 걷는다 (칸당 최소 0.18초)
               dur: Math.max(0.18, dur / path.length) * path.length };
    a.target = path[path.length - 1];
    a.path = [];
    a.walkT = 0;
  }

  /** 걸은 거리 — 짧게 가속, 등속, 짧게 감속 (사다리꼴 속도).
   *  경로 전체에 한 번만 건다. 칸마다 걸면 칸 사이에서 속도가 0으로 떨어진다. */
  function walked(t, T, L) {
    const ta = Math.min(0.25, T / 3);
    const v = L / (T - ta);
    if (t <= ta) return v * t * t / (2 * ta);
    if (t >= T - ta) return L - v * (T - t) ** 2 / (2 * ta);
    return v * (t - ta / 2);
  }

  /** 걷기는 이벤트와 무관하게 흐른다.
   *  전역 이벤트(모임·흩어짐) 때는 조사관이 처리 중인 이벤트가 없어서,
   *  걸음을 이벤트 타이머에 매어 두면 그 자리에 멈춰 선다. */
  function walk(a, dt) {
    if (!a.target) return;
    const w = a.walk;
    a.walkT = Math.min(a.walkT + dt, w.dur);
    const d = walked(a.walkT, w.dur, w.len);
    let i = 1;
    while (i < w.cum.length - 1 && w.cum[i] < d) i++;
    const seg = w.cum[i] - w.cum[i - 1];
    const k = seg > 0 ? (d - w.cum[i - 1]) / seg : 1;
    a.col = w.pts[i - 1].col + (w.pts[i].col - w.pts[i - 1].col) * k;
    a.row = w.pts[i - 1].row + (w.pts[i].row - w.pts[i - 1].row) * k;
    if (a.walkT >= w.dur) {
      a.col = a.target.col; a.row = a.target.row;
      a.from = { col: a.col, row: a.row };
      a.target = null;
      a.walk = null;
    }
  }

  /** dt 초만큼 굴린다. 끝났으면 true */
  function tick(dt) {
    if (done) return true;
    state.elapsed += dt;

    // 배리어 진행
    turn();                                   // 대사 차례 넘기기

    // 끝난 뒤 — 소장의 마지막 말이 끝나고 1.5초 뒤에 각자 자리로 돌아간다
    if (homeTimer === -1 && !talking()) homeTimer = 1.5;
    else if (homeTimer > 0) {
      homeTimer -= dt;
      if (homeTimer <= 0) {
        homeTimer = null;
        state.actors.forEach(x => { moveTo(x, x.home.col, x.home.row, 2.0); x.state = "idle"; });
        moveTo(state.coord, state.coord.home.col, state.coord.home.row, 2.0);
        everyone().forEach(x => setSay(x, ""));
        state.focus = null;                   // 방 전체를 다시 보여 준다
        state.finished = true;                // 화면이 이걸 보고 보고서를 띄운다
      }
    }
    if (barrier) {
      barrier.t += dt;
      // 하던 말이 끝나기 전에는 다음 단계로 넘어가지 않는다
      if (barrier.t >= barrier.dur && !talking()) barrier = null;
    }

    // 걷기와 말풍선 타자 — 누구든 매 프레임 진행한다
    everyone().forEach(a => { walk(a, dt); type(a, dt); });

    // 조사관별 진행
    for (let i = 0; i < 4; i++) {
      if (busy[i]) {
        busy[i].t += dt;
        if (busy[i].t >= busy[i].dur) busy[i] = null;
      }
      if (!busy[i] && !barrier && lanes[i].length) {
        const ev = lanes[i].shift();
        busy[i] = { ev, t: 0, dur: durOf(ev) };
        begin(ev, i);
      }
    }

    fill();
    // 귀가가 남았으면 아직 끝이 아니다 (homeTimer 가 null 이 되어야 한다)
    if (streamEnded && cursor >= steps.length && lanesIdle() && !barrier
        && !walking() && !talking() && homeTimer === null) done = true;
    return done;
  }

  // 녹화는 전부 부어 넣고 곧바로 닫는다 — 아래 push/endStream 이 유일한 차이다.
  if (loaded) { (loaded.events || loaded.run?.events || []).forEach(push); endStream(); }

  return {
    state, tick, titles, push, endStream,
    get done() { return done; },
    get waiting() { return !streamEnded && cursor >= steps.length; },
    get progress() { return steps.length ? cursor / steps.length : 1; },
  };
}
