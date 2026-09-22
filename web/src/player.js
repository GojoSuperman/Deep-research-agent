// 녹화 재생 — 계획서 5.5절.
//
// ts 는 순서 판정에만 쓰고 시간은 연출이 정한다. 이벤트 간격은 중앙값 0.18초인데
// 연출은 초 단위라 ts 를 그대로 재생하면 끝없이 밀린다.
// 큐를 **에이전트별로** 나눠 조사관끼리는 동시에 흐르게 하고, 전역 이벤트만 배리어로 모두를 기다린다.
// 전역 큐 하나로 직렬화하면 팬아웃이 화면에서 사라진다.
import { ZONES, DESKS } from "./config.js";

// 이벤트별 연출 지속시간 (초)
export const DUR = {
  "run.start": 1.3,
  "plan.done": 3.0,
  "dispatch": 1.1,
  "researcher.start": 0.8,
  "researcher.read": 2.8,
  "researcher.read.skip": 1.6,   // 관련 없음 — 짧게
  "researcher.fix": 2.3,
  "researcher.done": 2.1,
  "review": 2.3,
  "synthesize": 2.3,
  "evaluate": 2.8,
  "run.end": 1.0,
};

const GLOBAL = new Set(["run.start", "plan.done", "dispatch", "review", "synthesize",
                        "evaluate", "run.end"]);

const zoneSpot = name => ZONES.find(z => z.name === name);

/**
 * 녹화 한 편을 재생 가능한 형태로 푼다.
 *  - 절 제목 → 조사관 인덱스 (계획서 5.7: 인덱스가 ID다. 제목은 표시용)
 *  - 전역 큐와 에이전트별 큐
 */
export function load(run) {
  const plan = run.events.find(e => e.type === "plan.done");
  const titles = (plan?.목차 || []).map(s => s.절);
  const index = new Map();
  titles.forEach((t, i) => {
    if (index.has(t)) console.warn(`절 제목이 겹친다: ${t} — 먼저 나온 것에 붙인다`);
    else index.set(t, i);
  });

  // [{ kind:"global"|"agent", who, ev }] 를 ts 순서대로
  const steps = run.events.map(ev => {
    if (GLOBAL.has(ev.type)) return { kind: "global", ev };
    const i = index.get(ev.절);
    return { kind: "agent", who: i == null ? 0 : i, ev };
  });

  return { run, titles, steps, plan };
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
  const { steps, titles } = loaded;
  let cursor = 0;            // 다음에 꺼낼 step
  const lanes = [[], [], [], []];   // 조사관별 대기열
  let barrier = null;        // 실행 중인 전역 단계
  const busy = [null, null, null, null];   // 조사관별 실행 중 단계
  let done = false;

  const state = {
    actors: DESKS.map((d, i) => ({
      role: `r${i + 1}`, col: d.col, row: d.row, home: { ...d },
      state: "idle", target: null, t: 0, dur: 0, say: "",
    })),
    coord: { role: "coord", col: 2, row: 1, state: "idle", say: "" },
    reads: {},               // 서고 이름 → 읽은 횟수
    phase: "",
    metrics: null,
    report: "",
    elapsed: 0,
  };
  state.actors.forEach(a => { a.from = { col: a.col, row: a.row }; });

  const lanesIdle = () => busy.every(b => b === null) && lanes.every(l => l.length === 0);

  /** 다음 step 들을 큐에 채운다. 전역을 만나면 멈춘다(배리어). */
  function fill() {
    while (cursor < steps.length) {
      const s = steps[cursor];
      if (s.kind === "global") {
        if (!lanesIdle()) return;          // 앞의 조사관 연출이 끝나길 기다린다
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
        state.phase = "질문을 받았다";
        state.coord.state = "point";
        break;
      case "plan.done":
        state.phase = `목차 ${ev.목차.length}절`;
        state.coord.state = "point";
        break;
      case "dispatch":
        state.phase = `배치 — ${ev.인원}명`;
        state.coord.state = "enough";
        break;
      case "researcher.start":
        if (a) { a.state = "idle"; a.say = ev.역할; }
        break;
      case "researcher.read": {
        if (!a) break;
        const z = zoneSpot(ev.서고);
        if (z) moveTo(a, z.col, z.row + 1);   // 기계 앞에 선다
        a.state = ev.관련 ? "reading" : "skip";
        a.say = ev.문서;
        if (ev.관련) state.reads[ev.서고] = (state.reads[ev.서고] || 0) + 1;
        break;
      }
      case "researcher.fix":
        if (a) { a.state = "alarm"; a.say = "허위 인용 — 다시 쓴다"; }
        break;
      case "researcher.done":
        if (a) {
          moveTo(a, a.home.col, a.home.row);
          a.state = ev.충분 ? "done" : "short";
          a.say = ev.충분 ? `${ev.인용}곳 인용` : ev.부족 || "부족";
          if (ev.인용 === 0) a.state = "alarm";
        }
        break;
      case "review":
        state.phase = ev.빈칸?.length ? `점검 — 빈칸 ${ev.빈칸.length}` : "점검 — 통과";
        state.coord.state = ev.빈칸?.length ? "short" : "enough";
        break;
      case "synthesize":
        state.phase = `종합 — ${ev.보고서자수}자`;
        state.coord.state = "point";
        break;
      case "evaluate":
        state.phase = "계기판";
        state.metrics = ev.metrics;
        state.coord.state = ev.metrics?.그물?.통과 ? "done" : "alarm";
        break;
      case "run.end":
        state.phase = "끝";
        state.coord.state = "idle";
        break;
    }
  }

  function moveTo(a, col, row) {
    a.from = { col: a.col, row: a.row };
    a.target = { col, row };
    a.t = 0;
  }

  /** dt 초만큼 굴린다. 끝났으면 true */
  function tick(dt) {
    if (done) return true;
    state.elapsed += dt;

    // 배리어 진행
    if (barrier) {
      barrier.t += dt;
      if (barrier.t >= barrier.dur) barrier = null;
    }

    // 조사관별 진행
    for (let i = 0; i < 4; i++) {
      const a = state.actors[i];
      if (busy[i]) {
        busy[i].t += dt;
        // 이동 보간 — 연출 시간의 앞 60% 동안 걷는다
        if (a.target) {
          const k = Math.min(1, (busy[i].t / busy[i].dur) / 0.6);
          const e = k * k * (3 - 2 * k);         // smoothstep
          a.col = a.from.col + (a.target.col - a.from.col) * e;
          a.row = a.from.row + (a.target.row - a.from.row) * e;
          if (k >= 1) a.target = null;
        }
        if (busy[i].t >= busy[i].dur) busy[i] = null;
      }
      if (!busy[i] && !barrier && lanes[i].length) {
        const ev = lanes[i].shift();
        busy[i] = { ev, t: 0, dur: durOf(ev) };
        begin(ev, i);
      }
    }

    fill();
    if (cursor >= steps.length && lanesIdle() && !barrier) done = true;
    return done;
  }

  return {
    state, tick, titles,
    get done() { return done; },
    get progress() { return steps.length ? cursor / steps.length : 1; },
  };
}
