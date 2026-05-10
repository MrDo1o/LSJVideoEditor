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

struct EliteTimeline: View {
    @EnvironmentObject var state: AppState
    @State private var selectedCategory: String = "Enhance"
    
    var categories: [String] {
        var cats = Array(Set(state.eliteModels.compactMap { $0.category }))
        cats.sort()
        if let idx = cats.firstIndex(of: "Other") { cats.remove(at: idx); cats.append("Other") }
        if let idx = cats.firstIndex(of: "Legacy") { cats.remove(at: idx); cats.append("Legacy") }
        return ["Original"] + cats
    }
    
    var filteredModels: [String] {
        if selectedCategory == "Original" { return ["Original"] }
        return state.eliteModels.filter { $0.category == selectedCategory }.map { $0.rebrandedName }
    }

    var body: some View {
        VStack(spacing: 0) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 16) {
                    ForEach(categories, id: \.self) { cat in
                        Button(action: { selectedCategory = cat }) {
                            Text(cat)
                                .font(.system(size: 12, weight: selectedCategory == cat ? .bold : .medium))
                                .foregroundColor(selectedCategory == cat ? .cyan : .secondary)
                                .padding(.vertical, 6)
                                .padding(.horizontal, 12)
                                .background(selectedCategory == cat ? Color.cyan.opacity(0.15) : Color.clear)
                                .clipShape(Capsule())
                        }.buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 20).padding(.top, 12)
            }
            
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(filteredModels, id: \.self) { filter in
                        Button(action: { state.applyFilter(filter) }) {
                            FilterThumbnailView(filterName: filter, baseImage: state.currentThumbnailImage, isSelected: state.currentFilter == filter)
                        }.buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 20).padding(.vertical, 12)
            }
            .background(.thinMaterial)
            
            Divider().background(Color.white.opacity(0.1))
            
            HStack(spacing: 24) {
                Button(action: { state.tool = .select }) { Image(systemName: "cursorarrow").foregroundColor(state.tool == .select ? .cyan : .primary) }
                Button(action: { state.tool = .cut }) { Image(systemName: "scissors").foregroundColor(state.tool == .cut ? .cyan : .primary) }
                Button(action: { state.split() }) { Image(systemName: "timeline.selection") }
                Button(action: { state.deleteSelectedClip() }) { Image(systemName: "trash") }
                Spacer()
                Button(action: { state.toggleTimelineMode() }) { 
                    HStack {
                        Image(systemName: state.isTimelineMode ? "film.fill" : "film")
                        Text(state.isTimelineMode ? "Timeline" : "Clip")
                    }
                    .padding(.horizontal, 16).padding(.vertical, 8)
                    .background(Color.primary.opacity(0.05)).clipShape(Capsule())
                }
            }
            .font(.system(size: 14, weight: .medium)).buttonStyle(.plain)
            .padding(.horizontal, 24).padding(.vertical, 16)
            
            ScrollView([.horizontal, .vertical]) {
                ZStack(alignment: .topLeading) {
                    VStack(spacing: 8) {
                        ForEach(0..<state.videoTrackCount, id: \.self) { i in EliteTrackBackground(label: "V\(i+1)") }
                        ForEach(0..<state.audioTrackCount, id: \.self) { i in EliteTrackBackground(label: "A\(i+1)") }
                    }
                    ForEach(state.timelineClips) { clip in TimelineClipView(clip: clip).environmentObject(state) }
                    PlayheadView(height: CGFloat((state.videoTrackCount + state.audioTrackCount) * 58)).environmentObject(state)
                }
                .padding(.horizontal, 20).padding(.vertical, 10)
                .onDrop(of: [.text], delegate: TimelineDropDelegate(state: state))
            }
        }
        .background(.regularMaterial).cornerRadius(30)
        .overlay(RoundedRectangle(cornerRadius: 30).stroke(Color.primary.opacity(0.05), lineWidth: 1))
        .shadow(color: .black.opacity(0.05), radius: 15, y: 5)
    }
}

struct EliteTrackBackground: View {
    let label: String
    var body: some View {
        HStack(spacing: 0) {
            Text(label).font(.system(size: 10, weight: .bold)).frame(width: 30).foregroundColor(.primary.opacity(0.5))
            RoundedRectangle(cornerRadius: 12).fill(Color.primary.opacity(0.02)).frame(height: 50)
        }
    }
}

struct TimelineClipView: View {
    let clip: TimelineClip; @EnvironmentObject var state: AppState
    var body: some View {
        ZStack(alignment: .leading) {
            ClipThumbnailView(url: clip.mediaClip.url, isSelected: state.selectedTimelineClipIDs.contains(clip.id), track: clip.track)
                .frame(width: max(10, CGFloat(clip.duration * 20)), height: 46)
            WaveformView(url: clip.mediaClip.url).frame(width: max(10, CGFloat(clip.duration * 20)), height: 20).padding(.top, 26)
            HStack {
                TrimHandle { delta in state.updateClipDuration(clip.id, startTime: clip.startTime + Double(delta/20), duration: clip.duration - Double(delta/20)) }
                Spacer()
                TrimHandle { delta in state.updateClipDuration(clip.id, startTime: clip.startTime, duration: clip.duration + Double(delta/20)) }
            }.padding(.horizontal, -2)
            Text(clip.name).font(.system(size: 9, weight: .bold)).foregroundColor(.white).padding(4).background(Color.black.opacity(0.6)).cornerRadius(4)
        }
        .frame(width: max(10, CGFloat(clip.duration * 20)), height: 50)
        .offset(x: 30 + CGFloat(clip.startTime * 20), y: CGFloat(clip.track) * 58 + 2)
        .onTapGesture { state.selectedTimelineClipIDs = [clip.id] }
    }
}

struct TrimHandle: View {
    let onTrim: (CGFloat) -> Void
    @State private var dragAmount: CGFloat = 0
    var body: some View {
        RoundedRectangle(cornerRadius: 2).fill(Color.white.opacity(0.8)).frame(width: 6, height: 30).shadow(radius: 2)
            .gesture(DragGesture().onChanged { val in let delta = val.translation.width - dragAmount; dragAmount = val.translation.width; onTrim(delta) }.onEnded { _ in dragAmount = 0 })
    }
}

struct ClipThumbnailView: View {
    let url: URL; let isSelected: Bool; let track: Int
    @State private var image: NSImage?
    var body: some View {
        GeometryReader { geo in
            ZStack {
                if let img = image {
                    HStack(spacing: 0) {
                        let itemWidth = 50.0 * 1.77
                        let count = Int(ceil(geo.size.width / itemWidth))
                        ForEach(0..<max(1, count), id: \.self) { _ in Image(nsImage: img).resizable().aspectRatio(contentMode: .fill).frame(width: itemWidth, height: 50).clipped() }
                    }
                } else { Color.cyan.opacity(0.05) }
                if isSelected { RoundedRectangle(cornerRadius: 12).stroke(Color.cyan, lineWidth: 3).background(Color.cyan.opacity(0.1)) }
            }
        }.cornerRadius(12).onAppear { generateThumbnail() }
    }
    private func generateThumbnail() {
        Task {
            let isScoped = url.startAccessingSecurityScopedResource()
            defer { if isScoped { url.stopAccessingSecurityScopedResource() } }
            let generator = AVAssetImageGenerator(asset: AVAsset(url: url))
            generator.appliesPreferredTrackTransform = true
            if let cgImage = try? await generator.image(at: .zero).image {
                await MainActor.run { self.image = NSImage(cgImage: cgImage, size: NSSize(width: cgImage.width, height: cgImage.height)) }
            }
        }
    }
}

struct FilterThumbnailView: View { 
    let filterName: String; let baseImage: NSImage?; let isSelected: Bool
    @State private var filteredImage: NSImage?
    var body: some View { 
        VStack {
            ZStack {
                if let img = filteredImage ?? baseImage { Image(nsImage: img).resizable().aspectRatio(contentMode: .fill) }
                else { Color.primary.opacity(0.05).overlay(Image(systemName: "wand.and.stars").foregroundColor(.primary.opacity(0.3))) }
                if isSelected { RoundedRectangle(cornerRadius: 16).stroke(Color.cyan, lineWidth: 2.5).background(Color.cyan.opacity(0.15)) }
            }.frame(width: 80, height: 50).cornerRadius(16).clipped()
            Text(filterName).font(.system(size: 9, weight: isSelected ? .bold : .medium)).foregroundColor(isSelected ? .cyan : .primary.opacity(0.7))
        }.onAppear { applyFilter() }.onChange(of: baseImage) { _, _ in applyFilter() }
    } 
    private func applyFilter() {
        guard filterName != "Original", let img = baseImage, let tiff = img.tiffRepresentation, let ciImage = CIImage(data: tiff) else { filteredImage = baseImage; return }
        Task(priority: .background) {
            let output = FilterService.shared.applyCIFilter(to: ciImage, filterName: filterName)
            if let cgImage = CIContext().createCGImage(output, from: output.extent) {
                let newImg = NSImage(cgImage: cgImage, size: img.size)
                await MainActor.run { self.filteredImage = newImg }
            }
        }
    }
}

struct TimelineDropDelegate: DropDelegate {
    let state: AppState
    func performDrop(info: DropInfo) -> Bool {
        guard let provider = info.itemProviders(for: [.text]).first else { return false }
        provider.loadObject(ofClass: NSString.self) { (str, _) in
            if let uuidStr = str as? String, let uuid = UUID(uuidString: uuidStr), let clip = state.clips.first(where: { $0.id == uuid }) {
                DispatchQueue.main.async { state.addClipToTimeline(clip: clip, startTime: max(0, Double((info.location.x - 30) / 20)), track: max(0, min(Int(info.location.y / 58), state.videoTrackCount + state.audioTrackCount - 1))) }
            }
        }
        return true
    }
}

struct PlayheadView: View {
    let height: CGFloat; @EnvironmentObject var state: AppState
    var body: some View {
        Rectangle().fill(Color.red).frame(width: 2, height: height)
            .offset(x: 30 + CGFloat(state.currentTime * 20))
            .gesture(DragGesture().onChanged { val in state.seek(to: Double((val.location.x - 30) / 20)) })
    }
}
