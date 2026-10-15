// =====================================================================================
//  Playlists, rekordbox USB/SD devices and rekordbox XML
// =====================================================================================
// Own playlists live in IndexedDB ("playlists"): { id, name, folder, parent, order, items: [trackId],
// meta: { trackId: {title, artist, file, size} } } - meta lets a playlist show (and later re-find)
// tracks whose folder isn't connected right now.
// Devices are rekordbox USB/SD exports opened read-only: their tracks join the library (marked with
// t.device) and their playlist tree shows under DEVICES.
const PL = { lists: [], devices: [], view: { kind: "all" }, open: new Set(), focus: "list", treeRows: [], treeSel: 0 };
let plSaveT = 0;
const plDirty = new Set();
function plNew(name, folder = false, parent = null) {
  const id = "pl" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const order = PL.lists.filter((x) => x.parent === parent).length;
  const p = { id, name, folder, parent, order, items: [], meta: {} };
  PL.lists.push(p); plSave(p);
  if (parent) PL.open.add(parent);
  return p;
}
function plGet(id) { return PL.lists.find((x) => x.id === id); }
function plSave(p) {
  // batched: everything changed in the last moment is written together
  for (const x of p ? [p] : PL.lists) plDirty.add(x);
  clearTimeout(plSaveT);
  plSaveT = setTimeout(() => {
    for (const x of plDirty) if (PL.lists.includes(x)) idbPut("playlists", x.id, x);
    plDirty.clear();
  }, 150);
}
async function plLoad() {
  const all = await idb("playlists", "readonly", (o) => o.getAll());
  PL.lists = (all || []).filter((x) => x && x.id);
  try { for (const id of JSON.parse(localStorage.getItem("cb.plOpen") || "[]")) PL.open.add(id); } catch (e) {}
  renderTree();
}
function metaOf(t) { return { title: t.title, artist: t.artist, file: t.name || (t.rel || "").split("/").pop(), size: t.size || 0 }; }
function plAdd(p, tracks, at) {
  if (!p || p.folder) return 0;
  const ids = tracks.filter((t) => t && !t.missing).map((t) => t.id);
  for (const t of tracks) if (t && !t.missing) p.meta[t.id] = metaOf(t);
  if (at == null || at > p.items.length) at = p.items.length;
  p.items.splice(at, 0, ...ids);
  plSave(p); renderTree();
  if (PL.view.kind === "pl" && PL.view.id === p.id) applyView(true);
  return ids.length;
}
function plRemoveAt(p, positions) {
  const drop = new Set(positions);
  p.items = p.items.filter((_, i) => !drop.has(i));
  plSave(p); renderTree(); applyView(true);
}
function plMove(p, positions, to) {
  // move the items at `positions` so they start at index `to` (in the list before removal)
  const pos = [...positions].sort((a, b) => a - b), moving = pos.map((i) => p.items[i]);
  const before = pos.filter((i) => i < to).length;
  const rest = p.items.filter((_, i) => !pos.includes(i));
  rest.splice(Math.max(0, to - before), 0, ...moving);
  p.items = rest; plSave(p); applyView(true);
  lib.selIds = new Set(moving); lib.sel = Math.max(0, to - before); renderList();
}
function plDelete(p) {
  const kill = new Set([p.id]);
  let grew = true;
  while (grew) { grew = false; for (const x of PL.lists) if (x.parent && kill.has(x.parent) && !kill.has(x.id)) { kill.add(x.id); grew = true; } }
  PL.lists = PL.lists.filter((x) => !kill.has(x.id));
  for (const id of kill) idb("playlists", "readwrite", (o) => o.delete(id));
  if (PL.view.kind === "pl" && kill.has(PL.view.id)) setView({ kind: "all" });
  renderTree();
}
// tracks of a playlist; ones we can't find show as "missing" rows
function plTracks(p) {
  const byId = new Map(lib.tracks.map((t) => [t.id, t]));
  return p.items.map((id, i) => byId.get(id) || { id, missing: true, title: (p.meta[id] || {}).title || id.split("|")[0].split("/").pop(), artist: (p.meta[id] || {}).artist || "", pos: i });
}
// a folder was (re)connected: point missing playlist entries at tracks with the same file name and size
function plRematch() {
  const byFile = new Map();
  for (const t of lib.tracks) {
    const f = (t.name || "").toLowerCase();
    byFile.set(f + "|" + t.size, t); if (!byFile.has(f)) byFile.set(f, t);
  }
  const have = new Set(lib.tracks.map((t) => t.id));
  for (const p of PL.lists) {
    let changed = false;
    p.items = p.items.map((id) => {
      if (have.has(id)) return id;
      const m = p.meta[id];
      if (!m || !m.file) return id;
      const f = m.file.toLowerCase(), t = byFile.get(f + "|" + m.size) || byFile.get(f);
      if (!t) return id;
      changed = true; p.meta[t.id] = metaOf(t); return t.id;
    });
    if (changed) plSave(p);
  }
}
function setView(v) {
  PL.view = v;
  lib.selIds = new Set(); lib.sel = lib.anchor = 0;
  if (v.kind === "pl") lib.sort = null;          // a playlist opens in its own order (so it can be rearranged)
  $("#list").scrollTop = 0;
  $("#library").classList.remove("treeopen");
  applyView(); renderTree();
  const name = viewName(v);
  $("#viewName").textContent = name;
  $("#plRemove").hidden = v.kind !== "pl";
}
function viewName(v) {
  if (v.kind === "all") return "Collection";
  if (v.kind === "pl") { const p = plGet(v.id); return p ? p.name : "Playlist"; }
  const d = PL.devices.find((x) => x.id === v.dev);
  if (!d) return "Device";
  if (v.kind === "dev") return d.name;
  const n = d.tree.find((x) => x.id === v.id);
  return `${d.name} · ${n ? n.name : ""}`;
}
// the tracks the list shows for the current view (before search and sort)
function viewTracks() {
  const v = PL.view;
  if (v.kind === "pl") { const p = plGet(v.id); return p ? plTracks(p) : []; }
  if (v.kind === "dev") return lib.tracks.filter((t) => t.device === v.dev);
  if (v.kind === "devpl") {
    const d = PL.devices.find((x) => x.id === v.dev), n = d && d.tree.find((x) => x.id === v.id);
    if (!n) return [];
    return n.tracks.map((rid) => d.byRbId.get(rid)).filter(Boolean);
  }
  return lib.tracks.filter((t) => !t.device);
}
function isOwnPlaylistView() { return PL.view.kind === "pl" && !lib.sort && !lib.query; }

// ---- the tree (sidebar on desktop, sheet on phones) ----
function treeRows() {
  const rows = [{ kind: "all", depth: 0, label: "Collection", count: lib.tracks.filter((t) => !t.device).length }];
  rows.push({ kind: "head", label: "Playlists", what: "pl" });
  const kids = (parent) => PL.lists.filter((x) => x.parent === parent).sort((a, b) => a.order - b.order || a.name.localeCompare(b.name));
  const walk = (parent, depth) => {
    for (const p of kids(parent)) {
      rows.push({ kind: p.folder ? "folder" : "pl", id: p.id, depth, label: p.name, count: p.folder ? null : p.items.length });
      if (p.folder && PL.open.has(p.id)) walk(p.id, depth + 1);
    }
  };
  walk(null, 1);
  rows.push({ kind: "head", label: "Devices", what: "dev" });
  for (const d of PL.devices) {
    rows.push({ kind: "dev", dev: d.id, depth: 1, label: d.name, count: d.trackCount });
    if (!PL.open.has("dev:" + d.id)) continue;
    const dk = (parent) => d.tree.filter((x) => x.parent === parent).sort((a, b) => a.sort - b.sort);
    const dw = (parent, depth) => {
      for (const n of dk(parent)) {
        rows.push({ kind: n.folder ? "devfolder" : "devpl", dev: d.id, id: n.id, depth, label: n.name, count: n.folder ? null : n.tracks.length });
        if (n.folder && PL.open.has(`dev:${d.id}:${n.id}`)) dw(n.id, depth + 1);
      }
    };
    dw(0, 2);
  }
  return rows;
}
function rowIsView(r) {
  const v = PL.view;
  return (r.kind === "all" && v.kind === "all") || (r.kind === "pl" && v.kind === "pl" && v.id === r.id)
    || (r.kind === "dev" && v.kind === "dev" && v.dev === r.dev) || (r.kind === "devpl" && v.kind === "devpl" && v.dev === r.dev && v.id === r.id);
}
function openRow(r) {
  if (r.kind === "all") setView({ kind: "all" });
  else if (r.kind === "pl") setView({ kind: "pl", id: r.id });
  else if (r.kind === "dev") { PL.open.add("dev:" + r.dev); setView({ kind: "dev", dev: r.dev }); }
  else if (r.kind === "devpl") setView({ kind: "devpl", dev: r.dev, id: r.id });
  else if (r.kind === "folder" || r.kind === "devfolder") toggleOpen(r);
}
function toggleOpen(r) {
  const k = r.kind === "folder" ? r.id : r.kind === "dev" ? "dev:" + r.dev : `dev:${r.dev}:${r.id}`;
  PL.open.has(k) ? PL.open.delete(k) : PL.open.add(k);
  renderTree();
}
function renderTree() {
  const box = document.getElementById("tree");
  if (!box) return;
  const rows = PL.treeRows = treeRows();
  try { localStorage.setItem("cb.plOpen", JSON.stringify([...PL.open].filter((x) => !x.startsWith("dev:")))); } catch (e) {}
  PL.treeSel = clamp(PL.treeSel, 0, rows.length - 1);
  box.innerHTML = "";
  box.classList.toggle("focus", PL.focus === "tree");
  rows.forEach((r, i) => {
    if (r.kind === "head") {
      const head = h("div", { class: "thead" }, h("span", {}, r.label.toUpperCase()));
      if (r.what === "pl") {
        head.append(h("button", { class: "ticon", title: "New playlist", onclick: () => startRename(plNew(nextName("Playlist")), true) }, "+"),
          h("button", { class: "ticon", title: "New folder", onclick: () => startRename(plNew(nextName("Folder"), true), true) }, "▤"),
          h("button", { class: "ticon", title: "rekordbox XML: import / export", onclick: (e) => xmlMenu(e.currentTarget) }, "⋯"));
        head.addEventListener("dragover", (e) => { if (PL.dragList) { e.preventDefault(); head.classList.add("drop"); } });
        head.addEventListener("dragleave", () => head.classList.remove("drop"));
        head.addEventListener("drop", (e) => { head.classList.remove("drop"); if (PL.dragList) { e.preventDefault(); movePlaylist(PL.dragList, null); } });
      } else if (CAN_PICK_FOLDER) {
        head.append(h("button", { class: "ticon wide", title: "Open a rekordbox USB stick or SD card (read-only)", onclick: openDevice }, "+ USB"));
      }
      box.append(head);
      return;
    }
    const folderish = r.kind === "folder" || r.kind === "devfolder" || r.kind === "dev";
    const openKey = r.kind === "folder" ? r.id : r.kind === "dev" ? "dev:" + r.dev : `dev:${r.dev}:${r.id}`;
    const caret = folderish ? h("span", { class: "caret", onclick: (e) => { e.stopPropagation(); toggleOpen(r); } }, PL.open.has(openKey) ? "▾" : "▸") : h("span", { class: "caret" }, "");
    const icon = { all: "♫", pl: "≡", folder: "", dev: "⏏", devpl: "≡", devfolder: "" }[r.kind];
    const el = h("div", { class: `trow2${rowIsView(r) ? " cur" : ""}${PL.focus === "tree" && i === PL.treeSel ? " tsel" : ""}${r.kind.startsWith("dev") ? " ro" : ""}`, style: `padding-left:${6 + r.depth * 12}px` },
      caret, h("span", { class: "ic" }, icon), h("span", { class: "nm" }, r.label), r.count != null ? h("span", { class: "ct" }, String(r.count)) : "");
    el.addEventListener("click", () => { PL.treeSel = i; openRow(r); });
    if (r.kind === "pl" || r.kind === "folder") {
      el.addEventListener("dblclick", () => startRename(plGet(r.id)));
      if (TOUCH_UI) el.append(h("button", { class: "tx", title: "Rename or delete", onclick: (e) => { e.stopPropagation();
        popMenu(e.currentTarget, [["Rename", () => startRename(plGet(r.id))], ["Delete…", () => confirmDelete(el, plGet(r.id))]]); } }, "⋯"));
      else el.append(h("button", { class: "tx", title: "Delete", onclick: (e) => { e.stopPropagation(); confirmDelete(el, plGet(r.id)); } }, "×"));
      el.draggable = true;
      el.addEventListener("dragstart", (e) => { PL.dragList = r.id; e.dataTransfer.setData("text/cratebox-pl", r.id); e.dataTransfer.effectAllowed = "move"; });
      el.addEventListener("dragend", () => { PL.dragList = null; });
      el.addEventListener("dragover", (e) => {
        const tracks = e.dataTransfer.types.includes("text/cratebox");
        if ((tracks && r.kind === "pl") || (PL.dragList && PL.dragList !== r.id && r.kind === "folder")) { e.preventDefault(); el.classList.add("drop"); }
      });
      el.addEventListener("dragleave", () => el.classList.remove("drop"));
      el.addEventListener("drop", (e) => {
        el.classList.remove("drop");
        const data = e.dataTransfer.getData("text/cratebox");
        if (data && r.kind === "pl") {
          e.preventDefault();
          const n = plAdd(plGet(r.id), dragTracks(data));
          status(`Added ${n} track${n === 1 ? "" : "s"} to ${r.label}`);
        } else if (PL.dragList && r.kind === "folder") { e.preventDefault(); movePlaylist(PL.dragList, r.id); }
      });
    }
    if (r.kind === "devpl") el.append(h("button", { class: "tx", title: "Copy to my playlists", onclick: (e) => { e.stopPropagation(); copyDevicePlaylist(r); } }, "⧉"));
    if (r.kind === "dev") el.append(h("button", { class: "tx", title: "Close this device", onclick: (e) => { e.stopPropagation(); closeDevice(r.dev); } }, "×"));
    box.append(el);
  });
}
const TOUCH_UI = document.documentElement.classList.contains("touch");
// FLX4 browse: press to jump between the tree and the track list, turn to move in whichever has focus
function treeMove(n) {
  const rows = PL.treeRows.length ? PL.treeRows : treeRows();
  let i = PL.treeSel;
  for (let step = 0; step < Math.abs(n); step++) {
    let j = i + Math.sign(n);
    while (j >= 0 && j < rows.length && rows[j].kind === "head") j += Math.sign(n);
    if (j < 0 || j >= rows.length) break;
    i = j;
  }
  PL.treeSel = i;
  const r = rows[i];
  if (r && (r.kind === "all" || r.kind === "pl" || r.kind === "devpl")) openRow(r);      // show what's in it as you scroll, like rekordbox
  else renderTree();
  const el = document.querySelectorAll("#tree .trow2")[rows.slice(0, i).filter((x) => x.kind !== "head").length];
  if (el) el.scrollIntoView({ block: "nearest" });
}
function treePress() {
  if (PL.focus !== "tree") {
    PL.focus = "tree";
    const rows = treeRows(), cur = rows.findIndex(rowIsView);
    PL.treeSel = cur >= 0 ? cur : 0;
    renderTree();
    return;
  }
  const r = PL.treeRows[PL.treeSel];
  if (!r) return;
  if (r.kind === "folder" || r.kind === "devfolder") return toggleOpen(r);
  if (r.kind === "dev" && !PL.open.has("dev:" + r.dev)) { openRow(r); return; }
  if (!rowIsView(r)) openRow(r);
  PL.focus = "list";
  renderTree(); renderList();
}
function nextName(base) {
  let n = 1;
  while (PL.lists.some((x) => x.name === `${base} ${n}`)) n++;
  return `${base} ${n}`;
}
function movePlaylist(id, parent) {
  const p = plGet(id);
  if (!p) return;
  // no moving a folder into itself
  for (let x = parent; x; x = (plGet(x) || {}).parent) if (x === id) return;
  p.parent = parent; p.order = PL.lists.filter((x) => x.parent === parent && x !== p).length;
  if (parent) PL.open.add(parent);
  plSave(p); renderTree();
}
function startRename(p, isNew) {
  if (!p) return;
  renderTree();
  const rows = [...document.querySelectorAll("#tree .trow2")], i = PL.treeRows.filter((r) => r.kind !== "head").findIndex((r) => r.id === p.id);
  const el = rows[i];
  if (!el) return;
  const nm = el.querySelector(".nm"), inp = h("input", { class: "tren", value: p.name });
  nm.replaceWith(inp);
  inp.focus(); inp.select();
  const done = (keep) => {
    if (done.ran) return; done.ran = true;
    const v = inp.value.trim();
    if (keep && v) { p.name = v; plSave(p); }
    renderTree();
    if (isNew && !p.folder) setView({ kind: "pl", id: p.id });
  };
  inp.addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Enter") done(true); if (e.key === "Escape") done(false); });
  inp.addEventListener("blur", () => done(true));
}
function confirmDelete(el, p) {
  if (!p) return;
  const n = p.folder ? PL.lists.filter((x) => x.parent === p.id).length : p.items.length;
  const bar = h("div", { class: "tconfirm" }, h("span", {}, `Delete "${p.name}"${p.folder && n ? ` and what's in it` : ""}?`),
    h("button", { class: "hbtn danger", onclick: (e) => { e.stopPropagation(); plDelete(p); status(`Deleted ${p.name}`); } }, "Delete"),
    h("button", { class: "hbtn", onclick: (e) => { e.stopPropagation(); renderTree(); } }, "Cancel"));
  el.replaceWith(bar);
}
function dragTracks(data) {
  let ids;
  try { ids = JSON.parse(data); } catch (e) { ids = [data]; }
  if (!Array.isArray(ids)) ids = [ids];
  const byId = new Map(lib.tracks.map((t) => [t.id, t]));
  return ids.map((id) => byId.get(id)).filter(Boolean);
}
function selectedTracks() {
  const ids = lib.selIds && lib.selIds.size ? lib.selIds : new Set(lib.view[lib.sel] ? [lib.view[lib.sel].id] : []);
  return lib.view.filter((t) => ids.has(t.id));
}
// "Add to playlist" menu (toolbar button; also how phones add tracks)
function addToMenu(btn) {
  const tracks = selectedTracks();
  if (!tracks.length) return status("Select a track first");
  const own = PL.lists.filter((x) => !x.folder);
  const path = (p) => { const parts = [p.name]; for (let x = plGet(p.parent); x; x = plGet(x.parent)) parts.unshift(x.name); return parts.join(" / "); };
  popMenu(btn, [
    ...own.sort((a, b) => path(a).localeCompare(path(b))).map((p) => [path(p) + ` (${p.items.length})`, () => {
      const n = plAdd(p, tracks); status(`Added ${n} track${n === 1 ? "" : "s"} to ${p.name}`);
    }]),
    ["+ New playlist…", () => { const p = plNew(nextName("Playlist")); plAdd(p, tracks); startRename(p); status(`Added ${tracks.length} to a new playlist`); }],
  ]);
}
function popMenu(anchor, items) {
  closeMenus();
  const m = h("div", { class: "popmenu" });
  for (const [label, fn] of items) {
    if (fn === null) { m.append(h("div", { class: "pmhead" }, label)); continue; }
    const b = h("button", {}, label);
    b.addEventListener("click", (e) => { e.stopPropagation(); closeMenus(); fn(); });
    m.append(b);
  }
  document.body.append(m);
  const r = anchor.getBoundingClientRect();
  const top = r.bottom + 4 + m.offsetHeight > innerHeight ? Math.max(8, r.top - m.offsetHeight - 4) : r.bottom + 4;
  m.style.left = Math.max(8, Math.min(innerWidth - m.offsetWidth - 8, r.left)) + "px";
  m.style.top = top + "px";
  setTimeout(() => document.addEventListener("pointerdown", closeMenusOutside, { capture: true }), 0);
}
function closeMenusOutside(e) { if (!e.target.closest(".popmenu")) closeMenus(); }
function closeMenus() { for (const m of document.querySelectorAll(".popmenu")) m.remove(); document.removeEventListener("pointerdown", closeMenusOutside, { capture: true }); }
function removeFromPlaylist() {
  const v = PL.view;
  if (v.kind !== "pl") return;
  const p = plGet(v.id);
  const ids = lib.selIds && lib.selIds.size ? lib.selIds : new Set(lib.view[lib.sel] ? [lib.view[lib.sel].id] : []);
  const pos = [];
  lib.view.forEach((t, k) => { if (ids.has(t.id)) pos.push(lib.viewPos[k]); });
  if (!pos.length) return;
  plRemoveAt(p, pos);
  lib.selIds = new Set();
  status(`Removed ${pos.length} from ${p.name}`);
}

// ---- rekordbox USB / SD ----
async function openDevice() {
  let dir;
  try { dir = await window.showDirectoryPicker({ id: "cratebox-usb", mode: "read" }); }
  catch (e) { return; }
  await mountDevice(dir, true);
}
async function subHandle(dir, path, kind) {
  const parts = path.split("/").filter(Boolean);
  let h2 = dir;
  for (let i = 0; i < parts.length; i++) {
    const last = i === parts.length - 1;
    h2 = last && kind === "file" ? await h2.getFileHandle(parts[i]) : await h2.getDirectoryHandle(parts[i]);
  }
  return h2;
}
async function mountDevice(dir, remember) {
  let pdb;
  try { pdb = await (await (await subHandle(dir, "PIONEER/rekordbox/export.pdb", "file")).getFile()).arrayBuffer(); }
  catch (e) { return status(`"${dir.name}" doesn't look like a rekordbox USB/SD export (no PIONEER/rekordbox/export.pdb). Pick the drive itself.`, 9000); }
  let db;
  try { db = RB.parsePdb(pdb); } catch (e) { return status("Couldn't read that rekordbox database: " + e.message, 9000); }
  const id = "usb-" + dir.name;
  if (PL.devices.some((x) => x.id === id)) {
    closeDevice(id, true);
    if (PL.devices.some((x) => x.id === id)) return status(`${dir.name} is already open`);
  }
  // your own edits to these tracks (grid fixes) from earlier sessions
  const saved = new Map();
  await idb("analysis", "readonly", (o) => {
    const r = o.openCursor(IDBKeyRange.bound(id + "|", id + "|\uffff"));
    r.onsuccess = () => { const c = r.result; if (c) { saved.set(c.key, c.value); c.continue(); } };
    return null;
  });
  const dev = { id, name: dir.name, dir, tree: db.playlists, byRbId: new Map(), trackCount: db.tracks.length };
  for (const r of db.tracks) {
    const t = {
      id: `${id}|${r.path}`, name: r.filename, rel: r.path, size: r.size, title: r.title || r.filename, artist: r.artist,
      bpm: r.bpm ? foldBpm(r.bpm) : null, key: RB.keyIndex(r.key), duration: r.duration, firstBeat: null, device: id,
      rb: r, ver: ANALYSIS_VER, phrases: [], stored: false, handle: null, file: null,
      async getFile() { if (!this.handle) this.handle = await subHandle(dir, this.rel, "file"); return this.handle.getFile(); },
    };
    if (t.key == null) t.key = -1;
    const c = saved.get(t.id);
    if (c && c.gridManual) Object.assign(t, { bpm: c.bpm, firstBeat: c.firstBeat, gridManual: true, autoBpm: c.autoBpm, autoFirst: c.autoFirst });
    dev.byRbId.set(r.id, t);
    lib.tracks.push(t);
  }
  PL.devices.push(dev);
  PL.open.add("dev:" + id);
  if (remember) {
    const saved = (await idbGet("settings", "devices")) || [];
    await idbPut("settings", "devices", saved.filter((d) => d.name !== dir.name).concat([dir]));
  }
  renderTree(); applyView(true);
  status(`${dir.name}: ${db.tracks.length} tracks, ${db.playlists.filter((p) => !p.folder).length} playlists (read-only)`);
}
function closeDevice(id, quiet) {
  const d = PL.devices.find((x) => x.id === id);
  if (!d) return;
  if (decks.some((k) => k.track && k.track.device === id)) { if (!quiet) status("Load something else on the decks first"); return; }
  PL.devices = PL.devices.filter((x) => x !== d);
  lib.tracks = lib.tracks.filter((t) => t.device !== id);
  if (!quiet) idbGet("settings", "devices").then((s) => idbPut("settings", "devices", (s || []).filter((x) => x.name !== d.name)));
  if (PL.view.dev === id) setView({ kind: "all" }); else { renderTree(); applyView(true); }
}
async function restoreDevices() {
  const saved = (await idbGet("settings", "devices")) || [];
  for (const dir of saved) {
    try { if ((await dir.queryPermission({ mode: "read" })) === "granted") await mountDevice(dir, false); } catch (e) {}
  }
}
// rekordbox's own analysis for a device track: grid, phrases, hot cues and the memory cue
async function readDeviceAnalysis(t) {
  const dev = PL.devices.find((x) => x.id === t.device);
  if (!dev || !t.rb || !t.rb.anlzPath) return false;
  const read = async (p) => { try { return RB.parseAnlz(await (await (await subHandle(dev.dir, p, "file")).getFile()).arrayBuffer()); } catch (e) { return null; } };
  const dat = await read(t.rb.anlzPath), ext = await read(t.rb.anlzPath.replace(/\.DAT$/i, ".EXT"));
  if (!dat || !dat.beats.length) return false;
  const g = RB.gridFromBeats(dat.beats);
  if (!t.gridManual) { t.bpm = g.bpm; t.firstBeat = g.firstBeat; t.autoBpm = g.bpm; t.autoFirst = g.firstBeat; }
  const ph = ext ? RB.phrasesFrom({ beats: dat.beats, phrases: ext.phrases }) : null;
  t.phrases = ph || [];
  const cues = ext && (ext.hot.length || ext.memory.length) ? ext : dat;
  t.rbCues = { hot: cues.hot, memory: cues.memory };
  t.rbRead = true;
  return true;
}
function rbCuesFor(t) {
  // rekordbox hot cues A-H and the first memory cue, used until you set your own in Cratebox
  const c = t.rbCues;
  if (!c) return null;
  const hot = new Array(8).fill(null);
  for (const q of c.hot) if (q.hot >= 1 && q.hot <= 8) hot[q.hot - 1] = q.ms / 1000;
  const mem = c.memory.slice().sort((a, b) => a.ms - b.ms)[0];
  return { cue: mem ? mem.ms / 1000 : null, hot };
}
function copyDevicePlaylist(r) {
  const d = PL.devices.find((x) => x.id === r.dev), n = d && d.tree.find((x) => x.id === r.id);
  if (!n) return;
  const p = plNew(n.name);
  plAdd(p, n.tracks.map((rid) => d.byRbId.get(rid)).filter(Boolean));
  status(`Copied "${n.name}" to your playlists (${p.items.length} tracks). It plays from ${d.name} while that's plugged in.`);
}

// ---- rekordbox XML ----
function xmlMenu(btn) {
  popMenu(btn, [
    ["Import rekordbox XML…", () => $("#xmlInput").click()],
    ["Export to rekordbox XML…", exportXml],
    ["Music folder path for export…", askBasePath],
  ]);
}
function askBasePath() {
  const cur = pref("cb.basePath", "");
  const v = prompt(`Where is "${rootFolderName() || "your music folder"}" on this computer? rekordbox needs full paths, e.g. C:\\Users\\you\\Music`, cur);
  if (v != null) setPref("cb.basePath", v.trim().replace(/[\\/]+$/, ""));
}
function rootFolderName() { const t = lib.tracks.find((x) => !x.device && !x.stored && x.rel); return t ? t.rel.split("/")[0] : ""; }
async function importXml(file) {
  let x;
  try { x = RB.parseXml(await file.text()); } catch (e) { return status("Couldn't read that file: " + e.message, 8000); }
  // match rekordbox's tracks to files Cratebox knows (file name + size, then file name)
  const byFile = new Map();
  for (const t of lib.tracks) {
    if (t.device) continue;
    const f = (t.name || "").toLowerCase();
    byFile.set(f + "|" + t.size, t); if (!byFile.has(f)) byFile.set(f, t);
  }
  const resolved = new Map();
  let matched = 0, applied = 0;
  for (const [rid, r] of x.tracks) {
    const f = (r.filename || "").toLowerCase(), t = byFile.get(f + "|" + r.size) || byFile.get(f);
    if (t) { matched++; resolved.set(rid, t); if (applyRekordboxTrack(t, r)) applied++; }
    else resolved.set(rid, { id: "rbx|" + r.filename + "|" + r.size, missing: true, title: r.title, artist: r.artist, name: r.filename, size: r.size });
  }
  // playlists go into a folder of their own
  const stamp = new Date().toLocaleDateString();
  const top = plNew(`rekordbox (${stamp})`, true);
  const made = new Map();
  for (const n of x.playlists) {
    const parent = n.parent == null ? top.id : made.get(n.parent);
    const p = plNew(n.name, n.folder, parent);
    made.set(n.key, p.id);
    if (!n.folder) {
      for (const rid of n.tracks) {
        const t = resolved.get(rid);
        if (!t) continue;
        p.items.push(t.id);
        p.meta[t.id] = t.missing ? { title: t.title, artist: t.artist, file: t.name, size: t.size } : metaOf(t);
      }
      plSave(p);
    }
  }
  PL.open.add(top.id);
  renderTree(); applyView(true);
  status(`rekordbox XML: ${x.tracks.size} tracks (${matched} found in your folders, grids/cues/keys taken from rekordbox for ${applied}), ${x.playlists.filter((p) => !p.folder).length} playlists`, 12000);
}
// take rekordbox's grid, key and cues for a track (your own Cratebox edits win)
function applyRekordboxTrack(t, r) {
  let did = false;
  if (r.grid && r.grid.bpm > 0 && !t.gridManual) {
    const spb = 60 / r.grid.bpm;
    let first = r.grid.firstBeat - ((r.grid.beat || 1) - 1) * spb;       // back to the downbeat
    const bar = 4 * spb;
    first -= Math.floor(first / bar) * bar;
    t.bpm = r.grid.bpm; t.firstBeat = first; t.gridManual = true; t.gridFrom = "rekordbox";
    if (!t.autoBpm) { t.autoBpm = t.bpm; t.autoFirst = first; }
    did = true;
  }
  const k = RB.keyIndex(r.key);
  if (k >= 0) { t.key = k; t.keyFrom = "rekordbox"; did = true; }
  if (!t.duration && r.duration) t.duration = r.duration;
  if (r.marks.length) {
    const have = localStorage.getItem(trackKey(t));
    if (!have) {
      const hot = new Array(8).fill(null);
      for (const m of r.marks) if (m.num >= 0 && m.num < 8) hot[m.num] = m.start;
      const mem = r.marks.filter((m) => m.num === -1).sort((a, b) => a.start - b.start)[0];
      try { localStorage.setItem(trackKey(t), JSON.stringify({ cue: mem ? mem.start : null, hot })); } catch (e) {}
      did = true;
    }
  }
  if (did) {
    saveAnalysis(t);
    // not analysed yet: the analysis still runs (length, phrases) but keeps rekordbox's grid and key
    if (!analysisCurrent(t) && !lib.queue.includes(t)) { lib.queue.push(t); runAnalysisQueue(); }
  }
  return did;
}
function xmlEsc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
function exportXml() {
  const base = pref("cb.basePath", "");
  if (!base && lib.tracks.some((t) => !t.device && !t.stored)) {
    askBasePath();
    if (!pref("cb.basePath", "")) return status("Export needs the music folder's location on this computer", 8000);
  }
  const root = pref("cb.basePath", "").replace(/\\/g, "/");
  const own = lib.tracks.filter((t) => !t.device);
  const tid = new Map(own.map((t, i) => [t.id, i + 1]));
  const loc = (t) => {
    // the picked folder's name is the first part of rel; the base path is where that folder lives
    const rel = t.rel.split("/").slice(1).join("/"), full = root ? `${root}/${rel}` : rel;
    return "file://localhost/" + encodeURI(full.replace(/^\/+/, "")).replace(/#/g, "%23").replace(/\?/g, "%3F");
  };
  const out = ['<?xml version="1.0" encoding="UTF-8"?>', '<DJ_PLAYLISTS Version="1.0.0">', '  <PRODUCT Name="Cratebox" Version="1" Company="Cratebox"/>', `  <COLLECTION Entries="${own.length}">`];
  for (const t of own) {
    const c = loadCues(t), attrs = { TrackID: tid.get(t.id), Name: t.title, Artist: t.artist, Kind: (t.name || "").split(".").pop().toUpperCase() + " File",
      Size: t.size || 0, TotalTime: Math.round(t.duration || 0), AverageBpm: (t.bpm || 0).toFixed(2), Tonality: RB.keyName(t.key), Location: loc(t) };
    out.push(`    <TRACK ${Object.entries(attrs).map(([k, v]) => `${k}="${xmlEsc(v)}"`).join(" ")}>`);
    if (t.bpm && t.firstBeat != null) out.push(`      <TEMPO Inizio="${t.firstBeat.toFixed(3)}" Bpm="${t.bpm.toFixed(2)}" Metro="4/4" Battito="1"/>`);
    if (c.cue != null) out.push(`      <POSITION_MARK Name="" Type="0" Start="${c.cue.toFixed(3)}" Num="-1"/>`);
    c.hot.forEach((v, i) => { if (v != null) out.push(`      <POSITION_MARK Name="" Type="0" Start="${v.toFixed(3)}" Num="${i}"/>`); });
    out.push("    </TRACK>");
  }
  out.push("  </COLLECTION>", "  <PLAYLISTS>");
  const node = (parent, ind) => {
    const kids = PL.lists.filter((x) => x.parent === parent).sort((a, b) => a.order - b.order);
    for (const p of kids) {
      if (p.folder) { out.push(`${ind}<NODE Type="0" Name="${xmlEsc(p.name)}" Count="${PL.lists.filter((x) => x.parent === p.id).length}">`); node(p.id, ind + "  "); out.push(`${ind}</NODE>`); }
      else {
        const items = p.items.filter((id) => tid.has(id));
        out.push(`${ind}<NODE Name="${xmlEsc(p.name)}" Type="1" KeyType="0" Entries="${items.length}">`);
        for (const id of items) out.push(`${ind}  <TRACK Key="${tid.get(id)}"/>`);
        out.push(`${ind}</NODE>`);
      }
    }
  };
  out.push(`    <NODE Type="0" Name="ROOT" Count="${PL.lists.filter((x) => !x.parent).length}">`);
  node(null, "      ");
  out.push("    </NODE>", "  </PLAYLISTS>", "</DJ_PLAYLISTS>");
  const a = h("a", { href: URL.createObjectURL(new Blob([out.join("\n")], { type: "application/xml" })), download: "cratebox-rekordbox.xml" });
  document.body.append(a); a.click(); a.remove();
  status(`Exported ${own.length} tracks and ${PL.lists.filter((x) => !x.folder).length} playlists. In rekordbox: Preferences → Advanced → Imported Library = this file, and tick rekordbox xml under View → Layout.`, 12000);
}

// toolbar
$("#addToBtn").addEventListener("click", (e) => addToMenu(e.currentTarget));
$("#plRemove").addEventListener("click", removeFromPlaylist);
$("#xmlInput").addEventListener("change", (e) => { const f = e.target.files[0]; e.target.value = ""; if (f) importXml(f); });
$("#treeBtn").addEventListener("click", (e) => { e.stopPropagation(); $("#library").classList.toggle("treeopen"); });
document.addEventListener("pointerdown", (e) => {
  if ($("#library").classList.contains("treeopen") && !e.target.closest("#tree, #treeBtn, .popmenu")) $("#library").classList.remove("treeopen");
});
$("#tree").addEventListener("pointerdown", () => { if (PL.focus !== "tree") return; PL.focus = "list"; });
