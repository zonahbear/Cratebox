// rekordbox file parsers (tools/rekordbox.js, the same code that's in cratebox.html), in node.
//
//     node tests/test_rekordbox.js
//
// export.pdb + ANLZ: a real rekordbox USB export (tests/fixtures/rekordbox_usb, from pyrekordbox's
// test data, MIT licence). Cue lists: none of the available real exports have cues, so those are
// built here byte by byte from Deep Symmetry's documented layout (crate-digger, anlz.adoc).
const fs = require("fs"), path = require("path");
const ROOT = path.join(__dirname, "..");
global.DOMParser = class {};
eval(fs.readFileSync(path.join(ROOT, "tools/rekordbox.js"), "utf8") + "\nglobal.RB = RB;");
const camelotStub = null;          // keyIndex needs cratebox's camelot(); not tested here
let pass = 0, fail = 0;
const check = (name, ok, detail = "") => { ok ? pass++ : fail++; console.log((ok ? "PASS " : "FAIL ") + name + (detail ? `  (${detail})` : "")); };
const ab = (f) => { const b = fs.readFileSync(path.join(ROOT, f)); return b.buffer.slice(b.byteOffset, b.byteOffset + b.length); };
const USB = "tests/fixtures/rekordbox_usb";

// ---- export.pdb
const db = RB.parsePdb(ab(USB + "/PIONEER/rekordbox/export.pdb"));
const titles = db.tracks.map((t) => t.title).sort();
check("export.pdb: all 6 tracks", JSON.stringify(titles) === JSON.stringify(["Demo Track 1", "Demo Track 2", "HORN", "NOISE", "SINEWAVE", "SIREN"]), titles.join(", "));
const d1 = db.tracks.find((t) => t.title === "Demo Track 1");
check("export.pdb: artist, key, BPM, length, file path, analysis path",
  d1.artist === "Loopmasters" && d1.key === "Fm" && d1.bpm === 128 && d1.duration === 172
  && d1.path === "/Contents/Loopmasters/UnknownAlbum/Demo Track 1.mp3" && d1.anlzPath === "/PIONEER/USBANLZ/P016/0000875E/ANLZ0000.DAT", JSON.stringify(d1).slice(0, 200));
const pl = Object.fromEntries(db.playlists.map((p) => [p.name, p]));
check("export.pdb: playlist tree (Playlist 1, Folder > Sub Playlist)",
  pl["Playlist 1"] && !pl["Playlist 1"].folder && pl["Playlist 1"].parent === 0 && pl.Folder && pl.Folder.folder
  && pl["Sub Playlist"] && pl["Sub Playlist"].parent === pl.Folder.id, JSON.stringify(db.playlists));
check("export.pdb: playlist entries in order", JSON.stringify(pl["Playlist 1"].tracks) === "[1,2]", JSON.stringify(pl["Playlist 1"].tracks));

// ---- ANLZ: beat grid and phrases
const dat = RB.parseAnlz(ab(USB + d1.anlzPath)), ext = RB.parseAnlz(ab(USB + d1.anlzPath.replace(".DAT", ".EXT")));
const g = RB.gridFromBeats(dat.beats);
check("ANLZ beat grid: 128 BPM, first downbeat at 25 ms", g.bpm === 128 && Math.abs(g.firstBeat - 0.025) < 1e-9 && dat.beats.length === 368, JSON.stringify(g) + ` ${dat.beats.length} beats`);
const ph = RB.phrasesFrom({ beats: dat.beats, phrases: ext.phrases });
check("ANLZ phrases (PSSI, unmasked): 19, starting on the first beat", ph && ph.length === 19 && Math.abs(ph[0].start - 0.025) < 1e-9 && ph.every((p) => p.bars >= 1 && p.label), ph && JSON.stringify(ph.slice(0, 3)));
check("ANLZ phrase starts line up with the beat grid", ph.every((p) => Math.abs(((p.start - g.firstBeat) / (60 / 128)) % 1) < 0.01 || Math.abs(((p.start - g.firstBeat) / (60 / 128)) % 1 - 1) < 0.01));

// ---- cue lists, built from the documented layout
function section(four, headerBody, entries) {
  const lenHeader = 12 + headerBody.length, lenTag = lenHeader + entries.reduce((n, e) => n + e.length, 0);
  const b = Buffer.alloc(lenTag);
  b.write(four, 0, "ascii"); b.writeUInt32BE(lenHeader, 4); b.writeUInt32BE(lenTag, 8);
  Buffer.from(headerBody).copy(b, 12);
  let o = lenHeader;
  for (const e of entries) { e.copy(b, o); o += e.length; }
  return b;
}
function pcpt(hot, ms, loopMs, status = 0) {            // PCOB entry, 0x38 bytes
  const e = Buffer.alloc(0x38);
  e.write("PCPT", 0, "ascii"); e.writeUInt32BE(0x1c, 4); e.writeUInt32BE(0x38, 8);
  e.writeUInt32BE(hot, 0x0c); e.writeUInt32BE(status, 0x10); e.writeUInt32BE(0x10000, 0x14);
  e.writeUInt16BE(0xffff, 0x18); e.writeUInt16BE(1, 0x1a);
  e.writeUInt8(loopMs != null ? 2 : 1, 0x1c); e.writeUInt32BE(ms, 0x20); e.writeUInt32BE(loopMs != null ? loopMs : 0xffffffff, 0x24);
  return e;
}
function pcob(hotList, entries) {
  const hb = Buffer.alloc(12); hb.writeUInt32BE(hotList ? 1 : 0, 0); hb.writeUInt16BE(entries.length, 6);
  return section("PCOB", hb, entries);
}
function pcp2(hot, ms, loopMs, comment = "") {          // PCO2 entry with a comment and a colour
  const c = Buffer.from(comment ? comment + "\0" : "", "utf16le").swap16();
  const len = 0x2c + 4 + c.length + 4, e = Buffer.alloc(len);
  e.write("PCP2", 0, "ascii"); e.writeUInt32BE(0x10, 4); e.writeUInt32BE(len, 8);
  e.writeUInt32BE(hot, 0x0c); e.writeUInt8(loopMs != null ? 2 : 1, 0x10);
  e.writeUInt32BE(ms, 0x14); e.writeUInt32BE(loopMs != null ? loopMs : 0xffffffff, 0x18);
  e.writeUInt32BE(c.length, 0x2c); c.copy(e, 0x30); e.writeUInt8(0x2a, 0x30 + c.length);
  return e;
}
function pco2(hotList, entries) {
  const hb = Buffer.alloc(8); hb.writeUInt32BE(hotList ? 1 : 0, 0); hb.writeUInt16BE(entries.length, 4);
  return section("PCO2", hb, entries);
}
function anlz(...sections) {
  const head = Buffer.alloc(28); head.write("PMAI", 0, "ascii"); head.writeUInt32BE(28, 4);
  const all = Buffer.concat([head, ...sections]); all.writeUInt32BE(all.length, 8);
  return all.buffer.slice(all.byteOffset, all.byteOffset + all.length);
}
const a1 = RB.parseAnlz(anlz(pcob(false, [pcpt(0, 1234), pcpt(0, 900)]), pcob(true, [pcpt(1, 5000), pcpt(2, 8000, 12000, 4)])));
check("PCOB (.DAT): memory cues, ordinary status-0 entries kept", a1.memory.length === 2 && a1.memory.some((c) => c.ms === 1234) && a1.memory.some((c) => c.ms === 900), JSON.stringify(a1.memory));
check("PCOB (.DAT): hot cue A and a looping hot cue B (active loop status)", a1.hot.length === 2 && a1.hot[0].hot === 1 && a1.hot[0].ms === 5000 && a1.hot[0].loopMs == null
  && a1.hot[1].hot === 2 && a1.hot[1].loopMs === 12000, JSON.stringify(a1.hot));
const a2 = RB.parseAnlz(anlz(pcob(true, [pcpt(1, 5000)]), pco2(true, [pcp2(1, 5100, null, "Drop"), pcp2(8, 99000)]), pco2(false, [pcp2(0, 700)])));
check("PCO2 (.EXT, NXS2): wins over PCOB, comments skipped correctly, hot cues up to H", a2.hot.length === 2 && a2.hot[0].ms === 5100 && a2.hot[1].hot === 8 && a2.hot[1].ms === 99000
  && a2.memory.length === 1 && a2.memory[0].ms === 700, JSON.stringify(a2));
check("junk instead of an ANLZ file: empty result, no throw", (() => { const r = RB.parseAnlz(new ArrayBuffer(40)); return !r.beats.length && !r.hot.length; })());
check("keyName for XML export", RB.keyName(5) === "F" && RB.keyName(17) === "Fm" && RB.keyName(-1) === "");

console.log(`\n${pass}/${pass + fail} checks passed`);
process.exit(fail ? 1 : 0);
