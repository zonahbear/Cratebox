// Apple's Music Understanding results (iOS 27+), kept in Cratebox's own Codable form so the rest of the app, the
// stored files and the tests don't need the framework or the iOS 27 SDK: the app's adapter
// (App/AppleMusic.swift) fills this in from a MusicUnderstandingSession. These sit BESIDE Cratebox's own analysis,
// rekordbox's grids and the user's grid edits; nothing here replaces them. GridCompare measures how far apart
// Apple's beats and bars are from a grid we already trust, so the two can be judged on real tracks.
import Foundation

public struct AppleFeatures: Codable, Equatable {
    /// bump when what's stored (or how it's read from the framework) changes: older files are analysed again
    public static let VER = 1
    public var ver = AppleFeatures.VER
    /// the file this came from, so a replaced file (same name, new content) isn't matched with old results
    public var size: Int64 = 0, mtime: Double = 0
    public var analysedAt: Double = 0, os = "", seconds = 0.0      // when, on which iOS, and how long it took
    // rhythm
    public var bpm: Double?
    public var beats: [Double] = [], bars: [Double] = []          // seconds; bars = the first beat of each bar
    // key over time: our key numbers (0-11 major C...B, 12-23 minor, as Keys), with their time ranges
    public var keys: [Span] = []
    // structure: Apple's three levels (sections ≈ intro/verse/chorus, segments, phrases)
    public var sections: [Span] = [], segments: [Span] = [], phrases: [Span] = []
    /// how fast the music feels (Apple: an events-per-minute rate), per range: an energy measure, not the BPM
    public var pace: [Span] = []
    /// where each instrument is heard (vocal, drum, bass, other) and how strongly, 0...1, at most two values a second
    public var present: [String: [Span]] = [:]
    public var activity: [String: [Float]] = [:], activityStep = 0.5
    // loudness (LUFS; peak in dB), short-term LUFS once a second
    public var lufs: Double?, peakDb: Double?
    public var shortTerm: [Float] = []

    public struct Span: Codable, Equatable {
        public var start: Double, end: Double, value: Double
        public init(_ start: Double, _ end: Double, _ value: Double = 0) { self.start = start; self.end = end; self.value = value }
    }
    public init() {}

    /// the key heard for longest (−1 if Apple found none)
    public var key: Int {
        var total = [Int: Double]()
        for s in keys where s.value >= 0 { total[Int(s.value), default: 0] += s.end - s.start }
        return total.max { $0.value != $1.value ? $0.value < $1.value : $0.key > $1.key }?.key ?? -1
    }
    /// share of the track (0...1) where an instrument is heard; nil when Apple didn't report it
    public func share(_ instrument: String, duration: Double) -> Double? {
        guard let r = present[instrument], duration > 0 else { return nil }
        return min(1, r.reduce(0) { $0 + max(0, $1.end - $1.start) } / duration)
    }
    /// Apple's tempo, or the median beat spacing's if it gave none
    public var tempo: Double? {
        if let bpm, bpm > 0 { return bpm }
        guard beats.count > 2 else { return nil }
        let d = zip(beats.dropFirst(), beats).map { $0 - $1 }.sorted()
        let m = d[d.count / 2]
        return m > 0 ? 60 / m : nil
    }

    /// averages a dense series of (time, value) into fixed steps, so a whole track's activity stays small on disk
    public static func bin(_ pts: [(Double, Float)], step: Double, duration: Double) -> [Float] {
        guard step > 0, duration > 0 else { return [] }
        let n = Int((duration / step).rounded(.up))
        var sum = [Float](repeating: 0, count: n), cnt = [Int](repeating: 0, count: n)
        for (t, v) in pts where t >= 0 {
            let i = min(n - 1, Int(t / step))
            sum[i] += v; cnt[i] += 1
        }
        // a step with no value of its own keeps the last one (Apple's series can be sparser than the step)
        var out = [Float](repeating: 0, count: n), last: Float = 0
        for i in 0..<n { if cnt[i] > 0 { last = sum[i] / Float(cnt[i]) }; out[i] = last }
        return out
    }
}

/// How Apple's beats and bars sit against a grid Cratebox already has (its own, rekordbox's or a hand-fixed one).
/// Assumes 4/4, as the rest of the app does.
public enum GridCompare {
    /// a grid: BPM + where bar 1's first beat is, or rekordbox's beat-by-beat list (`beats`, bar 1 at `beat0`)
    public struct Grid {
        public var bpm: Double, firstBeat: Double
        public var beats: [Double]? = nil, beat0 = 0
        public init(bpm: Double, firstBeat: Double, beats: [Double]? = nil, beat0: Int = 0) {
            self.bpm = bpm; self.firstBeat = firstBeat; self.beats = beats; self.beat0 = beat0
        }
        /// where time t falls on the grid, in beats from bar 1's first beat (fractional)
        public func position(_ t: Double) -> Double {
            if let b = beats, b.count > 1 {
                var lo = 0, hi = b.count - 1
                if t <= b[0] { return Double(-beat0) + (t - b[0]) / (b[1] - b[0]) }
                if t >= b[hi] { return Double(hi - beat0) + (t - b[hi]) / (b[hi] - b[hi - 1]) }
                while hi - lo > 1 { let m = (lo + hi) / 2; if b[m] <= t { lo = m } else { hi = m } }
                return Double(lo - beat0) + (t - b[lo]) / (b[hi] - b[lo])
            }
            return (t - firstBeat) * bpm / 60
        }
    }
    public struct Result: Equatable {
        /// Apple's tempo over ours (1 = same; 2 or 0.5 = it counted double or half time)
        public var tempoRatio: Double?
        /// 1, 0.5 or 2 when Apple's tempo is ours, half or double (within 2%): the cases whose beats can be compared.
        /// Half time is the usual one for 140-ish bass music: Apple counts 70
        public var tempoMult: Double?
        /// median offset of Apple's beats from ours, in our beats and in ms; nil if the tempos can't be compared
        public var beatOffset: Double?, beatOffsetMs: Double?
        /// share of Apple's beats within 1/8 beat of ours
        public var beatsOnGrid: Double?
        /// which of our beats (0-3, 0 = our bar 1) Apple's bars start on most often, and how often (0...1).
        /// At double time Apple's bar is two of our beats, so only 0 or 1
        public var barShift: Int?, barShare: Double?
        public var sameTempo: Bool { tempoRatio.map { abs($0 - 1) < 0.02 } ?? false }
        public var comparable: Bool { tempoMult != nil }
        /// same tempo (or half / double), beats within 1/8 beat, bars on our bar 1
        public var agrees: Bool { comparable && abs(beatOffset ?? 1) < 0.125 && barShift == 0 }
        public init() {}
    }

    public static func compare(_ ref: Grid, apple a: AppleFeatures) -> Result {
        var r = Result()
        guard ref.bpm > 0, let tempo = a.tempo else { return r }
        r.tempoRatio = tempo / ref.bpm
        r.tempoMult = [1.0, 0.5, 2.0].first { abs(r.tempoRatio! / $0 - 1) < 0.02 }
        guard let mult = r.tempoMult, !a.beats.isEmpty else { return r }
        // beat phase: wrapped to the nearest beat of ours (half time: Apple's beats are every second one of ours, which
        // still land on our beats; double time: every second one of Apple's falls between ours, so wrap to half beats)
        let k = mult == 2 ? 2.0 : 1.0
        let ph = a.beats.map { p -> Double in let x = ref.position(p) * k; return (x - x.rounded()) / k }
        let off = median(ph)
        r.beatOffset = off
        r.beatOffsetMs = off * 60 / ref.bpm * 1000
        r.beatsOnGrid = Double(ph.filter { abs($0) < 0.125 }.count) / Double(ph.count)
        // bar phase, after taking the beat offset out, so a grid that's a little early doesn't split the vote
        guard !a.bars.isEmpty else { return r }
        let n = mult == 2 ? 2 : 4
        var votes = [Int](repeating: 0, count: n)
        for b in a.bars {
            let i = Int((ref.position(b) - off).rounded())
            votes[((i % n) + n) % n] += 1
        }
        let best = votes.indices.max { votes[$0] != votes[$1] ? votes[$0] < votes[$1] : $0 > $1 }!
        r.barShift = best
        r.barShare = Double(votes[best]) / Double(a.bars.count)
        return r
    }
    static func median(_ x: [Double]) -> Double {
        let s = x.sorted(), n = s.count
        return n % 2 == 1 ? s[n / 2] : (s[n / 2 - 1] + s[n / 2]) / 2
    }
}
