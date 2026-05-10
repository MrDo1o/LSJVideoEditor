/*
 *  LSJ ELITE VIDEO EDITOR
 *  Digital Architecture by LSJ Systems TM
 *  __________________________________________________________________
 *
 *  Proprietary & Confidential. 
 *  Unauthorized copying of this file, via any medium is strictly prohibited.
 *  Architected for Professional Production & Red Team Operations.
 */

import Foundation
import AVFoundation

// MARK: - Models
struct MediaClip: Identifiable, Codable, Equatable {
    var id = UUID()
    let url: URL
    let name: String
    var duration: Double = 0
    var width: Int?
    var height: Int?
    var codec: String?
    var fps: Double?
    var isAudio: Bool = false

    var durationText: String {
        let m = Int(duration) / 60
        let s = Int(duration) % 60
        return String(format: "%d:%02d", m, s)
    }
}

struct TimelineClip: Identifiable, Codable, Equatable {
    var id = UUID()
    let mediaClip: MediaClip
    var track: Int = 0
    var startTime: Double = 0
    var duration: Double
    var isFlagged: Bool? = false
    var filter: String? = "Original"
    var filterParams: [String: String]? // Dynamic AI tool parameters
    var captionText: String? // AI Auto-Captions
    var transitionType: String? // Smart Transitions: "None", "Fade", "Wipe"
    var name: String { mediaClip.name }
}

struct Project: Codable {
    let name: String
    let clips: [MediaClip]
    let timelineClips: [TimelineClip]
    let videoTrackCount: Int
    let audioTrackCount: Int
}

struct EliteParameter: Codable {
    let name: String
    let guiName: String
    let `default`: Double?
    let min: Double?
    let max: Double?
}

struct EliteModel: Codable {
    let id: String
    let rebrandedName: String
    let originalName: String
    let shortName: String
    let version: String
    let category: String?
    let parameters: [EliteParameter]?
}

struct EliteRegistryData: Codable {
    let models: [EliteModel]
}

enum EditTool { case select, cut }

struct AIResponse: Decodable {
    let agent: String
    let text: String
}
