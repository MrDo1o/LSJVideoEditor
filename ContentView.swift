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

struct ContentView: View {
    @EnvironmentObject var state: AppState
    @State private var showSplash = true

    var body: some View {
        ZStack {
            VisualEffectView().ignoresSafeArea()
            
            if showSplash {
                LSJSplashView()
                    .onAppear {
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
                            withAnimation(.easeOut(duration: 0.8)) {
                                showSplash = false
                            }
                        }
                    }
            } else {
                if state.clips.isEmpty {
                    EliteHomeView()
                } else {
                    EliteEditorView()
                }
            }
            
            if state.isProcessingAI {
                EliteProcessingOverlay()
            }
        }
        .sheet(isPresented: $state.showExport) {
            EliteExportSheet()
        }
        .preferredColorScheme(state.isDarkMode ? .dark : .light)
        .animation(.easeInOut(duration: 0.5), value: state.isDarkMode)
    }
}

struct LSJSplashView: View {
    @State private var scale: CGFloat = 0.8
    @State private var opacity: Double = 0.0
    @State private var barWidths: [CGFloat] = [10, 30, 15, 40, 20, 5, 25, 15, 35, 10, 20, 45, 15, 30]
    
    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            
            VStack(spacing: 30) {
                VStack(alignment: .leading, spacing: 5) {
                    HStack(alignment: .top) {
                        Text("LSJ")
                            .font(.system(size: 120, weight: .bold, design: .default))
                            .foregroundColor(.white)
                        Text("TM")
                            .font(.system(size: 20, weight: .bold))
                            .foregroundColor(.white)
                            .padding(.top, 15)
                    }
                    
                    HStack(spacing: 4) {
                        ForEach(0..<barWidths.count, id: \.self) { index in
                            Rectangle()
                                .fill(Color(red: 0.4, green: 0.9, blue: 0.9))
                                .frame(width: barWidths[index], height: 80)
                                .shadow(color: Color(red: 0.4, green: 0.9, blue: 0.9).opacity(0.8), radius: 15)
                        }
                    }
                    .padding(.vertical, 10)
                    
                    Text("DIGITAL ARCHITECTURE")
                        .font(.system(size: 24, weight: .light))
                        .tracking(10)
                        .foregroundColor(.white.opacity(0.8))
                }
                .offset(x: -20)
            }
            
            VStack {
                Spacer()
                HStack {
                    Spacer()
                    Text("LSJ SYSTEMS")
                        .font(.system(size: 14, weight: .medium))
                        .tracking(5)
                        .foregroundColor(.white.opacity(0.5))
                        .padding(40)
                }
            }
        }
        .scaleEffect(scale)
        .opacity(opacity)
        .onAppear {
            withAnimation(.easeOut(duration: 1.2)) {
                scale = 1.0
                opacity = 1.0
            }
        }
    }
}
