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
import UniformTypeIdentifiers

struct EliteExportSheet: View {
    @EnvironmentObject var state: AppState
    @State private var exportContainer = "mp4"
    @State private var useProMastering = true
    
    var body: some View {
        VStack(spacing: 30) {
            Text("Elite Master Render")
                .font(.system(size: 32, weight: .light))
                .foregroundColor(.primary)
            
            VStack(spacing: 20) {
                HStack {
                    Image(systemName: "sparkles.tv.fill").foregroundColor(.cyan)
                    VStack(alignment: .leading) {
                        Text("Professional Mastering").font(.headline)
                        Text("Auto Lighting, Noise Reduction & Audio Conformance").font(.caption).foregroundColor(.secondary)
                    }
                    Spacer()
                    Toggle("", isOn: $useProMastering).toggleStyle(.switch)
                }
                .padding()
                .background(Color.primary.opacity(0.05))
                .cornerRadius(16)

                HStack {
                    Text("Resolution").frame(width: 90, alignment: .leading).foregroundColor(.primary.opacity(0.7))
                    Picker("", selection: $state.exportResolution) {
                        Text("1080p").tag("1920x1080")
                        Text("4K").tag("3840x2160")
                    }.pickerStyle(.segmented)
                }
                HStack {
                    Text("Frame Rate").frame(width: 90, alignment: .leading).foregroundColor(.primary.opacity(0.7))
                    Picker("", selection: $state.exportFPS) {
                        Text("24").tag(24)
                        Text("30").tag(30)
                        Text("60").tag(60)
                    }.pickerStyle(.segmented)
                }
                Divider().background(Color.primary.opacity(0.1)).padding(.vertical, 4)
                HStack {
                    Text("Container").frame(width: 90, alignment: .leading).foregroundColor(.primary.opacity(0.7))
                    Picker("", selection: $exportContainer) {
                        Text("MP4").tag("mp4")
                        Text("MOV").tag("mov")
                    }.pickerStyle(.segmented)
                }
            }
            .padding(24)
            .background(Color.primary.opacity(0.03))
            .cornerRadius(24)
            .overlay(RoundedRectangle(cornerRadius: 24).stroke(Color.primary.opacity(0.05), lineWidth: 1))
            
            if state.isProcessingAI {
                VStack(spacing: 12) {
                    ProgressView(value: state.processingProgress)
                        .tint(.cyan)
                    Text(state.aiStatus)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            } else {
                HStack(spacing: 20) {
                    Button("Cancel") { state.showExport = false }
                        .buttonStyle(.plain)
                        .padding(.horizontal, 24).padding(.vertical, 14)
                        .background(Color.primary.opacity(0.05))
                        .clipShape(Capsule())
                    
                    Button("Start Render") { 
                        let panel = NSSavePanel()
                        panel.allowedContentTypes = [exportContainer == "mp4" ? .mpeg4Movie : .quickTimeMovie]
                        panel.nameFieldStringValue = "Elite_Export.\(exportContainer)"
                        if panel.runModal() == .OK, let url = panel.url {
                            state.exportProject(to: url, useMastering: useProMastering)
                        }
                    }
                    .buttonStyle(.plain)
                    .padding(.horizontal, 32).padding(.vertical, 14)
                    .background(LinearGradient(colors: [.cyan, .blue], startPoint: .topLeading, endPoint: .bottomTrailing))
                    .foregroundColor(.white)
                    .clipShape(Capsule())
                    .shadow(color: .cyan.opacity(0.4), radius: 10, y: 5)
                }
            }
        }
        .padding(50)
        .frame(width: 550)
        .background(VisualEffectView().ignoresSafeArea())
    }
}
