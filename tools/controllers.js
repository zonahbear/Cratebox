// =====================================================================================
//  Controllers: Pioneer DJ / AlphaTheta profiles, a table-driven MIDI engine, MIDI learn
// =====================================================================================
// A mapping entry is [status, data1, action, deck, lsb]: status/data1 of the message (note-offs
// are treated as their note-on), the Cratebox action, the deck (0/1, -1 = global) and, for 14-bit
// controls, the data1 of the LSB message (0 if none).
// Actions: play playCue cue start sync syncOn range touch jogTop jogSide jogSearch tempo
//   loopIn loopOut reloop reloopStop loopHalf loopDouble callPrev callNext jump:N pfl quant keylock
//   mode:M hot:I hotClear:I loop:SIZE load fader trim hi mid low cfx xfader headMix master
//   browse browsePress browseShift browseUp browseDown zoom unsupported:WHAT

/*MIXXX_MAPS*/

// The rekordbox-era DDJ layout (DDJ-400, FLX2/4/6/10, 800, 1000...), written out from the FLX4,
// which it was verified on. deckChs: the MIDI channels the decks use (4-deck units fold 3/4 onto 1/2).
function ddjRekordboxMap(deckChs = [0, 1], padChs = [[0x97, 0x98], [0x99, 0x9a]]) {
  const m = [];
  deckChs.forEach((ch, k) => {
    const d = k % 2, n = 0x90 + ch, c = 0xb0 + ch;
    const notes = [[0x0b, "play"], [0x0e, "playCue"], [0x0c, "cue"], [0x48, "start"], [0x58, "sync"], [0x5c, "syncOn"],
      [0x60, "range"], [0x36, "touch"], [0x67, "touch"], [0x10, "loopIn"], [0x11, "loopOut"], [0x4d, "reloop"],
      [0x50, "reloopStop"], [0x4c, "loopHalf"], [0x4e, "loopDouble"], [0x51, "callPrev"], [0x53, "callNext"],
      [0x3e, "jump:-4"], [0x3d, "jump:4"], [0x54, "pfl"], [0x68, "quant"], [0x3f, "ignore"],
      [0x1b, "mode:hotcue"], [0x6d, "mode:beatloop"], [0x20, "mode:beatjump"], [0x1e, "mode:padfx"],
      [0x6b, "mode:padfx2"], [0x22, "mode:sampler"], [0x69, "mode:keyboard"], [0x6f, "mode:keyshift"]];
    for (const [no, a] of notes) m.push([n, no, a, d, 0]);
    for (const [no, a] of [[0x22, "jogTop"], [0x23, "jogTop"], [0x21, "jogSide"], [0x29, "jogSearch"], [0x02, "ignore"]]) m.push([c, no, a, d, 0]);
    for (const [no, a] of [[0x00, "tempo"], [0x13, "fader"], [0x04, "trim"], [0x07, "hi"], [0x0b, "mid"], [0x0f, "low"]]) m.push([c, no, a, d, no + 0x20]);
  });
  padChs.forEach(([pn, ps], k) => {
    const d = k % 2;
    for (let p = 0; p < 8; p++) {
      m.push([pn, p, `hot:${p}`, d, 0], [ps, p, `hotClear:${p}`, d, 0]);
      m.push([pn, 0x60 + p, `loop:${LOOP_SIZES[p]}`, d, 0], [ps, 0x60 + p, `loop:${LOOP_SIZES[p]}`, d, 0]);
      m.push([pn, 0x20 + p, `jump:${JUMPS[p]}`, d, 0]);
    }
  });
  m.push([0x96, 0x46, "load", 0, 0], [0x96, 0x47, "load", 1, 0], [0x96, 0x48, "load", 0, 0], [0x96, 0x49, "load", 1, 0],
    [0x96, 0x41, "browsePress", -1, 0], [0x96, 0x42, "browseShift", -1, 0],
    [0xb6, 0x40, "browse", -1, 0], [0xb6, 0x64, "zoom", -1, 0],
    [0xb6, 0x1f, "xfader", -1, 0x3f], [0xb6, 0x17, "cfx", 0, 0x37], [0xb6, 0x18, "cfx", 1, 0x38], [0xb6, 0x0c, "headMix", -1, 0x2c]);
  for (const st of [0x94, 0x95]) for (let no = 0; no < 128; no++) m.push([st, no, "unsupported:Beat FX", -1, 0]);
  return m;
}
// Mixxx maps only cover channels 1-2 for some units: copy them onto 3-4 for four-deck hardware
function withDecks34(map) {
  const out = map.slice(), have = new Set(map.map((e) => e[0] * 256 + e[1]));
  for (const e of map) {
    const t = e[0] & 0xf0, ch = e[0] & 0x0f;
    if ((t === 0x90 || t === 0xb0) && ch <= 1) {
      const st = e[0] + 2;
      if (!have.has(st * 256 + e[1])) out.push([st, e[1], e[2], e[3], e[4]]);
    }
  }
  return out;
}
const FLX4_KEEPALIVE = [0xf0, 0x00, 0x40, 0x05, 0x00, 0x00, 0x04, 0x05, 0x00, 0x50, 0x02, 0xf7];
// src: "tested" = checked on the hardware, "mixxx" = from Mixxx's community mapping for this exact
// model, "family" = the shared Pioneer layout for that product line (likely right, not verified)
const PROFILES = [
  { id: "ddj-flx4", name: "Pioneer DDJ-FLX4", match: /FLX-?4/i, src: "tested", map: ddjRekordboxMap(), keepAlive: FLX4_KEEPALIVE, vu: true },
  { id: "ddj-400", name: "Pioneer DDJ-400", match: /DDJ-?400/i, src: "mixxx", map: () => MIXXX_MAPS["ddj-400"].concat(ddjRekordboxMap()), vu: true,
    init: [0xf0, 0x00, 0x40, 0x05, 0x00, 0x00, 0x02, 0x06, 0x00, 0x03, 0x01, 0xf7] },
  { id: "ddj-200", name: "Pioneer DDJ-200", match: /DDJ-?200/i, src: "mixxx", map: () => MIXXX_MAPS["ddj-200"],
    init: [0xf0, 0x00, 0x40, 0x05, 0x00, 0x00, 0x02, 0x0a, 0x00, 0x03, 0x01, 0xf7] },
  { id: "ddj-sb3", name: "Pioneer DDJ-SB3", match: /DDJ-?SB3/i, src: "mixxx", map: () => MIXXX_MAPS["ddj-sb3"], init: [0xf0, 0x00, 0x20, 0x7f, 0x03, 0x01, 0xf7] },
  { id: "ddj-sb2", name: "Pioneer DDJ-SB2", match: /DDJ-?SB2/i, src: "mixxx", map: () => MIXXX_MAPS["ddj-sb2"] },
  { id: "ddj-sb", name: "Pioneer DDJ-SB", match: /DDJ-?SB\b/i, src: "mixxx", map: () => withDecks34(MIXXX_MAPS["ddj-sb"]) },
  { id: "ddj-sx2", name: "Pioneer DDJ-SX2 / SX3", match: /DDJ-?SX[23]/i, src: "mixxx", map: () => MIXXX_MAPS["ddj-sx2"] },
  { id: "ddj-sx", name: "Pioneer DDJ-SX", match: /DDJ-?SX\b/i, src: "mixxx", map: () => MIXXX_MAPS["ddj-sx"] },
  { id: "xdj-rx", name: "Pioneer XDJ-RX", match: /XDJ-?RX\b(?!2|3)/i, src: "mixxx", map: () => MIXXX_MAPS["xdj-rx"], leds: false },
  { id: "cdj-2000", name: "Pioneer CDJ-2000 / NXS / NXS2 (MIDI mode)", match: /CDJ-?2000/i, src: "mixxx", map: () => withDecks34(MIXXX_MAPS["cdj-2000"]), leds: false },
  { id: "cdj-850", name: "Pioneer CDJ-850 / 900 (MIDI mode)", match: /CDJ-?(850|900)/i, src: "mixxx", map: () => withDecks34(MIXXX_MAPS["cdj-850"]), leds: false },
  { id: "cdj-350", name: "Pioneer CDJ-350 (MIDI mode)", match: /CDJ-?350/i, src: "mixxx", map: () => withDecks34(MIXXX_MAPS["cdj-350"]), leds: false },
  // product-line fallbacks
  { id: "ddj-rekordbox", name: "Pioneer DDJ / XDJ, rekordbox series (FLX2, FLX6, FLX10, 800, 1000, GRV6, RB, RR, RX, RZ...)", src: "family",
    match: /DDJ|FLX|XDJ|OPUS|GRV|AlphaTheta/i, map: ddjRekordboxMap([0, 1, 2, 3], [[0x97, 0x98], [0x99, 0x9a], [0x9b, 0x9c], [0x9d, 0x9e]]) },
  { id: "ddj-serato", name: "Pioneer DDJ, Serato series (SR, SR2, SZ, SZ2, REV1/5/7, 1000SRT, XP)", src: "family", match: /DDJ-?(SR|SZ|REV|XP|1000SRT)/i, map: () => MIXXX_MAPS["ddj-sx"] },
  { id: "cdj", name: "Pioneer CDJ / XDJ player (MIDI mode)", src: "family", match: /CDJ|XDJ-?(1000|700)/i, map: () => withDecks34(MIXXX_MAPS["cdj-2000"]), leds: false },
  { id: "learn", name: "Other controller (map it with MIDI learn)", src: "learn", match: /$^/, map: [] },
];
const SRC_NOTE = {
  tested: "Mapping checked on the hardware.",
  mixxx: "Mapping from Mixxx's community mapping for this model. Not tested here: if a control is wrong, fix it with Learn.",
  family: "This model uses the shared Pioneer layout for its product line. The main controls should work; fix anything wrong with Learn.",
  learn: "No built-in mapping: use Learn to assign controls.",
};
const PIONEERISH = /DDJ|FLX|CDJ|XDJ|DJM|OPUS|GRV|Pioneer|AlphaTheta/i;
function profileFor(portName) {
  // specific models first, then the product-line fallbacks (in list order)
  return PROFILES.find((p) => p.src !== "family" && p.match.test(portName))
    || PROFILES.filter((p) => p.src === "family").reverse().find((p) => p.match.test(portName))
    || PROFILES.find((p) => p.id === "learn");
}

const MIDI = { access: null, inputs: [], outputs: [], sysex: false, ledCache: new Map(), msb: new Map(), keep: null, log: [], name: "",
  profile: null, table: new Map(), lsbTable: new Map(), ledEntries: [], learned: [], learning: null };
const midiKey = (st, d1) => (((st & 0xf0) === 0x80 ? 0x90 | (st & 0x0f) : st) << 8) | d1;
function learnedKey(p) { return `cb.learn.${p.id}`; }
function useProfile(p, portName) {
  if (typeof p === "string") p = PROFILES.find((x) => x.id === p) || profileFor(p);
  MIDI.profile = p;
  let learned = [];
  try { learned = JSON.parse(localStorage.getItem(learnedKey(p)) || "[]"); } catch (e) {}
  MIDI.learned = learned;
  const base = typeof p.map === "function" ? p.map() : p.map;
  MIDI.table.clear(); MIDI.lsbTable.clear(); MIDI.msb.clear(); MIDI.ledCache.clear();
  // learned entries win; earlier entries in a profile win over later ones
  for (const e of learned.concat(base)) {
    const k = midiKey(e[0], e[1]);
    if (!MIDI.table.has(k)) MIDI.table.set(k, e);
    if (e[4]) { const lk = midiKey(e[0], e[4]); if (!MIDI.lsbTable.has(lk)) MIDI.lsbTable.set(lk, e); }
  }
  MIDI.ledEntries = p.leds === false && !learned.length ? [] : [...MIDI.table.values()].filter((e) => (e[0] & 0xf0) === 0x90 && LED_ACTIONS.test(e[2]));
  renderControllerPanel();
  return p;
}
async function initMIDI() {
  if (!navigator.requestMIDIAccess) { setMidiPill(false, IOS ? "Touch mode" : "Web MIDI needs Chrome or Edge"); return; }
  try { MIDI.access = await navigator.requestMIDIAccess({ sysex: true }); MIDI.sysex = true; }
  catch (e) {
    try { MIDI.access = await navigator.requestMIDIAccess(); }
    catch (e2) { setMidiPill(false, "MIDI blocked"); status("MIDI access was refused. Allow it in Chrome's site settings and reload.", 9000); return; }
  }
  MIDI.access.onstatechange = () => bindMIDI();
  bindMIDI();
}
function bindMIDI() {
  for (const inp of MIDI.inputs) inp.onmidimessage = null;
  const all = [...MIDI.access.inputs.values()];
  // a chosen device, else the first Pioneer/AlphaTheta one, else any controller at all
  const want = pref("cb.midiIn", "");
  const inp = all.find((p) => p.name === want) || all.find((p) => PIONEERISH.test(p.name)) || all[0];
  renderControllerPanel(all);
  if (!inp) { setMidiPill(false, "No controller"); MIDI.inputs = []; MIDI.outputs = []; return; }
  MIDI.inputs = [inp];
  const base = inp.name.replace(/\s*(MIDI|IN|OUT|\d+)\s*$/gi, "");
  MIDI.outputs = [...MIDI.access.outputs.values()].filter((o) => o.name === inp.name || (base && o.name.startsWith(base)));
  inp.onmidimessage = (e) => midiIn(e.data);
  MIDI.name = inp.name;
  const forced = pref(`cb.profileFor.${inp.name}`, "");
  const p = useProfile(PROFILES.find((x) => x.id === forced) || profileFor(inp.name), inp.name);
  setMidiPill(true, MIDI.name + (MIDI.sysex || !p.keepAlive ? "" : " (lights may sleep)"));
  clearInterval(MIDI.keep);
  if (MIDI.sysex && p.init) midiSend(p.init);
  if (MIDI.sysex && p.keepAlive) {
    // the FLX4 drops into demo-light mode unless the software checks in every so often
    MIDI.keep = setInterval(() => midiSend(p.keepAlive), 200);
    midiSend(p.keepAlive);
  }
  status(`${MIDI.name} connected · ${p.name}${p.src === "tested" ? "" : " (see Settings → Controller)"}`);
}
function setMidiPill(on, text) {
  const p = $("#midiPill");
  p.classList.toggle("on", on);
  p.querySelector("span").textContent = text;
}
function midiSend(bytes) {
  MIDI.log.push(bytes);
  if (MIDI.log.length > 500) MIDI.log.splice(0, 250);
  for (const o of MIDI.outputs) { try { o.send(bytes); } catch (e) {} }
}
function led(statusByte, note, on) {
  const key = statusByte * 256 + note, v = on === true ? 0x7f : on === false ? 0 : on;
  if (MIDI.ledCache.get(key) === v) return;
  MIDI.ledCache.set(key, v);
  midiSend([statusByte, note, v]);
}
function relTicks(v) { return v - 64; }                 // jog wheels: centre 64, <64 backwards
function relKnob(v) { return v < 64 ? v : v - 128; }    // browse knobs: 1 = clockwise, 127 = anticlockwise

function midiIn(data) {
  const [st, d1, d2 = 0] = data;
  const type = st & 0xf0;
  if (type !== 0x90 && type !== 0x80 && type !== 0xb0) return;
  if (MIDI.learning) return learnCapture(st, d1, d2);
  const k = midiKey(st, d1);
  const e = MIDI.table.get(k);
  if (e) return runEntry(e, type, d2, false);
  const l = MIDI.lsbTable.get(k);
  if (l && type === 0xb0) return runEntry(l, type, d2, true);
}

const ABS_ACTIONS = new Set(["tempo", "fader", "trim", "hi", "mid", "low", "cfx", "xfader", "headMix", "master"]);
const REL_ACTIONS = new Set(["jogTop", "jogSide", "jogSearch", "browse", "zoom"]);
const LED_ACTIONS = /^(play|cue|sync|pfl|loopIn|loopOut|reloop|keylock|quant|mode:|hot:|loop:)/;
const PAD_MODES_OK = new Set(["hotcue", "beatloop", "beatjump"]);
function runEntry(e, type, v, isLsb) {
  const [, , action, deck, lsb] = e;
  const colon = action.indexOf(":"), name = colon < 0 ? action : action.slice(0, colon), arg = colon < 0 ? "" : action.slice(colon + 1);
  const d = deck >= 0 ? decks[deck] : null;
  if (type === 0xb0 && ABS_ACTIONS.has(name)) {
    let val;
    if (!lsb) val = v / 127;
    else if (!isLsb) { MIDI.msb.set(e, v); val = v / 127; }       // apply the MSB straight away, refine on the LSB
    else val = (((MIDI.msb.get(e) || 0) << 7) | v) / 16383;
    return setAbs(name, deck, val);
  }
  if (REL_ACTIONS.has(name)) {
    if (type !== 0xb0) return;
    switch (name) {
      case "jogTop": return d.jogTicks(relTicks(v), "scratch");
      case "jogSide": return d.jogTicks(relTicks(v), "bend");
      case "jogSearch": return d.jogTicks(relTicks(v), "search");
      case "browse": return moveSel(relKnob(v));
      case "zoom": zoomSecs = clamp(zoomSecs * (relKnob(v) > 0 ? 0.8 : 1.25), 2, 32); return;
    }
  }
  const on = type === 0x90 ? v > 0 : type === 0x80 ? false : v > 63;
  pressAction(name, arg, d, deck, on);
}
function setAbs(name, deck, val) {
  switch (name) {
    case "tempo": { // top = slower, bottom = faster, like a CDJ
      const pitch = val * 2 - 1;
      decks[deck].setPitch(pitch); setCtl(`pitch${deck}`, 0.5 - pitch / 2); return;
    }
    case "fader": M.fader[deck] = val; applyMixer(deck); setCtl(`fader${deck}`, val); return;
    case "trim": case "hi": case "mid": case "low": case "cfx":
      M[name][deck] = val; applyMixer(deck); setCtl(`${name}${deck}`, val); return;
    case "xfader": M.xfader = val; applyMixer(0); applyMixer(1); setCtl("xfader", val); return;
    case "headMix": M.headMix = val; applyMaster(); setCtl("headmix", val); return;
    case "master": M.master = val; applyMaster(); setCtl("master", val); return;
  }
}
function pressAction(name, arg, d, deck, on) {
  switch (name) {
    case "play": if (on) d.togglePlay(); return;
    case "playCue": if (on) { d.seek(d.cue); d.setPlaying(true); } return;
    case "cue": on ? d.cueDown() : d.cueUp(); return;
    case "start": if (on) { d.setPlaying(false); d.seek(0); } return;
    case "sync": if (on) d.setSync(!d.sync); return;
    case "syncOn": if (on && !d.sync) d.setSync(true); return;
    case "range": if (on) d.cycleRange(); return;
    case "touch": d.jogTouch(on); return;
    case "loopIn":                                               // hold for half a second: 4-beat loop
      if (on) { d.loopInDown = performance.now(); d.loopIn(); }
      else if (d.loopInDown && performance.now() - d.loopInDown > 500) d.beatLoop(4);
      return;
    case "loopOut": if (on) d.loopOut(); return;
    case "reloop": if (on) d.reloopExit(); return;
    case "reloopStop": if (on) { d.reloopExit(); if (d.loop.on) d.setPlaying(false); } return;
    case "loopHalf": if (on) d.loopScale(0.5); return;
    case "loopDouble": if (on) d.loopScale(2); return;
    case "callPrev": if (on) d.callCue(-1); return;
    case "callNext": if (on) d.callCue(1); return;
    case "jump": if (on) d.beatJump(+arg); return;
    case "pfl": if (on) { M.pfl[deck] = !M.pfl[deck]; applyMixer(deck); refreshMixerUI(); } return;
    case "quant": if (on) { d.quant = !d.quant; refreshDeckUI(deck); } return;
    case "keylock": if (on) d.setMT(!d.mt); return;
    case "mode":
      if (!on) return;
      if (PAD_MODES_OK.has(arg)) { d.padMode = arg; refreshDeckUI(deck); }
      else status(`Pad mode "${arg}" isn't in Cratebox yet`);
      return;
    case "hot": if (on) d.hotcue(+arg); return;
    case "hotClear": if (on) d.clearHot(+arg); return;
    case "loop": if (on) d.beatLoop(+arg); return;
    case "load": if (on) loadSelected(deck); return;
    case "browsePress": if (on) $("#search").focus(); return;
    case "browseShift": if (on) setBrowse(!document.body.classList.contains("browse")); return;
    case "browseUp": if (on) moveSel(-1); return;
    case "browseDown": if (on) moveSel(1); return;
    case "unsupported": if (on) status(`${arg} isn't in Cratebox yet`); return;
  }
}
function setCtl(id, v) { if (widgets[id]) widgets[id].set(v); }

// ---- LEDs: Pioneer hardware lights a button when it receives its own note back ----
let blinkOn = false;
function updateLeds() {
  if (!MIDI.outputs.length) return;
  blinkOn = performance.now() % 1000 < 500;
  for (const e of MIDI.ledEntries) {
    const [st, no, action, deck] = e;
    if (deck < 0) continue;
    const d = decks[deck];
    const colon = action.indexOf(":"), name = colon < 0 ? action : action.slice(0, colon), arg = action.slice(colon + 1);
    let v;
    switch (name) {
      case "play": v = d.playing ? true : d.loaded ? blinkOn : false; break;            // PLAY blinks when paused
      case "cue": { const atCue = d.loaded && Math.abs(d.now() - d.cue) < 0.03;
        v = d.loaded && (atCue || d.previewing) ? true : d.loaded && !d.playing ? blinkOn : false; break; }
      case "sync": v = d.sync; break;
      case "pfl": v = M.pfl[deck]; break;
      case "loopIn": v = d.loop.on || (d.loop.a != null && d.loop.b == null && blinkOn); break;
      case "loopOut": v = d.loop.on; break;
      case "reloop": v = d.loop.b != null; break;
      case "keylock": v = d.mt; break;
      case "quant": v = d.quant; break;
      case "mode": v = d.padMode === arg; break;
      case "hot": v = d.padMode === "hotcue" && d.hot[+arg] != null; break;
      case "loop": v = d.padMode === "beatloop" && d.loop.on && Math.abs(d.loopBeats() - +arg) < 0.01; break;
      default: continue;
    }
    led(st, no, v);
  }
  if (MIDI.profile && MIDI.profile.vu) for (const i of [0, 1]) led(0xb0 + i, 0x02, Math.round(meterState[i] * 127));   // channel VU meters
}

// ---- MIDI learn: click a control on screen, then move or press it on the controller ----
// learnable on-screen controls carry data-learn="action" and data-deck
const LEARN_LABEL = { play: "Play", cue: "Cue", sync: "Sync", loopIn: "Loop in", loopOut: "Loop out", reloop: "Reloop/exit",
  tempo: "Tempo fader", jog: "Jog wheel", pfl: "Headphone cue", fader: "Channel fader", trim: "Trim", hi: "EQ high",
  mid: "EQ mid", low: "EQ low", cfx: "Filter (CFX)", xfader: "Crossfader", headMix: "Cue/master mix", master: "Master level",
  browse: "Browse knob", browsePress: "Browse knob press", load: "Load", keylock: "Master tempo", quant: "Quantize", jogSide: "Jog side (nudge)" };
function startLearn() {
  if (!MIDI.profile) useProfile("learn");
  document.documentElement.classList.add("learning");
  MIDI.learning = { target: null };
  $("#learnBar").hidden = false;
  learnHint("Click a control on screen, then move or press it on the controller.");
}
function stopLearn() {
  document.documentElement.classList.remove("learning");
  MIDI.learning = null;
  $("#learnBar").hidden = true;
  for (const el of document.querySelectorAll(".learn-target")) el.classList.remove("learn-target");
  renderControllerPanel();
}
function learnHint(t) { $("#learnText").textContent = t; }
function learnPick(el) {
  for (const x of document.querySelectorAll(".learn-target")) x.classList.remove("learn-target");
  el.classList.add("learn-target");
  const action = el.dataset.learn, deck = el.dataset.deck == null ? -1 : +el.dataset.deck;
  MIDI.learning.target = { action, deck, el, got: {} };
  const who = (deck >= 0 ? `Deck ${deck + 1} ` : "") + (LEARN_LABEL[action] || (action.startsWith("hot:") ? `Pad ${+action.slice(4) + 1}` : action));
  learnHint(action === "jog" ? `${who}: touch the top of the platter, then turn it.` : `${who}: now move or press it on the controller.`);
}
function learnCapture(st, d1, d2) {
  const L = MIDI.learning, t = L && L.target;
  if (!t) return;
  const type = st & 0xf0, s = type === 0x80 ? 0x90 | (st & 0x0f) : st;
  if (type === 0x80 || (type === 0x90 && d2 === 0)) return;       // releases
  let entries = [];
  if (t.action === "jog") {
    if (type === 0x90) t.got.touch = [s, d1, "touch", t.deck, 0];
    else t.got.turn = [s, d1, "jogTop", t.deck, 0];
    if (!(t.got.touch && t.got.turn)) { learnHint(t.got.touch ? "Got the touch. Now turn the platter." : "Got the turn. Now touch the top of the platter."); return; }
    entries = [t.got.touch, t.got.turn];
  } else if (ABS_ACTIONS.has(t.action)) {
    if (type !== 0xb0) return learnHint("That sent a button press. Move a knob or fader instead.");
    // Pioneer-style 14-bit pairs: the fine part arrives on CC + 32
    entries = [[s, d1, t.action, t.deck, d1 < 0x20 ? d1 + 0x20 : 0]];
  } else if (t.action === "browse") {
    if (type !== 0xb0) return learnHint("Turn the knob rather than pressing it.");
    entries = [[s, d1, "browse", -1, 0]];
  } else {
    entries = [[s, d1, t.action, t.deck, 0]];
  }
  const p = MIDI.profile, keys = new Set(entries.map((e) => midiKey(e[0], e[1])));
  const targets = new Set(entries.map((e) => `${e[2]}/${e[3]}`));
  // one control does one thing: drop older learns on the same message or for the same on-screen control
  MIDI.learned = MIDI.learned.filter((e) => !keys.has(midiKey(e[0], e[1])) && !targets.has(`${e[2]}/${e[3]}`));
  MIDI.learned.push(...entries);
  try { localStorage.setItem(learnedKey(p), JSON.stringify(MIDI.learned)); } catch (e) {}
  const keep = MIDI.learning;
  useProfile(p);
  MIDI.learning = keep;
  const hex = (b) => b.toString(16).toUpperCase().padStart(2, "0");
  learnHint(`Mapped ${entries.map((e) => `${hex(e[0])} ${hex(e[1])}`).join(" + ")}. Click the next control, or Done.`);
  t.el.classList.remove("learn-target"); t.el.classList.add("learned-flash");
  setTimeout(() => t.el.classList.remove("learned-flash"), 700);
  L.target = null;
}
document.addEventListener("pointerdown", (e) => {
  if (!MIDI.learning) return;
  const el = e.target.closest("[data-learn]");
  if (!el) return;
  e.preventDefault(); e.stopPropagation();
  learnPick(el);
}, true);
document.addEventListener("click", (e) => { if (MIDI.learning && e.target.closest("[data-learn]")) { e.preventDefault(); e.stopPropagation(); } }, true);
function clearLearned() {
  const p = MIDI.profile;
  if (!p) return;
  try { localStorage.removeItem(learnedKey(p)); } catch (e) {}
  useProfile(p);
  status(`Cleared your learned controls for ${p.name}`);
}
function exportMapping() {
  const p = MIDI.profile;
  if (!p) return;
  const data = { cratebox: 1, profile: p.id, device: MIDI.name, learned: MIDI.learned };
  const a = h("a", { href: URL.createObjectURL(new Blob([JSON.stringify(data, null, 1)], { type: "application/json" })), download: `cratebox-${p.id}-mapping.json` });
  document.body.append(a); a.click(); a.remove();
}
async function importMapping(file) {
  try {
    const data = JSON.parse(await file.text());
    if (!Array.isArray(data.learned)) throw new Error("not a Cratebox mapping file");
    const p = PROFILES.find((x) => x.id === data.profile) || MIDI.profile || PROFILES.find((x) => x.id === "learn");
    localStorage.setItem(learnedKey(p), JSON.stringify(data.learned.filter((e) => Array.isArray(e) && e.length === 5)));
    if (MIDI.name) setPref(`cb.profileFor.${MIDI.name}`, p.id);
    useProfile(p);
    status(`Imported ${data.learned.length} mapped controls for ${p.name}`);
  } catch (e) { status(`Couldn't import that mapping: ${e.message}`, 8000); }
}
// settings panel section
function renderControllerPanel(ports) {
  const box = document.getElementById("ctlPanel");
  if (!box) return;
  const p = MIDI.profile;
  const inSel = $("#ctlIn"), pSel = $("#ctlProfile");
  if (!ports && !inSel.options.length) inSel.append(h("option", { value: "" }, "No controller connected"));
  if (ports) {
    inSel.innerHTML = "";
    if (!ports.length) inSel.append(h("option", { value: "" }, "No MIDI devices"));
    for (const port of ports) inSel.append(h("option", { value: port.name }, port.name));
    inSel.value = MIDI.name || (ports[0] && ports[0].name) || "";
  }
  if (!pSel.options.length) for (const x of PROFILES) pSel.append(h("option", { value: x.id }, x.name));
  if (p) pSel.value = p.id;
  $("#ctlNote").textContent = p ? SRC_NOTE[p.src] + (MIDI.learned.length ? ` You've mapped ${MIDI.learned.length} control${MIDI.learned.length === 1 ? "" : "s"} yourself.` : "") : "";
}
