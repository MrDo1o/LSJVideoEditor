import SwiftUI

struct WelcomeView: View {
    @EnvironmentObject var state: AppState

    var body: some View {
        VStack(spacing: 40) {
            Spacer()

            VStack(spacing: 12) {
                Image(systemName: "film.stack")
                    .font(.system(size: 80))
                    .foregroundColor(.accentColor)
                
                Text("LSJ Video Editor")
                    .font(.system(size: 32, weight: .bold))
                
                Text("CapCut-Style Native NLE")
                    .font(.title3)
                    .foregroundColor(.secondary)
            }

            HStack(spacing: 20) {
                Button(action: { state.newProject() }) {
                    VStack(spacing: 12) {
                        Image(systemName: "plus.circle.fill")
                            .font(.title)
                        Text("New Project")
                            .font(.headline)
                    }
                    .frame(width: 160, height: 120)
                    .background(Color.accentColor)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
                .buttonStyle(.plain)

                Button(action: { state.openProject() }) {
                    VStack(spacing: 12) {
                        Image(systemName: "folder.fill")
                            .font(.title)
                        Text("Open Project")
                            .font(.headline)
                    }
                    .frame(width: 160, height: 120)
                    .background(Color(NSColor.controlBackgroundColor))
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color.secondary.opacity(0.3), lineWidth: 1)
                    )
                }
                .buttonStyle(.plain)
            }

            VStack(alignment: .leading, spacing: 15) {
                Text("Recent Projects")
                    .font(.headline)
                    .padding(.horizontal)

                ScrollView {
                    VStack(spacing: 1) {
                        ForEach(state.recentProjects, id: \.self) { url in
                            Button(action: { state.loadProject(url: url) }) {
                                HStack {
                                    Image(systemName: "doc.text.fill")
                                        .foregroundColor(.secondary)
                                    VStack(alignment: .leading) {
                                        Text(url.deletingPathExtension().lastPathComponent)
                                            .font(.body)
                                        Text(url.path)
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                            .lineLimit(1)
                                    }
                                    Spacer()
                                    Text(lastModifiedString(for: url))
                                        .font(.caption2)
                                        .foregroundColor(.secondary)
                                }
                                .padding(.vertical, 8)
                                .padding(.horizontal)
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)
                            Divider().padding(.horizontal)
                        }
                    }
                }
                .frame(width: 400, height: 200)
                .background(Color(NSColor.controlBackgroundColor))
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.secondary.opacity(0.3), lineWidth: 1)
                )
            }

            Spacer()
            
            HStack {
                Circle()
                    .fill(state.kbActive ? Color.green : Color.red)
                    .frame(width: 10, height: 10)
                Text(state.aiStatus)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.bottom, 20)
        }
        .frame(minWidth: 1000, minHeight: 700)
    }

    func lastModifiedString(for url: URL) -> String {
        guard let attributes = try? FileManager.default.attributesOfItem(atPath: url.path),
              let date = attributes[.modificationDate] as? Date else { return "" }
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .full
        return formatter.localizedString(for: date, relativeTo: Date())
    }
}
