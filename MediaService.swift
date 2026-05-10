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
import Photos

class MediaService {
    static let shared = MediaService()
    
    private init() {}
    
    func extractMetadata(from url: URL) async throws -> MediaClip {
        let asset = AVAsset(url: url)
        let duration = try await asset.load(.duration).seconds
        let tracks = try await asset.load(.tracks)
        let videoTrack = tracks.first { $0.mediaType == .video }

        var width: Int?
        var height: Int?
        var fps: Double?
        var codec: String?

        if let vt = videoTrack {
            let size = try await vt.load(.naturalSize)
            width = Int(size.width)
            height = Int(size.height)
            let rate = try await vt.load(.nominalFrameRate)
            fps = Double(rate)
            let descs = try await vt.load(.formatDescriptions)
            if let desc = descs.first {
                let fourCC = CMFormatDescriptionGetMediaSubType(desc)
                codec = fourCCToString(fourCC)
            }
        }

        let isAudio = videoTrack == nil
        return MediaClip(url: url, name: url.lastPathComponent, duration: duration, width: width, height: height, codec: codec, fps: fps, isAudio: isAudio)
    }
    
    func loadVideosFromPhotos(completion: @escaping (URL) -> Void, errorCompletion: @escaping (String) -> Void, finalCompletion: @escaping () -> Void) {
        PHPhotoLibrary.requestAuthorization(for: .readWrite) { status in
            guard status == .authorized || status == .limited else {
                errorCompletion("Photos access denied")
                finalCompletion()
                return
            }
            let opts = PHFetchOptions()
            opts.predicate = NSPredicate(format: "mediaType == %d", PHAssetMediaType.video.rawValue)
            opts.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: false)]
            opts.fetchLimit = 20
            let assets = PHAsset.fetchAssets(with: opts)
            let mgr = PHImageManager.default()
            let vidOpts = PHVideoRequestOptions()
            vidOpts.isNetworkAccessAllowed = true
            vidOpts.deliveryMode = .highQualityFormat
            
            var remaining = assets.count
            if remaining == 0 {
                finalCompletion()
                return
            }
            
            assets.enumerateObjects { asset, _, _ in
                mgr.requestAVAsset(forVideo: asset, options: vidOpts) { avAsset, _, _ in
                    if let urlAsset = avAsset as? AVURLAsset {
                        completion(urlAsset.url)
                    }
                    remaining -= 1
                    if remaining <= 0 { finalCompletion() }
                }
            }
        }
    }

    private func fourCCToString(_ fourCC: FourCharCode) -> String {
        let n = Int(fourCC)
        var s: String = ""
        let characterCount = 4
        for i in 0..<characterCount {
            let charCode = (n >> (8 * (3 - i))) & 0xFF
            if let scalar = UnicodeScalar(charCode) {
                s.append(Character(scalar))
            }
        }
        return s.trimmingCharacters(in: .whitespaces)
    }
}
