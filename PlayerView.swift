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

struct ElitePlayer: View {
    @EnvironmentObject var state: AppState
    var body: some View {
        ZStack(alignment: .bottom) {
            ZStack {
                if let player = state.player {
                    VideoPlayerView(player: player).cornerRadius(30)
                } else {
                    RoundedRectangle(cornerRadius: 30).fill(Color.primary.opacity(0.05))
                        .overlay(Image(systemName: "play.slash").font(.largeTitle).foregroundColor(.primary.opacity(0.3)))
                }
            }
            VStack(spacing: 10) {
                Slider(value: Binding(get: { state.currentTime }, set: { state.seek(to: $0) }), in: 0...max(0.1, state.totalDuration)).tint(.cyan)
                HStack(spacing: 24) {
                    Button(action: { state.isComparisonModeEnabled.toggle() }) { Image(systemName: "square.split.2x1.fill").foregroundColor(state.isComparisonModeEnabled ? .cyan : .primary) }
                    Text(state.currentTimeText).font(.system(size: 12, weight: .medium, design: .monospaced))
                    Spacer()
                    Button(action: { state.seek(by: -5) }) { Image(systemName: "gobackward.5") }
                    Button(action: { state.togglePlay() }) { Image(systemName: state.isPlaying ? "pause.circle.fill" : "play.circle.fill").font(.system(size: 32)).foregroundColor(.cyan) }
                    Button(action: { state.seek(by: 5) }) { Image(systemName: "goforward.5") }
                    Spacer()
                    Text(state.totalTimeText).font(.system(size: 12, weight: .medium, design: .monospaced))
                }
            }.buttonStyle(.plain).padding(.horizontal, 24).padding(.vertical, 14).background(.regularMaterial).cornerRadius(24).padding(.bottom, 24)
        }.overlay(RoundedRectangle(cornerRadius: 30).stroke(Color.primary.opacity(0.05), lineWidth: 1))
    }
}
