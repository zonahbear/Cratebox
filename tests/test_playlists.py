"""Playlists, rekordbox USB/SD devices and rekordbox XML, in headless Chromium.

Builds playlists with the mouse (new, rename, add by menu and by drag, reorder, remove, folders, delete),
checks they survive a reload, imports and exports rekordbox XML, mounts a real rekordbox USB export
(tests/fixtures/rekordbox_usb) through a stand-in for the browser's folder picker, loads a track off
it, and drives the tree with the FLX4's browse knob.

    python tests/test_playlists.py
"""
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cratebox as T  # noqa: E402

MUSIC = os.path.join(T.ROOT, "tests", "music")
NAMES = sorted(os.listdir(MUSIC))
HOUSE = "Test Artist - House Groove 126.wav"

ADD = """async (names) => {
  const files = [];
  for (const n of names) files.push({ file: new File([await (await fetch('tests/music/' + encodeURIComponent(n))).blob()], n, { lastModified: 1 }), rel: 'music/' + n });
  await cratebox.addFiles(files); }"""

# a stand-in for showDirectoryPicker()'s handle, serving the fixture export over HTTP. The audio on
# the "stick" is two of the test tracks. Demo Track 1's .EXT gets a PCO2 cue list added (hot cues A
# and C, a memory cue), since the fixture has no cues of its own.
MOCK_USB = """async () => {
  const U = 'tests/fixtures/rekordbox_usb', files = new Map();
  const add = (p, url, fix) => files.set(p, { url, fix });
  add('PIONEER/rekordbox/export.pdb', U + '/PIONEER/rekordbox/export.pdb');
  for (const a of ['P016/0000875E', 'P053/0001D21F', 'P017/00009B77', 'P021/00006D2B', 'P019/00020AA9', 'P043/00011517'])
    for (const x of ['DAT', 'EXT']) add(`PIONEER/USBANLZ/${a}/ANLZ0000.${x}`, `${U}/PIONEER/USBANLZ/${a}/ANLZ0000.${x}`, a === 'P016/0000875E' && x === 'EXT');
  add('Contents/Loopmasters/UnknownAlbum/Demo Track 1.mp3', 'tests/music/' + encodeURIComponent('Test Artist - House Groove 126.wav'));
  add('Contents/Loopmasters/UnknownAlbum/Demo Track 2.mp3', 'tests/music/' + encodeURIComponent('Bass Lab - Halftime Wobble 140.wav'));
  const cueTag = () => {
    const ent = (hot, ms) => { const e = new DataView(new ArrayBuffer(0x38)); [0x50, 0x43, 0x50, 0x32].forEach((c, i) => e.setUint8(i, c));
      e.setUint32(4, 0x10); e.setUint32(8, 0x38); e.setUint32(12, hot); e.setUint8(16, 1); e.setUint32(20, ms); e.setUint32(24, 0xffffffff); return new Uint8Array(e.buffer); };
    const list = (hotList, ents) => { const n = 20 + ents.reduce((a, e) => a + e.length, 0), b = new Uint8Array(n), v = new DataView(b.buffer);
      [0x50, 0x43, 0x4f, 0x32].forEach((c, i) => b[i] = c); v.setUint32(4, 20); v.setUint32(8, n); v.setUint32(12, hotList ? 1 : 0); v.setUint16(16, ents.length);
      let o = 20; for (const e of ents) { b.set(e, o); o += e.length; } return b; };
    const a = list(true, [ent(1, 2000), ent(3, 9000)]), m = list(false, [ent(0, 500)]);
    const out = new Uint8Array(a.length + m.length); out.set(a); out.set(m, a.length); return out;
  };
  const dir = (path, name) => ({
    kind: 'directory', name,
    async getDirectoryHandle(n) { const p = path ? path + '/' + n : n; if (![...files.keys()].some((k) => k.startsWith(p + '/'))) throw new DOMException('no ' + p, 'NotFoundError'); return dir(p, n); },
    async getFileHandle(n) {
      const p = path ? path + '/' + n : n, f = files.get(p);
      if (!f) throw new DOMException('no ' + p, 'NotFoundError');
      return { kind: 'file', name: n, async getFile() {
        let b = new Uint8Array(await (await fetch(f.url)).arrayBuffer());
        if (f.fix) { const c = cueTag(), o = new Uint8Array(b.length + c.length); o.set(b); o.set(c, b.length); new DataView(o.buffer).setUint32(8, o.length); b = o; }
        return new File([b], n);
      } };
    },
    async queryPermission() { return 'granted'; },
  });
  await cratebox.mountDevice(dir('', 'SANDISK'), false);
}"""


def tree(page):
    return page.evaluate("[...document.querySelectorAll('#tree .trow2 .nm')].map(e => e.textContent)")


def view_titles(page):
    return page.evaluate("cratebox.lib.view.map(t => t.title)")


def tree_row(page, name):
    return page.locator("#tree .trow2", has=page.locator(".nm", has_text=name)).first


def start(page, names=NAMES):
    page.goto(f"http://127.0.0.1:{T.PORT}/cratebox.html")
    page.click("#startBtn")
    page.wait_for_function("window.cratebox.A.ctx && window.cratebox.A.decks.length >= 2")
    page.evaluate(ADD, names)
    page.wait_for_function(f"cratebox.lib.tracks.length >= {len(names)}")


def main():
    T.PORT = 8627
    srv = T.serve()
    check = T.check
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        start(page)
        check("tree shows the collection, with no playlists yet", tree(page) == ["Collection"], str(tree(page)))

        # ---- new playlist: + then type a name
        page.click("#tree .thead button[title='New playlist']")
        page.keyboard.press("Control+A"); page.keyboard.type("Bangers"); page.keyboard.press("Enter")
        st = page.evaluate("({ v: cratebox.PL.view, n: document.querySelector('#viewName').textContent, lists: cratebox.PL.lists.map(p => p.name) })")
        check("new playlist: named, and opened", st["lists"] == ["Bangers"] and st["v"]["kind"] == "pl" and st["n"] == "Bangers", str(st))
        bangers = page.evaluate("cratebox.PL.lists[0].id")

        # ---- add with the menu: Ctrl-click two rows in the collection
        tree_row(page, "Collection").click()
        rows = page.locator("#list .trow")
        rows.nth(0).click(); rows.nth(2).click(modifiers=["Control"])
        check("Ctrl-click selects two rows", page.evaluate("cratebox.lib.selIds.size") == 2)
        page.click("#addToBtn")
        page.locator(".popmenu button", has_text="Bangers").click()
        first_two = page.evaluate("[cratebox.lib.view[0].title, cratebox.lib.view[2].title]")
        items = page.evaluate(f"cratebox.plGet('{bangers}').items.length")
        check("Add to ▾ adds the selection", items == 2, f"{items} items")

        # ---- add by dragging a row onto the playlist in the tree
        third = page.evaluate("cratebox.lib.view[1].title")
        rows.nth(1).click()
        rows.nth(1).drag_to(tree_row(page, "Bangers"))
        items = page.evaluate(f"cratebox.plGet('{bangers}').items.length")
        check("dragging a row onto a playlist adds it", items == 3, f"{items} items")

        # ---- open it: playlist order, then rearrange by dragging
        tree_row(page, "Bangers").click()
        order = view_titles(page)
        check("playlist shows its tracks in the order they were added", order == first_two + [third], str(order))
        rows.nth(0).drag_to(rows.nth(2), target_position={"x": 40, "y": 20})
        order2 = view_titles(page)
        check("drag a row to rearrange the playlist", order2 == [order[1], order[2], order[0]], str(order2))
        nums = page.evaluate("[...document.querySelectorAll('#list .trow .n')].map(e => e.textContent)")
        check("# column numbers the playlist", nums[:3] == ["1", "2", "3"], str(nums))

        # ---- Delete key removes from the playlist (not from the collection)
        rows.nth(0).click()
        page.keyboard.press("Delete")
        order3 = view_titles(page)
        n_all = page.evaluate("cratebox.lib.tracks.length")
        check("Delete removes the selected row from the playlist only", order3 == order2[1:] and n_all == len(NAMES), f"{order3}, collection {n_all}")

        # ---- rename (double-click), a folder, and moving the playlist into it
        tree_row(page, "Bangers").dblclick()
        page.keyboard.press("Control+A"); page.keyboard.type("Peak time"); page.keyboard.press("Enter")
        page.click("#tree .thead button[title='New folder']")
        page.keyboard.press("Control+A"); page.keyboard.type("Saturday"); page.keyboard.press("Enter")
        tree_row(page, "Peak time").drag_to(tree_row(page, "Saturday"))
        st = page.evaluate("cratebox.PL.lists.map(p => [p.name, p.folder, p.parent ? cratebox.plGet(p.parent).name : null])")
        check("rename + folder + drag a playlist into the folder", sorted(st) == sorted([["Peak time", False, "Saturday"], ["Saturday", True, None]]), str(st))
        check("tree shows the playlist inside the open folder", tree(page) == ["Collection", "Saturday", "Peak time"], str(tree(page)))
        page.click("#tree .thead button[title='New playlist']")
        page.keyboard.press("Control+A"); page.keyboard.type("Throwaway"); page.keyboard.press("Enter")
        page.wait_for_timeout(400)          # playlists save a moment after a change

        # ---- survives a reload
        page.reload()
        start(page)
        page.wait_for_function("cratebox.PL.lists.length === 3")
        tree_row(page, "Peak time").click()
        check("after a reload: folder, playlist and its order are back", view_titles(page) == order3 and tree(page) == ["Collection", "Saturday", "Peak time", "Throwaway"],
              f"{view_titles(page)} {tree(page)}")

        # ---- delete a playlist (× then confirm)
        r = tree_row(page, "Throwaway")
        r.hover(); r.locator(".tx").click()
        page.click(".tconfirm .danger")
        check("× + Delete removes a playlist", "Throwaway" not in tree(page) and page.evaluate("cratebox.PL.lists.length") == 2, str(tree(page)))

        # ---- rekordbox XML import
        size = os.path.getsize(os.path.join(MUSIC, HOUSE))
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<DJ_PLAYLISTS Version="1.0.0"><PRODUCT Name="rekordbox" Version="6.8.5" Company="AlphaTheta"/>
<COLLECTION Entries="2">
<TRACK TrackID="11" Name="House Groove" Artist="Test Artist" Kind="WAV File" Size="{size}" TotalTime="60" AverageBpm="126.00" Tonality="Am"
 Location="file://localhost/C:/Users/jonah/Music/Test%20Artist%20-%20House%20Groove%20126.wav">
 <TEMPO Inizio="0.367" Bpm="126.00" Metro="4/4" Battito="1"/>
 <POSITION_MARK Name="" Type="0" Start="0.367" Num="-1"/>
 <POSITION_MARK Name="drop" Type="0" Start="15.600" Num="0" Red="40" Green="226" Blue="20"/>
 <POSITION_MARK Name="" Type="0" Start="30.000" Num="3"/>
</TRACK>
<TRACK TrackID="12" Name="Ghost Track" Artist="Nobody" Kind="MP3 File" Size="12345" TotalTime="200" AverageBpm="140.00" Tonality="8A"
 Location="file://localhost/C:/Users/jonah/Music/ghost.mp3"><TEMPO Inizio="0.1" Bpm="140.00" Metro="4/4" Battito="1"/></TRACK>
</COLLECTION>
<PLAYLISTS><NODE Type="0" Name="ROOT" Count="2">
 <NODE Type="0" Name="Bass" Count="1"><NODE Name="Wobbles" Type="1" KeyType="0" Entries="2"><TRACK Key="11"/><TRACK Key="12"/></NODE></NODE>
 <NODE Name="Warmup" Type="1" KeyType="0" Entries="1"><TRACK Key="11"/></NODE>
</NODE></PLAYLISTS></DJ_PLAYLISTS>"""
        tmp = tempfile.mkdtemp()
        xp = os.path.join(tmp, "rekordbox.xml")
        with open(xp, "w") as f:
            f.write(xml)
        page.set_input_files("#xmlInput", xp)
        page.wait_for_function("cratebox.PL.lists.some(p => p.name === 'Wobbles')")
        st = page.evaluate("""(() => { const P = cratebox.PL.lists, by = (n) => P.find(p => p.name === n), up = (p) => p.parent ? cratebox.plGet(p.parent).name : null;
            const w = by('Wobbles'), b = by('Bass'), top = cratebox.plGet(b.parent);
            return { w: up(w), b: up(b), top: top.name, topFolder: top.folder, warm: up(by('Warmup')), n: w.items.length }; })()""")
        check("XML playlists land in a 'rekordbox (date)' folder, nesting kept", st["w"] == "Bass" and st["b"].startswith("rekordbox (") and st["topFolder"] and st["warm"] == st["top"] and st["n"] == 2, str(st))
        tree_row(page, "Wobbles").click()          # imported folders open themselves
        st = page.evaluate("cratebox.lib.view.map(t => [t.title, !!t.missing])")
        miss = page.evaluate("document.querySelectorAll('#list .trow.missing').length")
        check("XML playlist: the found track, and the one not on this computer greyed out", st == [["House Groove 126", False], ["Ghost Track", True]] and miss == 1, f"{st}, {miss} greyed")
        t = page.evaluate(f"""(() => {{ const t = cratebox.lib.tracks.find(t => t.name === {HOUSE!r});
            return {{ bpm: t.bpm, first: t.firstBeat, manual: t.gridManual, from: t.gridFrom, key: cratebox.camelot(t.key).label, cues: JSON.parse(localStorage.getItem('cb.cues.' + t.id)) }}; }})()""")
        check("XML: rekordbox's grid, key (Am = 8A) and cues taken for the matched track",
              t["bpm"] == 126 and abs(t["first"] - 0.367) < 1e-6 and t["manual"] and t["from"] == "rekordbox" and t["key"] == "8A"
              and t["cues"]["hot"][0] == 15.6 and t["cues"]["hot"][3] == 30 and abs(t["cues"]["cue"] - 0.367) < 1e-6, str(t))
        page.wait_for_function(f"(cratebox.lib.tracks.find(t => t.name === {HOUSE!r}).phrases || []).length > 0", timeout=60000)
        t2 = page.evaluate(f"(() => {{ const t = cratebox.lib.tracks.find(t => t.name === {HOUSE!r}); return [t.bpm, cratebox.camelot(t.key).label, t.phrases.length]; }})()")
        check("analysis afterwards adds phrases but keeps rekordbox's grid and key", t2[0] == 126 and t2[1] == "8A" and t2[2] > 0, str(t2))
        page.evaluate("cratebox.lib.sel = cratebox.lib.view.findIndex(t => t.missing)")
        page.evaluate("cratebox.loadSelected(0)")
        check("loading a missing track says so instead of failing", "isn't in a connected folder" in page.inner_text("#status") and not page.evaluate("cratebox.decks[0].track"))

        # ---- rekordbox XML export
        page.evaluate("localStorage.setItem('cb.basePath', 'C:\\\\Users\\\\jonah\\\\Music')")
        with page.expect_download() as dl:
            page.evaluate("cratebox.exportXml()")
        out = os.path.join(tmp, "out.xml")
        dl.value.save_as(out)
        root = ET.parse(out).getroot()
        tracks = root.findall("COLLECTION/TRACK")
        house = next(t for t in tracks if t.get("Name") == "House Groove 126")
        loc_ok = house.get("Location") == "file://localhost/C:/Users/jonah/Music/Test%20Artist%20-%20House%20Groove%20126.wav"
        marks = {m.get("Num"): float(m.get("Start")) for m in house.findall("POSITION_MARK")}
        tempo = house.find("TEMPO")
        check("XML export: every track, rekordbox-style Location, grid, key, cues",
              len(tracks) == len(NAMES) and loc_ok and tempo is not None and float(tempo.get("Bpm")) == 126 and house.get("Tonality") == "Am"
              and marks.get("0") == 15.6 and marks.get("-1") == 0.367, f"{len(tracks)} tracks, {house.get('Location')}, {marks}")
        nodes = {n.get("Name"): n for n in root.iter("NODE")}
        pk = nodes.get("Peak time")
        id2name = {t.get("TrackID"): t.get("Name") for t in tracks}
        pk_titles = [id2name[k.get("Key")] for k in pk.findall("TRACK")] if pk is not None else None
        check("XML export: playlist tree and order (missing tracks left out)",
              nodes.get("Saturday") is not None and nodes["Saturday"].get("Type") == "0" and pk is not None and pk_titles == order3
              and len(nodes["Wobbles"].findall("TRACK")) == 1, f"{pk_titles} vs {order3}")

        # ---- rekordbox USB stick
        page.evaluate(MOCK_USB)
        page.wait_for_function("cratebox.PL.devices.length === 1")
        tr = tree(page)
        check("USB: device in the tree with its playlists and folder", tr[-3:] == ["SANDISK", "Playlist 1", "Folder"], str(tr))
        tree_row(page, "SANDISK").click()
        check("USB: device view lists its 6 tracks; the collection doesn't mix them in",
              len(view_titles(page)) == 6 and page.evaluate("cratebox.lib.tracks.filter(t => !t.device).length") == len(NAMES), str(view_titles(page)))
        tree_row(page, "Folder").click()
        tree_row(page, "Sub Playlist").click()
        check("USB: nested playlist opens, in rekordbox's order", view_titles(page) == ["Demo Track 1", "Demo Track 2"], str(view_titles(page)))
        check("USB: rows are read-only (no remove button)", page.is_hidden("#plRemove"))
        page.evaluate("cratebox.lib.sel = 0; cratebox.loadSelected(0)")
        page.wait_for_function("cratebox.decks[0].loaded && cratebox.decks[0].track.title === 'Demo Track 1'", timeout=60000)
        d = page.evaluate("""(() => { const d = cratebox.decks[0]; return { bpm: d.bpm, first: d.ana.firstBeat, rb: d.track.rbRead, ph: d.ana.phrases.length,
            ph0: d.ana.phrases[0], hot: d.hot.slice(0, 4), cue: d.cue, key: cratebox.camelot(d.ana.key).label }; })()""")
        check("USB track: rekordbox's grid (128 BPM, downbeat 25 ms), phrases, key Fm = 4A",
              d["bpm"] == 128 and abs(d["first"] - 0.025) < 1e-9 and d["rb"] and d["ph"] == 19 and d["key"] == "4A", str(d))
        check("USB track: rekordbox hot cues A and C and the memory cue", d["hot"][0] == 2 and d["hot"][2] == 9 and d["hot"][1] is None and d["cue"] == 0.5, str(d))
        r = tree_row(page, "Playlist 1")
        r.hover(); r.locator(".tx").click()
        cp = page.evaluate("(() => { const p = cratebox.PL.lists.find(p => p.name === 'Playlist 1' && !p.folder); return p && p.items.length; })()")
        check("USB: ⧉ copies a device playlist into your own", cp == 2, str(cp))

        # ---- FLX4 browse: press = tree/list, turn = move through the tree
        res = page.evaluate("""async () => {
          const C = cratebox; C.useProfile('ddj-flx4');
          const tbl = [...C.MIDI.table.values()], f = (a) => tbl.find(e => e[2] === a);
          const press = f('browsePress'), turn = f('browse'), out = {};
          C.setView({ kind: 'all' });
          C.midiIn([press[0], press[1], 127]); C.midiIn([press[0], press[1], 0]);
          out.focus1 = C.PL.focus;
          const names = []; for (let k = 0; k < 4; k++) { C.midiIn([turn[0], turn[1], 1]); names.push(document.querySelector('#viewName').textContent); }
          out.names = names;
          C.midiIn([press[0], press[1], 127]); C.midiIn([press[0], press[1], 0]);
          out.focus2 = C.PL.focus; out.view = document.querySelector('#viewName').textContent;
          C.setView({ kind: 'all' }); const ts = C.PL.treeSel;
          C.midiIn([turn[0], turn[1], 1]); out.listSel = C.lib.sel; out.treeKept = C.PL.treeSel === ts;
          return out; }""")
        check("FLX4: browse press moves to the tree, turning walks it, press again goes back to the list",
              res["focus1"] == "tree" and res["focus2"] == "list" and res["listSel"] == 1 and res["treeKept"] and res["names"][-2:] == ["Wobbles", "Warmup"], str(res))
        ctx.close()

        b.close()
    srv.shutdown()
    check("no JavaScript errors", not errors, "; ".join(errors[:3]))
    failed = [n for n, ok in T.checks if not ok]
    print(f"\n{len(T.checks) - len(failed)}/{len(T.checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
