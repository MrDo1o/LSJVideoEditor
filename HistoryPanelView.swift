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

struct EliteHistoryPanel: View {
    @EnvironmentObject var state: AppState
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Edit History").font(.system(size: 16, weight: .bold))
            ScrollView {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(state.historyLog, id: \.self) { log in
                        Text(log).font(.system(size: 11, design: .monospaced)).foregroundColor(.secondary).padding(8).frame(maxWidth: .infinity, alignment: .leading).background(Color.primary.opacity(0.05)).cornerRadius(8)
                    }
                }
            }
        }.padding().background(.ultraThinMaterial).cornerRadius(20).overlay(RoundedRectangle(cornerRadius: 20).stroke(Color.primary.opacity(0.1), lineWidth: 1))
    }
}
