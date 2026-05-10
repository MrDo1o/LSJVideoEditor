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

struct EliteProcessingOverlay: View {
    @EnvironmentObject var state: AppState
    var body: some View {
        ZStack {
            Color.black.opacity(0.8).ignoresSafeArea()
            VStack(spacing: 24) {
                if state.aiStatus.contains("Mastering") || state.aiStatus.contains("Elite") {
                    Image(systemName: "sparkles")
                        .font(.system(size: 40))
                        .foregroundColor(.cyan)
                        .shadow(color: .cyan, radius: 10)
                        .symbolEffect(.pulse)
                } else {
                    ProgressView()
                        .tint(.cyan)
                        .scaleEffect(1.5)
                }

                VStack(spacing: 12) {
                    ProgressView(value: state.processingProgress)
                        .progressViewStyle(.linear)
                        .tint(.cyan)
                        .frame(width: 250)
                    
                    Text(state.aiStatus)
                        .font(.system(size: 14, weight: .medium, design: .monospaced))
                        .foregroundColor(.cyan)
                }
            }
            .padding(50)
            .background(.ultraThinMaterial)
            .cornerRadius(30)
            .shadow(color: .cyan.opacity(0.3), radius: 50)
            .overlay(RoundedRectangle(cornerRadius: 30).stroke(Color.cyan.opacity(0.2), lineWidth: 1))
        }
    }
}
