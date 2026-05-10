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

struct EliteEditorView: View {
    @EnvironmentObject var state: AppState
    @State private var aiInput: String = ""
    
    var body: some View {
        VStack(spacing: 0) {
            // Top Floating Toolbar
            HStack(spacing: 20) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(state.currentProjectName).font(.headline).foregroundColor(.primary)
                    HStack(spacing: 12) {
                        Button(action: { state.undo() }) { Image(systemName: "arrow.uturn.backward.circle.fill") }.buttonStyle(.plain)
                        Button(action: { state.redo() }) { Image(systemName: "arrow.uturn.forward.circle.fill") }.buttonStyle(.plain)
                    }
                    .font(.system(size: 16))
                    .foregroundColor(.secondary)
                }
                
                Spacer()
                
                // Minimal AI Input
                HStack {
                    Image(systemName: "sparkles")
                        .foregroundColor(state.isProcessingAI ? .secondary : .cyan)
                    TextField("Need help? Type here...", text: $aiInput)
                        .textFieldStyle(.plain)
                        .font(.system(size: 13))
                        .disabled(state.isProcessingAI)
                        .onSubmit {
                            if !aiInput.isEmpty {
                                state.aiEdit(prompt: aiInput)
                                aiInput = ""
                            }
                        }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .frame(width: 300)
                .background(.ultraThinMaterial)
                .cornerRadius(16)
                .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.white.opacity(0.1), lineWidth: 1))
                
                Spacer()
                
                VStack(spacing: 4) {
                    Text("Rhythm: \(Int(state.directorRhythm/60))m").font(.system(size: 8, weight: .bold))
                    Slider(value: $state.directorRhythm, in: 10...300, step: 10)
                        .frame(width: 80)
                        .tint(.purple)
                }
                
                Button(action: { state.runDirectorMode() }) {
                    HStack {
                        Image(systemName: "video.badge.waveform.fill")
                        Text("Director Mode")
                    }
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(LinearGradient(colors: [.purple, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing))
                    .clipShape(Capsule())
                    .shadow(color: .purple.opacity(0.4), radius: 5, y: 2)
                }.buttonStyle(.plain)
                
                Button(action: { withAnimation { state.showHistory.toggle() } }) {
                    Image(systemName: "clock.arrow.2.circlepath")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(state.showHistory ? .cyan : .primary)
                        .padding(10)
                        .background(.regularMaterial)
                        .clipShape(Circle())
                }.buttonStyle(.plain)
                
                Button(action: { state.isDarkMode.toggle() }) {
                    Image(systemName: state.isDarkMode ? "moon.stars.fill" : "sun.max.fill")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(state.isDarkMode ? .cyan : .orange)
                        .padding(10)
                        .background(.regularMaterial)
                        .clipShape(Circle())
                        .shadow(color: .black.opacity(0.1), radius: 5, y: 2)
                }.buttonStyle(.plain)
                
                Button(action: { state.showExport = true }) {
                    Image(systemName: "square.and.arrow.up.fill")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.white)
                        .padding(10)
                        .background(LinearGradient(colors: [.cyan, .blue], startPoint: .topLeading, endPoint: .bottomTrailing))
                        .clipShape(Circle())
                        .shadow(color: .cyan.opacity(0.4), radius: 5, y: 2)
                }.buttonStyle(.plain)
            }
            .padding(.horizontal, 24)
            .padding(.top, 24)
            .padding(.bottom, 12)
            
            ZStack(alignment: .trailing) {
                GeometryReader { geo in
                    HStack(spacing: 20) {
                        EliteMediaBin()
                            .frame(width: 300)
                        
                        VStack(spacing: 20) {
                            ElitePlayer()
                                .frame(maxWidth: .infinity, maxHeight: .infinity)
                            
                            EliteTimeline()
                        }
                        
                        EliteInspector()
                            .frame(width: 300)
                    }
                    .padding(.horizontal, 20)
                }
                
                if state.showHistory {
                    EliteHistoryPanel()
                        .frame(width: 250)
                        .transition(.move(edge: .trailing))
                        .padding(.trailing, 20)
                        .zIndex(100)
                }
            }
            .padding(.bottom, 20)
        }
    }
}
