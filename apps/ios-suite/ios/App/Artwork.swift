// Album art: rekordbox's own artwork for stick tracks (export.pdb's artwork table → PIONEER/Artwork/…), the
// picture embedded in the file for everything else (and for stick tracks rekordbox has none for).
// Library rows use the small one (rekordbox's 80 px a1.jpg), the decks the big one (a1_m.jpg, when the export
// has it) shrunk to fit. Images are decoded off the main thread at the size they're drawn, and kept in a cache
// iOS empties under memory pressure. Settings → Look → Album art turns it off (`cb.art`).
import SwiftUI
import ImageIO
import AVFoundation
import CrateboxKit

@MainActor
final class Artwork {
    static let shared = Artwork()
    enum Size: String {
        case icon, deck
        /// longest side in pixels it's decoded to (library icons are 22 pt, deck art up to 160 pt; 3x screens)
        var px: Int { self == .icon ? 72 : 480 }
    }
    private let cache = NSCache<NSString, UIImage>()
    private var none = Set<String>()                       // tracks known to have no art (at this size)
    private var running = [String: Task<UIImage?, Never>]()
    init() { cache.countLimit = 600 }

    private func key(_ id: String, _ s: Size) -> String { s.rawValue + "|" + id }
    func cached(_ id: String, _ s: Size) -> UIImage? { cache.object(forKey: key(id, s) as NSString) }

    func image(for t: LibTrack, _ s: Size) async -> UIImage? {
        let k = key(t.id, s)
        if let i = cache.object(forKey: k as NSString) { return i }
        if none.contains(k) { return nil }
        if let r = running[k] { return await r.value }
        // where to look, worked out here (the device list lives on the main thread)
        var files = [URL]()
        if let p = t.rb?.artwork, let d = Devices.shared.device(of: t) {
            func on(_ path: String) -> URL { d.root.appendingPathComponent(String(path.drop { $0 == "/" })) }
            if s == .deck { files.append(on(PDBTrack.bigArtwork(p))) }
            files.append(on(p))
        }
        let audio = Devices.shared.url(for: t) ?? Devices.shared.app?.library.fileURL(t)
        let px = s.px
        let task = Task.detached(priority: .utility) { () -> UIImage? in
            for f in files { if let i = Artwork.decode(url: f, px: px) { return i } }
            if let a = audio, let data = await Artwork.embedded(a) { return Artwork.decode(data: data, px: px) }
            return nil
        }
        running[k] = task
        let img = await task.value
        running[k] = nil
        if let img { cache.setObject(img, forKey: k as NSString) } else { none.insert(k) }
        return img
    }
    nonisolated static func decode(url: URL, px: Int) -> UIImage? {
        guard let src = CGImageSourceCreateWithURL(url as CFURL, [kCGImageSourceShouldCache: false] as CFDictionary) else { return nil }
        return thumb(src, px)
    }
    nonisolated static func decode(data: Data, px: Int) -> UIImage? {
        guard let src = CGImageSourceCreateWithData(data as CFData, [kCGImageSourceShouldCache: false] as CFDictionary) else { return nil }
        return thumb(src, px)
    }
    nonisolated static func thumb(_ src: CGImageSource, _ px: Int) -> UIImage? {
        let o: [CFString: Any] = [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceCreateThumbnailWithTransform: true,
                                  kCGImageSourceShouldCacheImmediately: true, kCGImageSourceThumbnailMaxPixelSize: px]
        return CGImageSourceCreateThumbnailAtIndex(src, 0, o as CFDictionary).map { UIImage(cgImage: $0) }
    }
    /// the cover in the file's tags (ID3 APIC, MP4 covr, FLAC/Vorbis picture: whatever AVFoundation reads)
    nonisolated static func embedded(_ url: URL) async -> Data? {
        let asset = AVURLAsset(url: url)
        guard let items = try? await asset.load(.commonMetadata) else { return nil }
        for i in AVMetadataItem.metadataItems(from: items, filteredByIdentifier: .commonIdentifierArtwork) {
            if let d = try? await i.load(.dataValue) { return d }
        }
        return nil
    }
}

/// A track's cover, square, filling its frame; a note on the deck's colour while it loads or when there's none.
struct ArtworkView: View {
    let track: LibTrack?
    var size: Artwork.Size = .icon
    var tint: Color = Theme.muted
    @State private var img: UIImage?
    var body: some View {
        let r = size == .deck ? 5.0 : 3.0
        ZStack {
            RoundedRectangle(cornerRadius: r).fill(Theme.raise)
            if let img {
                Image(uiImage: img).resizable().scaledToFill()
            } else {
                Image(systemName: "music.note").resizable().scaledToFit().padding(size == .deck ? 10 : 5).foregroundStyle(tint.opacity(0.5))
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: r))
        .task(id: track?.id) {
            guard let t = track else { img = nil; return }
            img = Artwork.shared.cached(t.id, size)
            if img == nil { img = await Artwork.shared.image(for: t, size) }
        }
        .accessibilityHidden(true)
    }
}
