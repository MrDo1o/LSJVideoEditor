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

struct EliteInspector: View {
    @EnvironmentObject var state: AppState
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Inspector").font(.title2.weight(.semibold))
            if let id = state.selectedTimelineClipIDs.first, let clip = state.timelineClips.first(where: { $0.id == id }) {
                VStack(spacing: 16) {
                    EliteInfoBox(title: "Timeline Clip") {
                        EliteInfoRow(label: "Name", value: clip.name)
                        EliteInfoRow(label: "Duration", value: String(format: "%.2fs", clip.duration))
                        EliteInfoRow(label: "Track", value: "T\(clip.track + 1)")
                        EliteInfoRow(label: "AI Model", value: clip.filter ?? "None")
                    }
                    if let filterName = clip.filter, filterName != "Original", let model = state.eliteModels.first(where: { $0.rebrandedName == filterName }), let params = model.parameters, !params.isEmpty {
                        EliteInfoBox(title: "AI Parameters") {
                            ForEach(params, id: \.name) { param in
                                VStack(alignment: .leading, spacing: 4) {
                                    HStack { Text(param.guiName).font(.caption); Spacer(); Text(String(format: "%.2f", Double(clip.filterParams?[param.name] ?? "") ?? param.default ?? 0.0)).font(.system(size: 10, weight: .bold)) }
                                    Slider(value: Binding(get: { Double(clip.filterParams?[param.name] ?? "") ?? param.default ?? 0.0 }, set: { state.updateClipFilterParam(clip.id, key: param.name, value: String($0)) }), in: (param.min ?? 0.0)...(param.max ?? 1.0)).tint(.cyan)
                                }.padding(.bottom, 6)
                            }
                        }
                    }
                }
            } else if let clip = state.selectedClip {
                EliteInfoBox(title: "Media Asset") {
                    EliteInfoRow(label: "Name", value: clip.name)
                    EliteInfoRow(label: "Duration", value: clip.durationText)
                }
            } else { Spacer(); Text("Select a clip to view details").font(.caption).foregroundColor(.secondary).frame(maxWidth: .infinity, alignment: .center); Spacer() }
            Spacer()
        }.padding(24).background(.regularMaterial).cornerRadius(30)
        .overlay(RoundedRectangle(cornerRadius: 30).stroke(Color.primary.opacity(0.05), lineWidth: 1))
        .shadow(color: .black.opacity(0.05), radius: 15, y: 5)
    }
}

struct EliteInfoBox<Content: View>: View {
    let title: String; let content: Content
    init(title: String, @ViewBuilder content: () -> Content) { self.title = title; self.content = content() }
    var body: some View {
        VStack(alignment: .leading, spacing: 14) { Text(title).font(.caption.weight(.bold)).foregroundColor(.primary.opacity(0.5)).textCase(.uppercase); content }
        .padding(20).background(Color.primary.opacity(0.03)).cornerRadius(20)
    }
}

struct EliteInfoRow: View {
    let label: String; let value: String
    var body: some View { HStack { Text(label).foregroundColor(.secondary).font(.system(size: 11)); Spacer(); Text(value).font(.system(size: 11, weight: .medium)) } }
}
