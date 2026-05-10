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

@main
struct LSJVideoEditorApp: App {
  @StateObject private var appState = AppState()

  var body: some Scene {
    WindowGroup {
      ContentView()
        .environmentObject(appState)
        #if os(macOS)
          .frame(minWidth: 1200, minHeight: 800)
          .navigationTitle("")
        #endif
    }
    #if os(macOS)
      .windowStyle(.hiddenTitleBar)
      .defaultSize(width: 1600, height: 1000)
      .commands {
          EditorCommands(appState: appState)
      }
    #endif

    #if os(macOS)
      WindowGroup("Media Bin", id: "MediaBinWindow") {
        EliteMediaBin()
          .environmentObject(appState)
          .frame(minWidth: 300, idealWidth: 350, minHeight: 500)
          .background(VisualEffectView().ignoresSafeArea())
      }
      .windowStyle(.hiddenTitleBar)
    #endif
  }
}

#if os(macOS)
struct EditorCommands: Commands {
  @ObservedObject var appState: AppState
  
  var body: some Commands {
    // File Menu
    CommandGroup(replacing: .newItem) {
      Button("New Project") { appState.newProject() }
        .keyboardShortcut("n")
      Button("Open Project…") { appState.openProject() }
        .keyboardShortcut("o")
      Divider()
      Button("Import Media…") { appState.showImportPanel = true }
        .keyboardShortcut("i")
      Divider()
      Button("Save Project") { appState.saveProject() }
        .keyboardShortcut("s")
      Button("Save As…") {}
        .keyboardShortcut("s", modifiers: [.command, .shift])
      Divider()
      Button("Export…") { appState.showExport = true }
        .keyboardShortcut("e")
    }
    
    // Edit Menu
    CommandGroup(after: .pasteboard) {
      Divider()
      Button("Select All Timeline") { appState.selectAllTimelineClips() }
        .keyboardShortcut("a")
      Button("Select All Media") { appState.selectAllMediaClips() }
        .keyboardShortcut("a", modifiers: [.command, .shift])
      Button("Deselect All") { appState.deselectAll() }
        .keyboardShortcut("d", modifiers: [.command, .shift])
      Divider()
      Button("Split at Playhead") { appState.split() }
        .keyboardShortcut("b")
      Button("Delete Selected") { appState.deleteSelectedClip() }
        .keyboardShortcut(.delete)
      Divider()
      Button("Select Tool") { appState.tool = .select }
        .keyboardShortcut("v")
      Button("Cut Tool") { appState.tool = .cut }
        .keyboardShortcut("c", modifiers: [.command, .shift])
      Divider()
      Button("Toggle Timeline Mode") { appState.toggleTimelineMode() }
        .keyboardShortcut("t", modifiers: [.command, .shift])
    }
    
    // View Menu
    CommandGroup(after: .toolbar) {
      Divider()
      Button("Zoom In Timeline") {}
        .keyboardShortcut("=")
      Button("Zoom Out Timeline") {}
        .keyboardShortcut("-")
      Button("Fit Timeline") {}
        .keyboardShortcut("0", modifiers: [.command, .shift])
    }
    
    // Playback Menu
    CommandMenu("Playback") {
      Button("Play / Pause") { appState.togglePlay() }
        .keyboardShortcut(" ", modifiers: [])
      Divider()
      Button("Skip Forward 5s") { appState.seek(by: 5) }
        .keyboardShortcut(.rightArrow)
      Button("Skip Back 5s") { appState.seek(by: -5) }
        .keyboardShortcut(.leftArrow)
      Button("Skip Forward 30s") { appState.seek(by: 30) }
        .keyboardShortcut(.rightArrow, modifiers: [.command, .shift])
      Button("Skip Back 30s") { appState.seek(by: -30) }
        .keyboardShortcut(.leftArrow, modifiers: [.command, .shift])
      Divider()
      Button("Go to Start") { appState.seek(by: -appState.currentTime) }
        .keyboardShortcut(.home)
    }
    
    CommandMenu("AI Tools") {
      Button("Smart Edit…") { appState.aiEdit(prompt: "Perform a smart creative edit") }
        .keyboardShortcut("g", modifiers: [.command, .shift])
      Button("Smart Cut (AutoShot)") {
        appState.aiEdit(prompt: "Vanguard: Detect scenes and auto-cut")
      }
      .keyboardShortcut("k", modifiers: [.command, .shift])
      Divider()
      Button("Elite HDR Master") {
        appState.aiEdit(prompt: "Solstice: Apply Hyperion HDR mastering")
      }
      Button("Full-Frame Stabilize") {
        appState.aiEdit(prompt: "Stabilizer: Apply Elite Stabilization")
      }
      Divider()
      Menu("Upscale (Enhance Models)") {
        ForEach(appState.eliteModels.filter { $0.category == "Enhance" }, id: \.id) { model in
          Menu(model.rebrandedName) {
            Button("2x Scale") {
              appState.upscaleModel = model.shortName
              appState.upscaleLevel = 2
              appState.upscale()
            }
            Button("4x Scale") {
              appState.upscaleModel = model.shortName
              appState.upscaleLevel = 4
              appState.upscale()
            }
          }
        }
      }
      Divider()
      Button("Generate Captions") { appState.generateCaptions() }
      Button("Action Pulse") { appState.actionPulse() }
    }
    
    // Help Menu
    CommandGroup(replacing: .help) {
      Button("LSJ Systems Documentation") {
        if let url = URL(string: "https://LSJSystems.com") {
          NSWorkspace.shared.open(url)
        }
      }
      Button("Contact Support") {
        if let url = URL(string: "mailto:support@lsjsystems.com") {
          NSWorkspace.shared.open(url)
        }
      }
      Divider()
      Text("LSJ Elite Video Editor™")
      Text("© 2026 LSJ Systems. All Rights Reserved.")
    }
    
    // System Settings & Privacy
    CommandGroup(after: .appInfo) {
      Button("Elite System Settings…") {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Photos") {
          NSWorkspace.shared.open(url)
        }
      }
      .keyboardShortcut(",", modifiers: .command)
    }
    
    // Filters Menu
    CommandMenu("Filters") {
      ForEach(appState.availableFilters, id: \.self) { f in
        Button(f) { appState.applyFilter(f) }
      }
    }
  }
}
#endif
