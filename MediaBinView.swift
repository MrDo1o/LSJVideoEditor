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
import PhotosUI
import AVFoundation

struct EliteMediaBin: View {
    @EnvironmentObject var state: AppState
    @State private var isDragOver = false
    @State private var selectedPhotos: [PhotosPickerItem] = []
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Media Bin").font(.title2.weight(.semibold))
                Spacer()
                Button(action: {
                    let panel = NSOpenPanel()
                    panel.allowsMultipleSelection = true
                    panel.canChooseDirectories = false
                    panel.canChooseFiles = true
                    panel.allowedContentTypes = [.movie, .mpeg4Movie, .quickTimeMovie]
                    if panel.runModal() == .OK {
                        for url in panel.urls {
                            state.importMedia(url: url)
                        }
                    }
                }) {
                    Image(systemName: "externaldrive.fill").foregroundColor(.cyan).font(.title3)
                }.buttonStyle(.plain)
                
                PhotosPicker(selection: $selectedPhotos, matching: .videos) {
                    Image(systemName: "photo.on.rectangle.angled").foregroundColor(.secondary).font(.title3)
                }.buttonStyle(.plain)
                .onChange(of: selectedPhotos) { _, items in
                    loadPhotos(items)
                }
                
                Button(action: { state.smartVaultAudit() }) {
                    Image(systemName: "lock.shield.fill")
                        .foregroundColor(state.isProcessingAI ? .secondary : .orange)
                        .font(.title3)
                }
                .buttonStyle(.plain)
                .help("AI Smart Audit: Identify & Move NSFW Content to Vault")
            }
            
            ScrollView {
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 16) {
                    ForEach(state.clips) { clip in
                        EliteClipCard(clip: clip)
                            .onTapGesture { state.selectedClip = clip }
                    }
                }
            }
        }
        .padding(20)
        .background(.regularMaterial)
        .cornerRadius(30)
        .overlay(RoundedRectangle(cornerRadius: 30).stroke(Color.primary.opacity(0.05), lineWidth: 1))
        .shadow(color: .black.opacity(0.05), radius: 15, y: 5)
        .onDrop(of: [.fileURL], isTargeted: $isDragOver) { providers in
            for provider in providers {
                provider.loadObject(ofClass: NSURL.self) { (url, _) in
                    if let url = url as? URL { DispatchQueue.main.async { state.importMedia(url: url) } }
                }
            }
            return true
        }
    }
    
    private func loadPhotos(_ items: [PhotosPickerItem]) {
        for item in items {
            item.loadTransferable(type: MovieTransferable.self) { result in
                switch result {
                case .success(let movie?):
                    DispatchQueue.main.async { state.importMedia(url: movie.url) }
                case .success(nil):
                    print("Failed to load movie: nil")
                case .failure(let error):
                    print("Error loading movie: \(error.localizedDescription)")
                }
            }
        }
    }
}

struct EliteClipCard: View {
    let clip: MediaClip
    @EnvironmentObject var state: AppState
    var isSelected: Bool { state.selectedClip?.id == clip.id }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ZStack(alignment: .topTrailing) {
                MediaClipThumbnailView(url: clip.url)
                    .frame(height: 80)
                    .cornerRadius(12)
                
                Button(action: { state.addClipToTimeline(clip: clip, startTime: state.currentTime, track: 0) }) {
                    Image(systemName: "plus")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.white)
                        .padding(6)
                        .background(Color.black.opacity(0.6))
                        .clipShape(Circle())
                }.buttonStyle(.plain).padding(6)
            }
            Text(clip.name).font(.system(size: 11, weight: .medium)).lineLimit(1).foregroundColor(.primary)
        }
        .padding(8)
        .background(isSelected ? Color.cyan.opacity(0.15) : Color.primary.opacity(0.03))
        .cornerRadius(20)
        .overlay(RoundedRectangle(cornerRadius: 20).stroke(isSelected ? Color.cyan : Color.clear, lineWidth: 1.5))
        .shadow(color: isSelected ? .cyan.opacity(0.3) : .clear, radius: 8, y: 4)
        .onDrag { NSItemProvider(object: clip.id.uuidString as NSString) }
    }
}

struct MediaClipThumbnailView: View {
    let url: URL
    @State private var image: NSImage?
    var body: some View {
        ZStack {
            if let img = image {
                Image(nsImage: img).resizable().aspectRatio(contentMode: .fill).clipped()
            } else {
                Color.gray.opacity(0.2); Image(systemName: "film").foregroundColor(.secondary)
            }
        }.onAppear { generateThumbnail() }
    }
    private func generateThumbnail() {
        Task {
            let isScoped = url.startAccessingSecurityScopedResource()
            defer { if isScoped { url.stopAccessingSecurityScopedResource() } }
            let asset = AVAsset(url: url)
            let generator = AVAssetImageGenerator(asset: asset)
            generator.appliesPreferredTrackTransform = true
            generator.maximumSize = CGSize(width: 400, height: 225)
            if let cgImage = try? await generator.image(at: .zero).image {
                await MainActor.run { self.image = NSImage(cgImage: cgImage, size: NSSize(width: cgImage.width, height: cgImage.height)) }
            }
        }
    }
}
