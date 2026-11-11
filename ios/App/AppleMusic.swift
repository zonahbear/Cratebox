// AI mode (Settings → AI mode) and Apple's Music Understanding analysis.
//
// AI mode is one switch for every AI feature in the app, off by default: Ask the library (SmartSearch.swift,
// Apple Intelligence, iOS 26+) and Apple's Music Understanding (this file, iOS 27+). Both run on the device only;
// nothing is sent anywhere.
//
// Music Understanding (Apple, iOS 27): beats, bars, BPM, key over time, sections/segments/phrases, pace, where the
// vocals / drums / bass are, and loudness in LUFS. Here it runs in the background, one track at a time and only
// while nothing is playing, and its results are kept BESIDE Cratebox's own analysis: they never change a track's
// grid, key, phrases or cues (Cratebox's, rekordbox's or a hand-fixed grid stay in charge). Settings → AI mode →
// Compare shows how Apple's beats and bars sit against those grids, and exports it as a CSV, so the two can be
// judged on real tracks before Apple's results are used for anything.
//
// The framework is only in the iOS 27 SDK (Xcode 27). Built with an older Xcode, `canImport(MusicUnderstanding)`
// is false, this part compiles to "not in this build" and Settings says so.
import AVFoundation
import Combine
import CryptoKit
import Foundation
import CrateboxKit
#if canImport(MusicUnderstanding)
import MusicUnderstanding
#endif

enum AIMode {
    static let key = "cb.ai"
    static var on: Bool { UserDefaults.standard.bool(forKey: key) }
}

final class AppleMusic: ObservableObject {
    static let shared = AppleMusic()
    /// this build has the framework (made with the iOS 27 SDK)
    static var builtIn: Bool {
        #if canImport(MusicUnderstanding)
        return true
        #else
        return false
        #endif
    }
    static var osSupports: Bool { if #available(iOS 27, *) { return true } else { return false } }
    static var usable: Bool { builtIn && osSupports }
    /// why it can't run here, for Settings (nil when it can)
    static var unavailableReason: String? {
        if !builtIn { return "Not in this build: it was made with an Xcode older than 27, which doesn't have Apple's Music Understanding." }
        if !osSupports { return "Needs iOS 27 or later." }
        return nil
    }

    @Published private(set) var progress = ""
    @Published private(set) var analysed = 0
    weak var app: AppModel?
    /// what's been analysed (or failed): the file's size and date, and the format version
    struct Stamp: Codable { var size: Int64, mtime: Double, ver: Int, failed: String? }
    private var index = [String: Stamp]()
    private var cache = [String: AppleFeatures]()
    private var job: Task<Void, Never>?
    private var jobId: String?
    private var watch: Timer?
    private var retry: DispatchWorkItem?
    private var subs = Set<AnyCancellable>()
    private var deadFolder = [String: Double]()   // music folders found unreachable, and when
    private var saveWork: DispatchWorkItem?
    private let dir: URL

    private init() {
        dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("Cratebox/apple", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        if let d = try? Data(contentsOf: dir.appendingPathComponent("index.json")), let i = try? JSONDecoder().decode([String: Stamp].self, from: d) { index = i }
        analysed = index.values.filter { $0.failed == nil && $0.ver == AppleFeatures.VER }.count
    }
    func attach(_ app: AppModel) {
        self.app = app
        // new folders, a stick plugged in: look for tracks to analyse a few seconds after the list settles
        app.library.$tracks.debounce(for: .seconds(4), scheduler: RunLoop.main).sink { [weak self] _ in self?.kick() }.store(in: &subs)
        kick()
    }

    // ---- results ----
    private func file(_ id: String) -> URL {
        let h = SHA256.hash(data: Data(id.utf8)).prefix(12).map { String(format: "%02x", $0) }.joined()
        return dir.appendingPathComponent(h + ".json")
    }
    /// Apple's results for a track, if they're for the file as it is now
    func features(_ t: LibTrack) -> AppleFeatures? {
        guard let s = index[t.id], s.failed == nil, current(s, t) else { return nil }
        if let f = cache[t.id] { return f }
        guard let d = try? Data(contentsOf: file(t.id)), let f = try? JSONDecoder().decode(AppleFeatures.self, from: d) else { return nil }
        if cache.count > 200 { cache.removeAll() }      // a few hundred kB each: keep the memory bounded
        cache[t.id] = f
        return f
    }
    /// a stamp still describes the track's file (same size, same date when the library knows it, same format)
    private func current(_ s: Stamp, _ t: LibTrack) -> Bool {
        s.ver == AppleFeatures.VER && s.size == t.rec.size && (t.rec.mtime == 0 || s.mtime == 0 || abs(s.mtime - t.rec.mtime) < 1)
    }
    private func saveIndex() { if let d = try? JSONEncoder().encode(index) { try? d.write(to: dir.appendingPathComponent("index.json"), options: .atomic) } }

    // ---- the background queue ----
    private var playing: Bool { app?.core.decks.contains { $0.playing } ?? false }
    /// start the next track if AI mode is on, it's supported, nothing plays and nothing's running
    func kick() {
        retry?.cancel(); retry = nil
        guard AIMode.on, AppleMusic.usable, let app else { if !AIMode.on { stop() }; return }
        guard job == nil else { return }
        if playing {
            progress = "Waits while a deck plays"
            later(5); return
        }
        let todo = app.library.tracks.filter { t in index[t.id].map { !current($0, t) } ?? true }
        // a folder whose drive isn't there is asked once a minute, not once per track (resolving a bookmark to a
        // missing drive can take seconds, and this runs on the main thread)
        let now = Date().timeIntervalSince1970
        var found: (LibTrack, URL)?
        for t in todo {
            if t.device == nil, let since = deadFolder[t.rec.folder], now - since < 60 { continue }
            if let u = url(of: t) { found = (t, u); break }
            if t.device == nil { deadFolder[t.rec.folder] = now }
        }
        guard let next = found else {
            progress = todo.isEmpty ? "" : "\(todo.count) to do when their drives are connected"
            if !todo.isEmpty { later(60) }
            return
        }
        let (t, u) = next
        progress = "Analysing \(todo.count) track\(todo.count == 1 ? "" : "s") (Apple)…"
        let id = t.id, size = t.rec.size, mtime = t.rec.mtime
        jobId = id
        job = Task.detached(priority: .utility) { [weak self] in
            let r = await AppleMusic.run(u)
            await MainActor.run { self?.finished(id, size: size, mtime: mtime, r) }
        }
        // a deck starts playing: stop this track (it's done again later), so analysis never competes with the audio
        watch = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            if let self, self.playing { self.job?.cancel() }
        }
    }
    private func later(_ s: Double) {
        let w = DispatchWorkItem { [weak self] in self?.kick() }
        retry = w
        DispatchQueue.main.asyncAfter(deadline: .now() + s, execute: w)
    }
    func stop() {
        job?.cancel()
        progress = ""
    }
    private func finished(_ id: String, size: Int64, mtime: Double, _ r: Result<AppleFeatures, Error>) {
        let cancelled = job?.isCancelled ?? false
        watch?.invalidate(); watch = nil
        job = nil; jobId = nil
        switch r {
        case .success(var f):
            if f.size == 0 { f.size = size }
            if f.mtime == 0 { f.mtime = mtime }
            // the library's size and date win for the stamp (that's what `current` compares against)
            index[id] = Stamp(size: size, mtime: mtime, ver: AppleFeatures.VER, failed: nil)
            if let d = try? JSONEncoder().encode(f) { try? d.write(to: file(id), options: .atomic) }
            cache[id] = f
            analysed += 1
        case .failure(let e):
            if e is CancellationError || cancelled { progress = AIMode.on ? "Paused while a deck plays" : ""; later(5); return }
            index[id] = Stamp(size: size, mtime: mtime, ver: AppleFeatures.VER, failed: e.localizedDescription)
        }
        // the index is written a couple of seconds after the last change, not after every track
        saveWork?.cancel()
        let w = DispatchWorkItem { [weak self] in self?.saveIndex() }
        saveWork = w
        DispatchQueue.main.asyncAfter(deadline: .now() + 2, execute: w)
        objectWillChange.send()
        // a short breather between tracks (longer after a failure), so a run of quick failures can't keep the
        // main thread busy
        if case .failure = r { later(1) } else { later(0.3) }
    }
    private func url(of t: LibTrack) -> URL? { Devices.shared.url(for: t) ?? app?.library.fileURL(t) }
    /// forget everything (Settings), so it's all analysed again
    func clear() {
        job?.cancel()
        index = [:]; cache = [:]; analysed = 0; deadFolder = [:]
        try? FileManager.default.removeItem(at: dir)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        objectWillChange.send()
        kick()
    }
    var failedCount: Int { index.values.filter { $0.failed != nil }.count }

    // ---- the framework ----
    enum Failure: LocalizedError {
        case unsupported
        var errorDescription: String? { AppleMusic.unavailableReason ?? "Not available" }
    }
    static func run(_ url: URL) async -> Result<AppleFeatures, Error> {
        #if canImport(MusicUnderstanding)
        if #available(iOS 27, *) {
            do { return .success(try await analyse(url)) } catch { return .failure(error) }
        }
        #endif
        return .failure(Failure.unsupported)
    }

    #if canImport(MusicUnderstanding)
    @available(iOS 27, *)
    static func analyse(_ url: URL) async throws -> AppleFeatures {
        var f = AppleFeatures()
        let v = try? url.resourceValues(forKeys: [.fileSizeKey, .contentModificationDateKey])
        f.size = Int64(v?.fileSize ?? 0); f.mtime = v?.contentModificationDate?.timeIntervalSince1970 ?? 0
        f.analysedAt = Date().timeIntervalSince1970
        f.os = ProcessInfo.processInfo.operatingSystemVersionString
        let t0 = Date()
        // Apple: precise timing, or the results can be slightly off on compressed files
        let asset = AVURLAsset(url: url, options: [AVURLAssetPreferPreciseDurationAndTimingKey: true])
        let duration = (try? await asset.load(.duration))?.seconds ?? 0
        let session = try await MusicUnderstandingSession(asset: asset)
        let r = try await withTaskCancellationHandler {
            try await session.analyze(for: [.rhythm, .key, .structure, .pace, .instrumentActivity, .loudness])
        } onCancel: {
            Task { await session.cancel() }
        }
        try Task.checkCancellation()
        func sec(_ t: CMTime) -> Double { t.isNumeric ? t.seconds : 0 }
        func span(_ r: CMTimeRange, _ x: Double = 0) -> AppleFeatures.Span { .init(sec(r.start), sec(r.end), x) }
        if let rh = r.rhythm {
            f.bpm = rh.beatsPerMinute.map { Double($0) }
            f.beats = rh.beats.map(sec); f.bars = rh.bars.map(sec)
        }
        if let k = r.key { f.keys = k.ranges.map { span($0.range, Double(keyNumber($0.value))) } }
        if let st = r.structure {
            f.sections = st.sections.map { span($0) }; f.segments = st.segments.map { span($0) }; f.phrases = st.phrases.map { span($0) }
        }
        if let p = r.pace { f.pace = p.ranges.map { span($0.range, $0.value) } }
        let dur = duration > 0 ? duration : max(f.beats.last ?? 0, f.sections.last?.end ?? 0)
        if let ia = r.instrumentActivity {
            for (inst, rs) in ia.ranges { f.present[name(inst)] = rs.map { span($0) } }
            for (inst, vs) in ia.activity {
                f.activity[name(inst)] = AppleFeatures.bin(vs.map { (sec($0.time), $0.value) }, step: f.activityStep, duration: dur)
            }
        }
        if let l = r.loudness {
            f.lufs = Double(l.integrated.value); f.peakDb = Double(l.peak.value)
            f.shortTerm = AppleFeatures.bin(l.shortTerm.map { (sec($0.time), $0.value) }, step: 1, duration: dur)
        }
        f.seconds = Date().timeIntervalSince(t0)
        return f
    }
    @available(iOS 27, *)
    static func name(_ i: InstrumentActivityResult.Instrument) -> String {
        if i == .vocal { return "vocal" }
        if i == .drum { return "drum" }
        if i == .bass { return "bass" }
        if i == .other { return "other" }
        return i.rawValue
    }
    /// Apple's key → Cratebox's key number (0-11 major C...B, 12-23 minor)
    @available(iOS 27, *)
    static func keyNumber(_ k: KeyResult.KeySignature) -> Int {
        let pc: Int
        switch k.tonic {
        case .c: pc = 0
        case .cSharp, .dFlat: pc = 1
        case .d: pc = 2
        case .dSharp, .eFlat: pc = 3
        case .e: pc = 4
        case .f: pc = 5
        case .fSharp, .gFlat: pc = 6
        case .g: pc = 7
        case .gSharp, .aFlat: pc = 8
        case .a: pc = 9
        case .aSharp, .bFlat: pc = 10
        case .b: pc = 11
        @unknown default: return -1
        }
        return pc + (k.mode == .minor ? 12 : 0)
    }
    #endif

    // ---- comparing with the grids we trust ----
    struct Row: Identifiable {
        let id: String, title: String, artist: String
        let source: String                 // whose grid it's compared with: Cratebox, rekordbox or "hand-fixed"
        let bpm: Double?, appleBpm: Double?
        let key: Int, appleKey: Int
        let cmp: GridCompare.Result
        let vocals: Double?, lufs: Double?, seconds: Double
    }
    func rows() -> [Row] {
        guard let app else { return [] }
        return app.library.tracks.compactMap { t in
            guard let f = features(t) else { return nil }
            let i = t.info
            let src = i.gridManual ? "hand-fixed" : i.rbGrid ? "rekordbox" : "Cratebox"
            var cmp = GridCompare.Result()
            if let b = i.bpm, b > 0, let fb = i.firstBeat {
                cmp = GridCompare.compare(.init(bpm: b, firstBeat: fb, beats: i.gridManual ? nil : i.rbBeats, beat0: i.rbBeat0), apple: f)
            }
            return Row(id: t.id, title: i.title, artist: i.artist, source: src, bpm: i.bpm, appleBpm: f.tempo, key: i.key, appleKey: f.key, cmp: cmp,
                       vocals: f.share("vocal", duration: i.duration), lufs: f.lufs, seconds: f.seconds)
        }
    }
    /// the comparison as a CSV in Files → On My iPhone → Cratebox Suite
    func exportCSV() -> URL? {
        func q(_ s: String) -> String { "\"" + s.replacingOccurrences(of: "\"", with: "\"\"") + "\"" }
        func n(_ x: Double?, _ d: Int = 2) -> String { x.map { String(format: "%.\(d)f", $0) } ?? "" }
        var out = "title,artist,grid,bpm,apple_bpm,tempo_ratio,beat_offset_beats,beat_offset_ms,beats_on_grid,bar1_shift_beats,bar1_share,key,apple_key,vocals_share,lufs,apple_seconds\n"
        for r in rows() {
            out += [q(r.title), q(r.artist), r.source, n(r.bpm), n(r.appleBpm), n(r.cmp.tempoRatio, 3), n(r.cmp.beatOffset, 3), n(r.cmp.beatOffsetMs, 0),
                    n(r.cmp.beatsOnGrid, 2), r.cmp.barShift.map(String.init) ?? "", n(r.cmp.barShare, 2),
                    Keys.camelot(r.key)?.label ?? "", Keys.camelot(r.appleKey)?.label ?? "", n(r.vocals, 2), n(r.lufs, 1), n(r.seconds, 1)].joined(separator: ",") + "\n"
        }
        let u = Recorder.folder.appendingPathComponent("Apple analysis vs grids.csv")
        do { try out.write(to: u, atomically: true, encoding: .utf8); return u } catch { return nil }
    }
}
