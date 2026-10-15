"""Turn Mixxx controller mappings (MIDI XML) into Cratebox controller profiles.

Mixxx's mappings record which MIDI message each control sends; this keeps those facts (status
byte, note/CC number, which deck) and translates Mixxx's control names into Cratebox actions.
Usage: python tools/mixxx2cratebox.py <out.js> <profile-id>=<mapping.xml> ...
"""
import json
import re
import sys
import xml.etree.ElementTree as ET

LOOP_SIZES = [0.25, 0.5, 1, 2, 4, 8, 16, 32]
JUMPS = [-1, 1, -2, 2, -4, 4, -8, 8]


def deck_of(group):
    m = re.search(r"\[Channel(\d)\]", group)
    if not m:
        return None
    return (int(m.group(1)) - 1) % 2          # Cratebox has two decks: 3 -> 1, 4 -> 2


def translate(group, key, status, midino, opts, lsb_of):
    """Return (action, deck) or None. deck -1 = global."""
    k = key.lower()
    d = deck_of(group)
    is_note = (status & 0xF0) in (0x80, 0x90)
    is_cc = (status & 0xF0) == 0xB0
    num = [int(x) for x in re.findall(r"\d+", key.split(".")[-1] if "." in key else key)]
    pad = midino & 7

    if "sampler" in group.lower() or "previewdeck" in group.lower():
        return None
    # ---- library / global
    if re.search(r"movevertical|rotaryselector$|select_track_knob|select_turn|selecttrackknob", k) and is_cc:
        return ("browse", -1)
    if re.search(r"shiftedrotaryselector$", k) and is_cc:
        return ("browse", -1)
    if re.search(r"rotaryselectorclick$|movefocusforward|select_push", k) and is_note:
        return ("browsePress", -1)
    if re.search(r"selectnexttrack", k):
        return ("browseDown", -1)
    if re.search(r"selectprevtrack", k):
        return ("browseUp", -1)
    if re.search(r"waveformzoom", k):
        return ("zoom", -1)
    if re.search(r"crossfader(msb)?$", k) and "curve" not in k:
        return ("xfader", -1)
    if re.search(r"headmix", k):
        return ("headMix", -1)
    if d is None:
        return None
    # ---- per deck
    if re.search(r"loadselectedtrack$|loadbutton", k):
        return ("load", d)
    if re.search(r"hotcue_\d+_clear|hotcue\d+clear", k):
        return (f"hotClear:{num[0] - 1}", d) if num else None
    if re.search(r"clearhotcuebuttons", k):
        return (f"hotClear:{pad}", d)
    if re.search(r"hotcue_\d+_activate|hotcue\d+activate", k):
        return (f"hot:{num[0] - 1}", d) if num else None
    if re.search(r"hotcuebuttons", k):
        return (f"hot:{pad}", d)
    m = re.search(r"beatloop_([\d.]+)_(toggle|activate)", k)
    if m:
        return (f"loop:{float(m.group(1)):g}", d)
    if re.search(r"beatloopbuttons$|beatlooprollbuttons$|autoloop.*beatloopbutton", k):
        return (f"loop:{LOOP_SIZES[pad]:g}", d)
    m = re.search(r"beatjump_(\d+)_(forward|backward)", k)
    if m:
        n = int(m.group(1))
        return (f"jump:{n if m.group(2) == 'forward' else -n}", d)
    if re.search(r"beatjumppadpressed", k):
        return (f"jump:{JUMPS[pad]}", d)
    if re.search(r"play_?stutter", k):
        return ("playCue", d)
    if re.search(r"(^|\.)play$|playbutton|deck\[\d\]\.playbutton|(^|\.)play\b", k) and "start" not in k and is_note:
        return ("play", d)
    if re.search(r"headphoneshiftcuebutton", k):
        return None
    if re.search(r"headphonecuebutton$|(^|\.)pfl$|toogleheadphone", k):
        return ("pfl", d)
    if re.search(r"cue_default|cuedefault|cuebutton", k):
        return ("cue", d)
    if re.search(r"jumptobeginning|^start$|(^|\.)start_?stop$|cue_gotoandstop|cuegotoandstop", k):
        return ("start", d)
    if re.search(r"synclongpressed", k):
        return ("syncOn", d)
    if re.search(r"sync(pressed|button|enabled|enable|\.input)?$|beatsync$|sync_enabled", k) and "disable" not in k:
        return ("sync", d)
    if re.search(r"cycletemporange|tempo_btn|settemporange", k):
        return ("range", d)
    if re.search(r"keylock(button)?$", k) and "shift" not in k:
        return ("keylock", d)
    if re.search(r"quantize", k):
        return ("quant", d)
    if re.search(r"headphonecuebutton$|(^|\.)pfl$|toogleheadphone", k):
        return ("pfl", d)
    # jog wheels: touch is a note, turning is a CC
    if is_note and re.search(r"jogtouch|(^|\.)touch$|jogscratchtouch|scratch\d?_enable|jogseektouch", k):
        return ("touch", d)
    if is_cc and re.search(r"jog|scratch|wheel|seek$", k):
        if re.search(r"shift|search|seek", k):
            return ("jogSearch", d)
        if re.search(r"platter|scratchturn|jog_scratch|(^|\.)scratch$", k):
            return ("jogTop", d)
        if midino in (0x22, 0x23):           # Pioneer DDJ: 0x22/0x23 = top of the platter
            return ("jogTop", d)
        if midino in (0x29, 0x26, 0x1f):
            return ("jogSearch", d)
        return ("jogSide", d)
    # tempo, faders, knobs (14-bit aware: LSB entries are folded in later)
    if re.search(r"tempo(slider|fader)|(^|\.)rate(msb|lsb)?$", k) and is_cc:
        return ("tempo", d)
    if re.search(r"(^|\.)volume(msb|lsb)?$|deckfader", k):
        return ("fader", d)
    if re.search(r"(^|\.)pregain$|gainknob|(^|\.)gain$", k):
        return ("trim", d)
    if "equalizerrack" in group.lower():
        m = re.search(r"parameter(\d)", k)
        if m:
            return ({"3": "hi", "2": "mid", "1": "low"}.get(m.group(1)), d)
        if "eq" in k:   # DDJ-200 style script: one function for all three, by CC number
            return ({0x07: "hi", 0x0B: "mid", 0x0F: "low"}.get(midino & ~0x20), d)
    m = re.search(r"eqknob\[(\d)\]", k)
    if m:
        return ({"3": "hi", "2": "mid", "1": "low"}[m.group(1)], d)
    if re.search(r"filterhigh", k):
        return ("hi", d)
    if re.search(r"filtermid", k):
        return ("mid", d)
    if re.search(r"filterlow", k):
        return ("low", d)
    if ("quickeffectrack" in group.lower() and "super1" in k) or re.search(r"quickeffectknob|filterknob(msb|lsb)?$|(^|\.)super1$", k):
        return ("cfx", d)
    # loops and jumps
    if re.search(r"loop_in$|loopinbutton$|(^|\.)loopin$", k):
        return ("loopIn", d)
    if re.search(r"loop_out$|loopoutbutton$", k):
        return ("loopOut", d)
    if re.search(r"reloop_andstop", k):
        return ("reloopStop", d)
    if re.search(r"reloop_toggle|reloop_exit|loopexitbutton|reloopbutton|loopactivebutton", k):
        return ("reloop", d)
    if re.search(r"loop_halve|loophalvebutton|beatloophalvebutton|togglelooopadjustin", k):
        return ("loopHalf", d)
    if re.search(r"loop_double|loopdoublebutton|beatloopdoublebutton", k):
        return ("loopDouble", d)
    if re.search(r"cueloopcallleft", k):
        return ("callPrev", d)
    if re.search(r"cueloopcallright", k):
        return ("callNext", d)
    if re.search(r"quickjumpback|beatjump_backward|loopmovebackbutton|loop_move_\d+_backward", k):
        return ("jump:-4", d)
    if re.search(r"quickjumpforward|beatjump_forward|loopmoveforwardbutton|loop_move_\d+_forward", k):
        return ("jump:4", d)
    # pad modes
    if re.search(r"hotcuemode|togglehotcuemode|sethotcuemode", k):
        return ("mode:hotcue", d)
    if re.search(r"beatjumpmode", k):
        return ("mode:beatjump", d)
    if re.search(r"togglebeatloopmode|autoloopmode|beatloopmode", k):
        return ("mode:beatloop", d)
    return None


def convert(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    # some community files have a second document glued on the end
    second = txt.find("<?xml", 10)
    if second > 0:
        txt = txt[:second]
    root = ET.fromstring(txt)
    rows = []
    for c in root.iter("control"):
        g = (c.findtext("group") or "").strip()
        k = (c.findtext("key") or "").strip()
        try:
            st = int((c.findtext("status") or "").strip(), 16)
            no = int((c.findtext("midino") or "").strip(), 16)
        except ValueError:
            continue
        opts = [o.tag.lower() for o in c.find("options")] if c.find("options") is not None else []
        rows.append((st, no, g, k, opts))
    # 14-bit pairs: an LSB control for the same thing sits at midino + 0x20
    lsb_keys = {(st, no) for st, no, g, k, o in rows if "fourteen-bit-lsb" in o or re.search(r"lsb$", k.lower())}
    out, seen = [], set()
    for st, no, g, k, o in rows:
        if (st, no) in lsb_keys:
            continue
        r = translate(g, k, st, no, o, lsb_keys)
        if not r or not r[0]:
            continue
        action, deck = r
        if (st, no) in seen:
            continue
        seen.add((st, no))
        lsb = no + 0x20 if (st, no + 0x20) in lsb_keys and (st & 0xF0) == 0xB0 else 0
        out.append([st, no, action, deck, lsb])
    return out


if __name__ == "__main__":
    profiles = {}
    for arg in sys.argv[2:]:
        pid, path = arg.split("=", 1)
        profiles.setdefault(pid, [])
        have = {(e[0], e[1]) for e in profiles[pid]}
        profiles[pid] += [e for e in convert(path) if (e[0], e[1]) not in have]
    with open(sys.argv[1], "w") as f:
        f.write("// generated by tools/mixxx2cratebox.py from Mixxx's controller mappings (mixxx.org)\n")
        f.write("const MIXXX_MAPS = " + json.dumps(profiles, separators=(",", ":")) + ";\n")
    for pid, rows in profiles.items():
        acts = sorted({r[2].split(":")[0] for r in rows})
        print(f"{pid:12s} {len(rows):4d} messages  {', '.join(acts)}")
