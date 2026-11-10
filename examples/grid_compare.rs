//! Cratebox's own analysis against rekordbox's, on a rekordbox stick (or a folder copied from one):
//! BPM, how far the beats are apart, and whether bar 1 lands on the same beat. Reads only.
//!
//!     cargo run --release --example grid_compare -- /path/to/stick [bpm range index, default 3]
//!
//! Tracks whose audio file isn't there are skipped (so a partial copy works). A folder with no PIONEER in it
//! is taken as plain audio files: BPM and bar 1 (seconds) are printed for each.
use cratebox::analysis::{analyze, mono_for, Opts, BPM_RANGES};
use cratebox::rekordbox::{grid_from_beats, parse_anlz, parse_pdb};
use std::path::PathBuf;

fn main() {
    let root = PathBuf::from(std::env::args().nth(1).expect("the stick's folder"));
    let ri: usize = std::env::args().nth(2).and_then(|s| s.parse().ok()).unwrap_or(3);
    let range = (BPM_RANGES[ri].1, BPM_RANGES[ri].2);
    if !root.join("PIONEER").exists() {
        // a plain folder of audio: just print Cratebox's own BPM and bar 1 for each file
        let mut files: Vec<_> = std::fs::read_dir(&root).expect("folder").flatten().map(|e| e.path()).collect();
        files.sort();
        for p in files {
            let Ok(d) = cratebox::decode::decode(&p) else { continue };
            let (mono, fs) = mono_for(&[&d.l, &d.r], d.sr, 11025.0);
            let a = analyze(&mono, fs, None, range, Opts { no_wave: true, ..Default::default() });
            println!("{:8.3} | {:8.4} | {}", a.bpm, a.first_beat, p.file_name().unwrap().to_string_lossy());
        }
        return;
    }
    let pdb = parse_pdb(&std::fs::read(root.join("PIONEER/rekordbox/export.pdb")).expect("export.pdb")).expect("pdb");
    println!("range {}; columns: rekordbox BPM | Cratebox BPM | ratio | beat offset ms | bar offset beats | title", BPM_RANGES[ri].0);
    let (mut n, mut same, mut octave, mut other, mut beat_ok, mut bar_ok) = (0, 0, 0, 0, 0, 0);
    for t in &pdb.tracks {
        let p = root.join(t.path.trim_start_matches('/'));
        if t.anlz_path.is_empty() { continue; }
        let anlz = root.join(t.anlz_path.trim_start_matches('/'));
        if !p.exists() || !anlz.exists() { continue; }
        let Ok(d) = cratebox::decode::decode(&p) else { println!("couldn't decode {}", p.display()); continue };
        let a_rb = parse_anlz(&std::fs::read(&anlz).unwrap_or_default());
        let Some((rb, rf)) = grid_from_beats(&a_rb.beats) else { continue };
        let steady = a_rb.beats.iter().all(|b| (b.bpm - rb).abs() < 0.011);
        let (mono, fs) = mono_for(&[&d.l, &d.r], d.sr, 11025.0);
        let a = analyze(&mono, fs, None, range, Opts { no_wave: true, ..Default::default() });
        n += 1;
        if std::env::var("GRID_DUMP").is_ok() { println!("REF {{\"rb\":{},\"rf\":{},\"bpm\":{},\"fb\":{},\"steady\":{},\"title\":{:?}}}", rb, rf, a.bpm, a.first_beat, steady, t.title); }
        let ratio = a.bpm / rb;
        let kind = if (ratio - 1.0).abs() < 0.004 { same += 1; "same" } else if (ratio - 2.0).abs() < 0.008 || (ratio - 0.5).abs() < 0.002 { octave += 1; "half/double" } else { other += 1; "DIFFERENT" };
        // beats: where Cratebox's nearest beat sits against rekordbox's, at the middle of the track (on the faster grid)
        let (mut beat_ms, mut bar) = (f64::NAN, f64::NAN);
        if kind != "DIFFERENT" {
            let spb = 60.0 / a.bpm.max(rb);
            let mid = d.duration() / 2.0;
            let ph = |first: f64| { let x = (mid - first) / spb; x - x.floor() };
            let mut e = ph(a.first_beat) - ph(rf);
            e -= e.round();
            beat_ms = e * spb * 1000.0;
            if beat_ms.abs() < 25.0 { beat_ok += 1; }
            if kind == "same" {
                // bar 1: Cratebox's first_beat against rekordbox's first downbeat, in beats, 0..4
                let b = ((a.first_beat - rf) / (60.0 / rb)).round().rem_euclid(4.0).abs();
                bar = b;
                if b == 0.0 { bar_ok += 1; }
            }
        }
        println!("{:7.2} | {:7.2} | {:5.3} {:11} | {:6.1} | {:3} | {}{}", rb, a.bpm, ratio, kind, beat_ms, if bar.is_nan() { "-".into() } else { format!("{bar:.0}") }, t.title, if steady { "" } else { "  (rekordbox grid has tempo changes)" });
    }
    println!("\n{n} tracks: BPM same {same}, half/double {octave}, different {other}; beats within 25 ms {beat_ok} of {}; bar 1 on the same beat {bar_ok} of {same}", same + octave);
}
