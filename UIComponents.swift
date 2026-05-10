/*
 *  LSJ ELITE VIDEO EDITOR
 *  Digital Architecture by LSJ Systems TM
 *  __________________________________________________________________
 *
 *  Proprietary & Confidential. 
 *  Unauthorized copying of this file, via any medium is strictly prohibited.
 *  Architected for Professional Production & Red Team Operations.
 */

import SwiftUI
import AVFoundation

struct VisualEffectView: NSViewRepresentable {
    func makeNSView(context: Context) -> NSVisualEffectView {
        let view = NSVisualEffectView()
        view.blendingMode = .behindWindow
        view.state = .active
        view.material = .hudWindow
        return view
    }
    func updateNSView(_ nsView: NSVisualEffectView, context: Context) {}
}

struct VideoPlayerView: NSViewRepresentable {
    let player: AVPlayer
    func makeNSView(context: Context) -> PlayerNSView { let v = PlayerNSView(); v.player = player; return v }
    func updateNSView(_ nsView: PlayerNSView, context: Context) { nsView.player = player }
}

class PlayerNSView: NSView {
    var player: AVPlayer? { get { playerLayer.player } set { playerLayer.player = newValue } }
    private let playerLayer = AVPlayerLayer()
    override init(frame: NSRect) { super.init(frame: frame); wantsLayer = true; playerLayer.videoGravity = .resizeAspect; layer?.addSublayer(playerLayer) }
    required init?(coder: NSCoder) { fatalError() }
    override func layout() { super.layout(); playerLayer.frame = bounds }
}

struct WaveformView: View {
    let url: URL
    @State private var samples: [Float] = []
    
    var body: some View {
        GeometryReader { geo in
            HStack(spacing: 1) {
                ForEach(0..<samples.count, id: \.self) { i in
                    RoundedRectangle(cornerRadius: 1)
                        .fill(Color.cyan.opacity(0.4))
                        .frame(height: max(2, CGFloat(samples[i]) * geo.size.height))
                }
            }
            .onAppear {
                Task {
                    let count = Int(geo.size.width / 4)
                    let result = await WaveformGenerator.generateWaveform(from: url, count: max(1, count))
                    await MainActor.run { self.samples = result }
                }
            }
        }
    }
}

struct MovieTransferable: Transferable {
    let url: URL
    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(contentType: .movie) { movie in
            SentTransferredFile(movie.url)
        } importing: { received in
            let copy = FileManager.default.temporaryDirectory.appendingPathComponent(received.file.lastPathComponent)
            if FileManager.default.fileExists(atPath: copy.path) { try? FileManager.default.removeItem(at: copy) }
            try FileManager.default.copyItem(at: received.file, to: copy)
            return Self.init(url: copy)
        }
    }
}
