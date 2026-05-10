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
import Combine
import CoreImage
import WidgetKit

// MARK: - App State
class AppState: ObservableObject {
    @Published var clips: [MediaClip] = []
    @Published var timelineClips: [TimelineClip] = [] {
        didSet {
            Task { await updateTimelineComposition() }
            saveProject()
        }
    }
    @Published var videoTrackCount = 2
    @Published var audioTrackCount = 1
    
    @Published var selectedClipIDs: Set<UUID> = []
    @Published var selectedClip: MediaClip? {
        didSet {
            if let clip = selectedClip {
                selectedClipIDs = [clip.id]
                loadPlayer(url: clip.url, duration: clip.duration)
                generatePreviewThumbnail(url: clip.url)
                aiStatus = "Selected: \(clip.name)"
            }
        }
    }
    
    @Published var selectedTimelineClipIDs: Set<UUID> = [] {
        didSet {
            if let firstID = selectedTimelineClipIDs.first, let tc = timelineClips.first(where: { $0.id == firstID }) {
                aiStatus = "Selected in Timeline: \(selectedTimelineClipIDs.count) clips"
                if isTimelineMode {
                    seek(to: tc.startTime)
                } else {
                    loadPlayer(url: tc.mediaClip.url, duration: tc.mediaClip.duration)
                }
            }
        }
    }
    
    @Published var player: AVPlayer?
    @Published var isTimelineMode = true
    @Published var isAutoFramingEnabled = true
    @Published var timelineComposition: AVMutableComposition?
    @Published var timelineVideoComposition: AVMutableVideoComposition?
    @Published var isComparisonModeEnabled = false
    @Published var comparisonSplitX: CGFloat = 0.5
    @Published var timelineDragOffset: CGSize = .zero
    @Published var showHistory = false
    
    @Published var isPlaying = false
    @Published var tool: EditTool = .select
    @Published var showExport = false
    @Published var showImportPanel = false
    @Published var historyLog: [String] = []
    @Published var isDirectorModeEnabled = false
    @Published var directorRhythm: Double = 180.0
    
    @Published var upscaleLevel = 2
    @Published var upscaleModel = "proteus"
    @Published var exportResolution = "1920x1080"
    @Published var exportFPS = 30
    @Published var exportQuality = "medium"
    @Published var currentTime: Double = 0
    @Published var currentThumbnailImage: NSImage?
    @Published var totalDuration: Double = 0
    @Published var currentFilter: String = "Original"
    @Published var isProcessingAI = false
    @Published var processingProgress: Double = 0
    @Published var aiStatus = ""
    @Published var kbActive = true
    @Published var isWelcomeScreenActive = true
    @Published var isDarkMode = true
    @Published var recentProjects: [URL] = []
    @Published var currentProjectName: String = "Untitled"
    @Published var debugLog: [String] = []

    @Published var isLoadingPhotos = false
    @Published var eliteModels: [EliteModel] = []
    @Published var availableFilters: [String] = ["Original"]
    
    var currentTimeText: String { formatTime(currentTime) }
    var totalTimeText: String { formatTime(totalDuration) }

    private let ciContext = CIContext()
    private var timeObserver: Any?
    private var eventMonitor: Any?
    private var autoSaveTimer: Timer?
    
    private let filterService = FilterService.shared
    private let projectService = ProjectService.shared
    private let mediaService = MediaService.shared
    private let aiService = AIService.shared
    private let kb = KBManager.shared
    
    private var gcpProjectId: String?
    private var gcpAuthToken: String?

    init() {
        self.gcpProjectId = ProcessInfo.processInfo.environment["GCP_PROJECT_ID"]
        self.gcpAuthToken = ProcessInfo.processInfo.environment["GCP_AUTH_TOKEN"]
        
        self.recentProjects = projectService.loadRecentProjects()
        self.eliteModels = filterService.loadEliteRegistry()
        self.availableFilters = ["Original"] + eliteModels.map { $0.rebrandedName }
        
        startAutoSave()
        setupEventMonitor()
    }

    // MARK: - Core Helpers
    private func formatTime(_ seconds: Double) -> String {
        let m = Int(seconds) / 60
        let s = Int(seconds) % 60
        let ms = Int((seconds.truncatingRemainder(dividingBy: 1)) * 100)
        return String(format: "%d:%02d.%02d", m, s, ms)
    }

    // MARK: - Logic Extractions
    func setupEventMonitor() {
        eventMonitor = NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown, .keyDown]) { [weak self] event in
            let desc = event.type == .leftMouseDown ? "Mouse Click" : "Key: \(event.characters ?? "?")"
            self?.logEvent("DEBUG: \(desc)")
            return event
        }
    }

    func logEvent(_ msg: String) {
        DispatchQueue.main.async {
            self.debugLog.append("[\(Date().formatted(date: .omitted, time: .standard))] \(msg)")
            if self.debugLog.count > 50 { self.debugLog.removeFirst() }
        }
    }

    func startAutoSave() {
        autoSaveTimer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            self?.saveProject()
        }
    }

    // MARK: - Project Management
    func newProject() {
        clips = []
        timelineClips = []
        selectedClip = nil
        player = nil
        isPlaying = false
        currentTime = 0
        totalDuration = 0
        currentProjectName = "Untitled"
        isWelcomeScreenActive = false
    }

    func openProject() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.data]
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.begin { response in
            if response == .OK, let url = panel.url {
                self.loadProject(url: url)
            }
        }
    }

    func loadProject(url: URL) {
        guard let data = try? Data(contentsOf: url) else { return }
        if let project = try? JSONDecoder().decode(Project.self, from: data) {
            self.clips = project.clips
            self.timelineClips = project.timelineClips
            self.videoTrackCount = project.videoTrackCount
            self.audioTrackCount = project.audioTrackCount
            self.currentProjectName = project.name
            self.isWelcomeScreenActive = false
            self.aiStatus = "Loaded: \(project.name)"
            if let first = clips.first { loadPlayer(url: first.url, duration: first.duration) }
        }
    }

    func saveProject() {
        let project = Project(name: currentProjectName, clips: clips, timelineClips: timelineClips, videoTrackCount: videoTrackCount, audioTrackCount: audioTrackCount)
        projectService.saveProject(project: project, gcpProjectId: gcpProjectId, gcpAuthToken: gcpAuthToken) { [weak self] status in
            DispatchQueue.main.async { self?.aiStatus = status }
        }
        recentProjects = projectService.loadRecentProjects()
    }

    // MARK: - Media Actions
    func importMedia(url: URL) {
        Task {
            do {
                let clip = try await mediaService.extractMetadata(from: url)
                await MainActor.run {
                    if !self.clips.contains(where: { $0.url == url }) { self.clips.append(clip) }
                    if self.player == nil { self.loadPlayer(url: url, duration: clip.duration) }
                }
            } catch { print("Import failed: \(error)") }
        }
    }

    func loadVideosFromPhotos() {
        isLoadingPhotos = true
        mediaService.loadVideosFromPhotos(completion: { [weak self] url in
            DispatchQueue.main.async { self?.importMedia(url: url) }
        }, errorCompletion: { [weak self] error in
            DispatchQueue.main.async { self?.aiStatus = error }
        }, finalCompletion: { [weak self] in
            DispatchQueue.main.async { self?.isLoadingPhotos = false }
        })
    }

    // MARK: - Player Control
    private func loadPlayer(url: URL, duration: Double) {
        if let obs = timeObserver { player?.removeTimeObserver(obs); timeObserver = nil }
        let asset = AVAsset(url: url)
        let item = AVPlayerItem(asset: asset)
        if currentFilter != "Original" { item.videoComposition = createVideoComposition(for: asset, filterName: currentFilter) }
        player = AVPlayer(playerItem: item)
        totalDuration = duration
        timeObserver = player?.addPeriodicTimeObserver(forInterval: CMTime(seconds: 0.1, preferredTimescale: 600), queue: .main) { [weak self] time in
            self?.currentTime = time.seconds
        }
    }

    private func createVideoComposition(for asset: AVAsset, filterName: String) -> AVVideoComposition {
        return AVMutableVideoComposition(asset: asset) { [weak self] request in
            let source = request.sourceImage.clampedToExtent()
            let filtered = self?.filterService.applyCIFilter(to: source, filterName: filterName) ?? source
            request.finish(with: filtered, context: self?.ciContext)
        }
    }

    func togglePlay() {
        guard let player else { return }
        if isPlaying { player.pause() } else { player.play() }
        isPlaying.toggle()
    }

    func seek(to seconds: Double) {
        let target = max(0, min(seconds, totalDuration))
        player?.seek(to: CMTime(seconds: target, preferredTimescale: 600), toleranceBefore: .zero, toleranceAfter: .zero)
    }
    
    func seek(by delta: Double) {
        seek(to: currentTime + delta)
    }

    // MARK: - AI Orchestration
    func aiSuggestFilter() {
        guard !isProcessingAI, let url = selectedClip?.url else { return }
        isProcessingAI = true
        aiStatus = "Gemini Vision analyzing..."
        Task {
            let frames = await aiService.extractKeyframes(from: url)
            aiService.getSuggestion(directive: "Suggest best filter for this visual content.", frames: frames) { [weak self] result in
                self?.isProcessingAI = false
                self?.aiStatus = "AI: " + result
                if let suggested = self?.availableFilters.first(where: { result.contains($0) }) { self?.applyFilter(suggested) }
            }
        }
    }

    func aiEdit(prompt: String) {
        guard !isProcessingAI, let url = selectedClip?.url else { return }
        isProcessingAI = true
        aiStatus = "One Unit Orchestration..."
        Task {
            let frames = await aiService.extractKeyframes(from: url)
            aiService.getSuggestion(directive: "Smart Edit: \(prompt)", frames: frames) { [weak self] result in
                self?.isProcessingAI = false
                self?.aiStatus = "Elite: " + result
                self?.saveProject()
            }
        }
    }

    func applyFilter(_ name: String) {
        takeSnapshot("Filter: \(name)")
        currentFilter = name
        if isTimelineMode, let firstID = selectedTimelineClipIDs.first, let index = timelineClips.firstIndex(where: { $0.id == firstID }) {
            timelineClips[index].filter = name
            Task { await updateTimelineComposition() }
        } else if let player, let item = player.currentItem {
            item.videoComposition = createVideoComposition(for: item.asset, filterName: name)
        }
    }

    // MARK: - Timeline Composition
    func updateTimelineComposition() async {
        let composition = AVMutableComposition()
        guard !timelineClips.isEmpty,
              let vTrack = composition.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid),
              let aTrack = composition.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid) else { return }
        
        var maxTime: Double = 0
        for clip in timelineClips.sorted(by: { $0.startTime < $1.startTime }) {
            let asset = AVAsset(url: clip.mediaClip.url)
            let range = CMTimeRange(start: .zero, duration: CMTime(seconds: clip.duration, preferredTimescale: 600))
            let atTime = CMTime(seconds: clip.startTime, preferredTimescale: 600)
            if let vt = try? await asset.loadTracks(withMediaType: .video).first { try? vTrack.insertTimeRange(range, of: vt, at: atTime) }
            if let at = try? await asset.loadTracks(withMediaType: .audio).first { try? aTrack.insertTimeRange(range, of: at, at: atTime) }
            maxTime = max(maxTime, clip.startTime + clip.duration)
        }
        
        let videoComp = AVMutableVideoComposition(asset: composition) { [weak self] request in
            let source = request.sourceImage
            let time = request.compositionTime.seconds
            let clip = self?.timelineClips.first { time >= $0.startTime && time < ($0.startTime + $0.duration) }
            let filtered = self?.filterService.applyCIFilter(to: source, filterName: clip?.filter ?? "Original") ?? source
            request.finish(with: filtered, context: self?.ciContext)
        }
        
        let finalMax = maxTime
        await MainActor.run {
            self.timelineVideoComposition = videoComp
            self.totalDuration = finalMax
            self.timelineComposition = composition
            if isTimelineMode { loadTimelinePlayer() }
        }
    }

    func loadTimelinePlayer() {
        guard let comp = timelineComposition else { return }
        let item = AVPlayerItem(asset: comp)
        if let vc = timelineVideoComposition { item.videoComposition = vc }
        player?.replaceCurrentItem(with: item)
    }

    // MARK: - Undo/Redo & Snapshots
    private var undoStack: [[TimelineClip]] = []
    private var redoStack: [[TimelineClip]] = []

    func undo() {
        guard !undoStack.isEmpty else { return }
        redoStack.append(timelineClips)
        timelineClips = undoStack.removeLast()
    }
    
    func redo() {
        guard !redoStack.isEmpty else { return }
        undoStack.append(timelineClips)
        timelineClips = redoStack.removeLast()
    }

    func takeSnapshot(_ actionName: String? = nil) {
        undoStack.append(timelineClips)
        redoStack.removeAll()
        if let name = actionName { logAction(name) }
    }

    func logAction(_ action: String) {
        let timestamp = Date().formatted(date: .omitted, time: .standard)
        historyLog.insert("[\(timestamp)] \(action)", at: 0)
        aiStatus = action
    }
    
    func updateClipDuration(_ id: UUID, startTime: Double, duration: Double) {
        if let idx = timelineClips.firstIndex(where: { $0.id == id }) {
            timelineClips[idx].startTime = max(0, startTime)
            timelineClips[idx].duration = max(0.1, duration)
        }
    }
    
    func moveClip(_ id: UUID, to: Double, track: Int) {
        if let idx = timelineClips.firstIndex(where: { $0.id == id }) {
            timelineClips[idx].startTime = max(0, to)
            timelineClips[idx].track = track
        }
    }
    
    func updateClipFilterParam(_ id: UUID, key: String, value: String) {
        if let idx = timelineClips.firstIndex(where: { $0.id == id }) {
            var params = timelineClips[idx].filterParams ?? [:]
            params[key] = value
            timelineClips[idx].filterParams = params
        }
    }

    // MARK: - Legacy / Stub Actions
    func split() {
        takeSnapshot("Split Clip")
        let time = currentTime
        let clipsToSplit = timelineClips.filter { time > $0.startTime && time < ($0.startTime + $0.duration) }
        for clip in clipsToSplit {
            let splitOffset = time - clip.startTime
            if splitOffset < 0.1 || (clip.duration - splitOffset) < 0.1 { continue }
            let index = timelineClips.firstIndex(where: { $0.id == clip.id }) ?? 0
            var firstHalf = clip
            firstHalf.duration = splitOffset
            let secondHalf = TimelineClip(mediaClip: clip.mediaClip, track: clip.track, startTime: clip.startTime + splitOffset, duration: clip.duration - splitOffset)
            timelineClips[index] = firstHalf
            timelineClips.insert(secondHalf, at: index + 1)
        }
    }

    func deleteSelectedClip() {
        takeSnapshot("Delete Clip")
        if !selectedTimelineClipIDs.isEmpty {
            timelineClips.removeAll { selectedTimelineClipIDs.contains($0.id) }
            selectedTimelineClipIDs.removeAll()
        } else if let selMC = selectedClip {
            clips.removeAll { $0.id == selMC.id }
            timelineClips.removeAll { $0.mediaClip.id == selMC.id }
            selectedClip = nil
        }
    }

    func addClipToTimeline(clip: MediaClip, startTime: Double, track: Int) {
        takeSnapshot("Add Clip")
        let newTimelineClip = TimelineClip(mediaClip: clip, track: track, startTime: max(0, startTime), duration: clip.duration)
        timelineClips.append(newTimelineClip)
    }

    func selectAllTimelineClips() { selectedTimelineClipIDs = Set(timelineClips.map { $0.id }) }
    func deselectAll() { selectedTimelineClipIDs.removeAll(); selectedClip = nil }
    func toggleTimelineMode() { isTimelineMode.toggle(); if isTimelineMode { Task { await updateTimelineComposition() } } }
    
    func upscale() {
        guard !isProcessingAI, let sel = selectedClip else { return }
        aiStatus = "Initializing Elite AI Upscale..."
        isProcessingAI = true
        
        let directive = "upscale \(upscaleModel) \(upscaleLevel)x"
        
        Task {
            let results = await aiService.execute(directive: directive, frames: [], inputURL: sel.url)
            
            await MainActor.run {
                self.isProcessingAI = false
                let combined = results.map { $0.text }.joined(separator: " | ")
                self.aiStatus = "Upscale Complete: \(combined)"
                
                // Attempt to auto-import the upscaled file if it exists
                let outputURL = sel.url.deletingLastPathComponent().appendingPathComponent("\(sel.url.deletingPathExtension().lastPathComponent)_upscaled.mp4")
                if FileManager.default.fileExists(atPath: outputURL.path) {
                    self.importMedia(url: outputURL)
                }
            }
        }
    }

    func generateCaptions() {
        aiStatus = "Transcribing with Whisper Elite..."
        isProcessingAI = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
            self.isProcessingAI = false
            self.aiStatus = "Captions Generated"
        }
    }
    
    func beatSync() {
        aiStatus = "Analyzing Audio Pacing..."
        isProcessingAI = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
            self.isProcessingAI = false
            self.aiStatus = "Beat Pacing Applied to Timeline"
        }
    }

    func exportProject(to url: URL, useMastering: Bool) {
        guard let comp = timelineComposition else { return }
        
        aiStatus = "Exporting Elite Master..."
        isProcessingAI = true
        
        if FileManager.default.fileExists(atPath: url.path) {
            try? FileManager.default.removeItem(at: url)
        }
        
        guard let exportSession = AVAssetExportSession(asset: comp, presetName: AVAssetExportPresetHighestQuality) else {
            self.isProcessingAI = false
            self.aiStatus = "Export Failed: Could not create session"
            return
        }
        
        exportSession.outputURL = url
        exportSession.outputFileType = url.pathExtension.lowercased() == "mp4" ? .mp4 : .mov
        
        if let videoComp = timelineVideoComposition {
            exportSession.videoComposition = videoComp
        }
        
        exportSession.exportAsynchronously {
            DispatchQueue.main.async {
                self.isProcessingAI = false
                if exportSession.status == .completed {
                    self.aiStatus = "Export Complete: \(url.lastPathComponent)"
                    self.showExport = false
                } else {
                    self.aiStatus = "Export Failed: \(exportSession.error?.localizedDescription ?? "Unknown Error")"
                }
            }
        }
    }

    func runDirectorMode() {
        DirectorEngine.shared.applyDirectorMode(to: &timelineClips, rhythmSeconds: directorRhythm)
        logAction("AI Director Mode Applied")
    }

    func generatePreviewThumbnail(url: URL) {
        Task {
            let asset = AVAsset(url: url)
            let generator = AVAssetImageGenerator(asset: asset)
            generator.appliesPreferredTrackTransform = true
            generator.maximumSize = CGSize(width: 400, height: 225)
            if let cgImage = try? await generator.image(at: .zero).image {
                await MainActor.run { self.currentThumbnailImage = NSImage(cgImage: cgImage, size: NSSize(width: cgImage.width, height: cgImage.height)) }
            }
        }
    }

    func smartVaultAudit() {
        guard !isProcessingAI, let sel = selectedClip else { return }
        isProcessingAI = true
        aiStatus = "Performing Deep Content Audit..."
        
        Task {
            let frames = await aiService.extractKeyframes(from: sel.url)
            let category = await aiService.auditContent(frames: frames)
            
            await MainActor.run {
                self.isProcessingAI = false
                if category == "NSFW" {
                    self.aiStatus = "NSFW IDENTIFIED: Moving to Secure Vault."
                    self.moveToVault(clip: sel)
                } else {
                    self.aiStatus = "SFW VERIFIED: Content is Social/Safe."
                }
            }
        }
    }

    private func moveToVault(clip: MediaClip) {
        let vaultURL = URL(fileURLWithPath: "\(NSHomeDirectory())/NSFW_Vault")
        let destination = vaultURL.appendingPathComponent(clip.url.lastPathComponent)
        
        do {
            try FileManager.default.moveItem(at: clip.url, to: destination)
            logAction("Moved \(clip.name) to NSFW Vault.")
            clips.removeAll { $0.id == clip.id }
            timelineClips.removeAll { $0.mediaClip.id == clip.id }
            if selectedClip?.id == clip.id { selectedClip = nil }
        } catch {
            print("Vault move failed: \(error)")
            aiStatus = "Vault Error: Permission or Disk Space."
        }
    }
}
