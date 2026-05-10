/*
 *  LSJ ELITE VIDEO EDITOR
 *  Digital Architecture by LSJ Systems TM
 *  __________________________________________________________________
 */

import SwiftUI

struct EliteWidgetComponent: View {
    let projectName: String
    
    var body: some View {
        ZStack {
            // Background Glow
            Circle()
                .fill(PremiumTheme.primaryGradient.opacity(0.15))
                .frame(width: 250, height: 250)
                .blur(radius: 50)
                .offset(x: 50, y: -20)

            VStack(alignment: .leading, spacing: 0) {
                // Header
                HStack(alignment: .center, spacing: 8) {
                    Text("LSJ")
                        .font(.system(size: 28, weight: .black))
                        .foregroundStyle(.white)
                    
                    Text("SYSTEMS")
                        .font(.system(size: 10, weight: .bold))
                        .tracking(4)
                        .foregroundStyle(.white.opacity(0.4))
                    
                    Spacer()
                    
                    Image(systemName: "cpu.fill")
                        .font(.system(size: 16))
                        .foregroundStyle(PremiumTheme.primaryGradient)
                        .premiumGlow(color: .cyan, radius: 10)
                }
                .padding(.bottom, 24)
                
                // Content
                VStack(alignment: .leading, spacing: 4) {
                    Text("CURRENT PRODUCTION")
                        .font(.system(size: 9, weight: .black))
                        .tracking(2)
                        .foregroundStyle(.cyan)
                    
                    Text(projectName.uppercased())
                        .font(.system(size: 20, weight: .light, design: .monospaced))
                        .lineLimit(1)
                        .foregroundStyle(.white)
                }
                
                Spacer()
                
                // Footer Metrics
                HStack(spacing: 20) {
                    MetricLabel(label: "FPS", value: "60.0")
                    MetricLabel(label: "BUFFER", value: "0.2s")
                    MetricLabel(label: "ENGINE", value: "ELITE")
                    
                    Spacer()
                    
                    Text("AUTHENTICATED")
                        .font(.system(size: 7, weight: .black))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.green.opacity(0.2))
                        .foregroundStyle(.green)
                        .cornerRadius(2)
                }
            }
            .padding(24)
            .glassCard()
        }
        .frame(width: 380, height: 200)
    }
}

struct MetricLabel: View {
    let label: String
    let value: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.system(size: 7, weight: .bold))
                .foregroundStyle(.secondary)
            Text(value)
                .font(.system(size: 10, weight: .medium, design: .monospaced))
                .foregroundStyle(.white)
        }
    }
}
