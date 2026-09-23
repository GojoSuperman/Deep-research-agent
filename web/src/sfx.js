// 말풍선 타자 효과음 — 소리만 아는 모듈. 화면도 재생도 모른다.
//
// 음원 파일을 두지 않고 오실레이터로 만든다. 배포 용량이 0 만큼 늘고,
// ASSET_V 캐시 관리 대상도 늘지 않는다 (/assets/ 는 1년 immutable 이다).
//
// AudioContext 는 **사용자가 무언가를 누른 뒤에만** 만든다.
// 화면을 열어만 둔 방문자에게는 컨텍스트조차 생기지 않는다 (자동재생 정책).

const KEY = "sfx-muted";

// 배역별 목소리 — 소장은 낮게, 조사관 넷은 화음이 되는 음으로 올린다.
// 조사관 넷이 동시에 타자를 쳐도(각자 큐가 따로 돈다) 불협이 되지 않는다.
const VOICE = {
  coord: 220,   // A3
  r1: 330,      // E4
  r2: 370,      // F#4
  r3: 415,      // G#4
  r4: 466,      // A#4
};

let ctx = null;          // 첫 클릭 전에는 null
let master = null;
let muted = false;
let blips = 0;           // 실측용 — 재생 한 편에 몇 번 울렸나
let live = 0, peak = 0;  // 동시에 울린 최대 개수

try { muted = localStorage.getItem(KEY) === "1"; } catch { /* 사생활 보호 창 */ }

/** 소리가 켜져 있나 */
export const isMuted = () => muted;

/** 켜고 끄기 — 기억해 둔다 */
export function setMuted(v) {
  muted = !!v;
  try { localStorage.setItem(KEY, muted ? "1" : "0"); } catch { /* 무시 */ }
  return muted;
}

/**
 * 사용자 제스처 안에서 부른다 (▶ 재생 · 실행).
 * 여기서만 AudioContext 가 생긴다. 이미 있으면 깨우기만 한다.
 */
export function unlock() {
  if (muted) return;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;                       // 지원 안 하면 조용히 없던 일로
  if (!ctx) {
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = 0.06;            // 작게 — 말풍선은 30초에 수백 번 울린다
    master.connect(ctx.destination);
  }
  if (ctx.state === "suspended") ctx.resume();
}

/**
 * 한 글자 소리 — 40ms 짜리 「쫍」.
 * role 은 "coord" 또는 "r1"~"r4". 모르는 이름이면 조용히 넘어간다.
 */
export function blip(role) {
  if (muted || !ctx || ctx.state !== "running") return;
  const f = VOICE[role];
  if (!f) return;

  const t = ctx.currentTime;
  const osc = ctx.createOscillator();
  const g = ctx.createGain();
  osc.type = "square";
  // 살짝 떨어지는 음 — 같은 높이로 이으면 기계음처럼 들린다
  osc.frequency.setValueAtTime(f, t);
  osc.frequency.exponentialRampToValueAtTime(f * 0.88, t + 0.04);
  // 엔벨로프 — 딱 끊으면 「딱」 소리(클릭 노이즈)가 난다
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(1, t + 0.005);
  g.gain.exponentialRampToValueAtTime(0.0001, t + 0.04);
  osc.connect(g); g.connect(master);
  osc.start(t);
  osc.stop(t + 0.05);

  blips++; live++; peak = Math.max(peak, live);
  osc.onended = () => { live--; osc.disconnect(); g.disconnect(); };
}

/** 실측용 계수기 — 재생 한 편당 몇 번 울렸는지 본다 */
export const stats = () => ({ blips, peak });
export function resetStats() { blips = 0; peak = 0; }
