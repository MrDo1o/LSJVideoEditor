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

struct EliteHomeView: View {
    @EnvironmentObject var state: AppState
    @State private var isDragOver = false
    @State private var selectedPhotos: [PhotosPickerItem] = []
    
    var body: some View {
        VStack {
            Spacer()
            
            VStack(spacing: 24) {
                Image(systemName: "bolt.horizontal.circle.fill")
                    .font(.system(size: 80, weight: .ultraLight))
                    .foregroundStyle(.linearGradient(colors: [.cyan, .purple], startPoint: .topLeading, endPoint: .bottomTrailing))
                    .shadow(color: .cyan.opacity(0.5), radius: 20)
                
                Text("LSJ Elite Video Editor")
                    .font(.system(size: 42, weight: .thin, design: .default))
                    .tracking(2)
                
                Text("Drop Media to Begin Production")
                    .font(.title3)
                    .foregroundColor(.secondary)
                
                HStack(spacing: 30) {
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
                        HStack {
                            Image(systemName: "externaldrive.fill")
                            Text("Import from Disk")
                        }
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.white)
                        .padding(.horizontal, 28)
                        .padding(.vertical, 14)
                        .background(
                            Capsule().fill(LinearGradient(colors: [.cyan, .blue], startPoint: .topLeading, endPoint: .bottomTrailing))
                        )
                        .shadow(color: .cyan.opacity(0.4), radius: 10, y: 5)
                    }.buttonStyle(.plain)
                    
                    PhotosPicker(selection: $selectedPhotos, matching: .videos) {
                        HStack {
                            Image(systemName: "photo.on.rectangle.angled")
                            Text("Photos Album")
                        }
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.primary)
                        .padding(.horizontal, 28)
                        .padding(.vertical, 14)
                        .background(
                            Capsule().fill(Color.primary.opacity(0.05))
                        )
                    }.buttonStyle(.plain)
                    .onChange(of: selectedPhotos) { _, items in
                        loadPhotos(items)
                    }
                    
                    Button(action: { state.openProject() }) {
                        HStack {
                            Image(systemName: "folder.fill")
                            Text("Open Project")
                        }
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.primary)
                        .padding(.horizontal, 28)
                        .padding(.vertical, 14)
                        .background(.regularMaterial)
                        .clipShape(Capsule())
                        .shadow(color: .black.opacity(0.1), radius: 10, y: 5)
                        .overlay(Capsule().stroke(Color.primary.opacity(0.1), lineWidth: 1))
                    }.buttonStyle(.plain)
                }
                .padding(.top, 20)
            }
            .padding(60)
            .background(
                RoundedRectangle(cornerRadius: 40)
                    .fill(isDragOver ? Color.cyan.opacity(0.1) : Color.clear)
                    .overlay(
                        RoundedRectangle(cornerRadius: 40)
                            .stroke(isDragOver ? Color.cyan : Color.primary.opacity(0.05), style: StrokeStyle(lineWidth: 2, dash: [10, 10]))
                    )
            )
            .onDrop(of: [.fileURL], isTargeted: $isDragOver) { providers in
                for provider in providers {
                    provider.loadObject(ofClass: NSURL.self) { (url, _) in
                        if let url = url as? URL { DispatchQueue.main.async { state.importMedia(url: url) } }
                    }
                }
                return true
            }
            
            Spacer()
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
