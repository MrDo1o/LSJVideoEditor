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
import AppKit

class AIService {
    static let shared = AIService()
    private let ai = OneUnitAI()
    
    private init() {}
    
    func extractKeyframes(from url: URL) async -> [String] {
        let asset = AVAsset(url: url)
        let generator = AVAssetImageGenerator(asset: asset)
        generator.appliesPreferredTrackTransform = true
        generator.maximumSize = CGSize(width: 640, height: 360)
        
        var base64Frames: [String] = []
        
        do {
            let duration = try await asset.load(.duration).seconds
            let times = [
                CMTime(seconds: duration * 0.1, preferredTimescale: 600),
                CMTime(seconds: duration * 0.5, preferredTimescale: 600),
                CMTime(seconds: duration * 0.9, preferredTimescale: 600)
            ]
            
            for time in times {
                let cgImage = try await generator.image(at: time).image
                let bitmapRep = NSBitmapImageRep(cgImage: cgImage)
                if let jpegData = bitmapRep.representation(using: .jpeg, properties: [.compressionFactor: 0.6]) {
                    base64Frames.append(jpegData.base64EncodedString())
                }
            }
        } catch {
            print("Failed to extract multimodal frames: \(error)")
        }
        
        return base64Frames
    }
    
    func getSuggestion(directive: String, frames: [String], completion: @escaping (String) -> Void) {
        Task {
            let results = await ai.execute(directive: directive, frames: frames)
            let combined = results.map { "\($0.agent): \($0.text)" }.joined(separator: "\n\n")
            await MainActor.run {
                completion(combined)
            }
        }
    }
    
    func execute(directive: String, frames: [String] = [], inputURL: URL? = nil) async -> [AIResponse] {
        return await ai.execute(directive: directive, frames: frames, inputURL: inputURL)
    }
    
    func auditContent(frames: [String]) async -> String {
        let directive = """
            CRITICAL CONTENT AUDIT:
            Analyze these frames. Distinguish between standard social content (friends sitting, talking, casual activities) and NSFW/Adult content (explicit nudity, adult themes).
            
            The goal is to prevent accidental leakage of private adult content while keeping normal videos of friends and colleagues in the primary bin.
            
            Return ONLY 'NSFW' if explicit adult content is detected.
            Return ONLY 'SAFE' if the content is social, professional, or non-explicit.
            """
        let results = await ai.execute(directive: directive, frames: frames)
        let verdict = results.map { $0.text.uppercased() }.joined(separator: " ")
        return verdict.contains("NSFW") ? "NSFW" : "SAFE"
    }
}
