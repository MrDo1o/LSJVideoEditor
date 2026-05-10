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
import CoreImage
import CoreImage.CIFilterBuiltins

class FilterService {
    static let shared = FilterService()
    
    private init() {}
    
    func loadEliteRegistry() -> [EliteModel] {
        let registryUrl = Bundle.main.url(forResource: "EliteRegistry", withExtension: "json") ?? 
            FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("LSJ-Video-Editor-Swift/LSJVideoEditor/EliteRegistry.json")
        
        guard let data = try? Data(contentsOf: registryUrl),
              let registry = try? JSONDecoder().decode(EliteRegistryData.self, from: data) else {
            return []
        }
        return registry.models
    }
    
    func applyCIFilter(to image: CIImage, filterName: String) -> CIImage {
        switch filterName {
        case "Apex": 
            let f = CIFilter.colorControls()
            f.inputImage = image
            f.saturation = 1.2
            f.contrast = 1.1
            return f.outputImage ?? image
        case "Prism": 
            let f = CIFilter.vibrance()
            f.inputImage = image
            f.amount = 1.5
            return f.outputImage ?? image
        case "Lumina": 
            let f = CIFilter.sharpenLuminance()
            f.inputImage = image
            f.sharpness = 1.5
            return f.outputImage ?? image
        case "Vector": 
            let f = CIFilter.noiseReduction()
            f.inputImage = image
            f.noiseLevel = 0.02
            f.sharpness = 0.4
            return f.outputImage ?? image
        case "Terra": 
            let f = CIFilter.colorControls()
            f.inputImage = image
            f.saturation = 1.4
            f.contrast = 1.05
            return f.outputImage ?? image
        case "Obsidian": 
            let f = CIFilter.colorControls()
            f.inputImage = image
            f.brightness = 0.1
            f.contrast = 1.3
            return f.outputImage ?? image
        case "Flux": 
            let f = CIFilter.colorControls()
            f.inputImage = image
            f.saturation = 0.8
            f.contrast = 1.1
            return f.outputImage ?? image
        case "Helios": 
            let f = CIFilter.temperatureAndTint()
            f.inputImage = image
            f.neutral = CIVector(x: 5500, y: 0)
            f.targetNeutral = CIVector(x: 5000, y: 0)
            return f.outputImage ?? image
        case "Stellar": 
            let f = CIFilter.sepiaTone()
            f.inputImage = image
            f.intensity = 0.3
            return f.outputImage ?? image
        case "Zenith": 
            let f = CIFilter.colorControls()
            f.inputImage = image
            f.saturation = 1.1
            f.contrast = 1.2
            return f.outputImage ?? image
        case "Aeon": 
            let f = CIFilter.colorControls()
            f.inputImage = image
            f.brightness = 0.05
            return f.outputImage ?? image
        case "Elysium": 
            let f = CIFilter.temperatureAndTint()
            f.inputImage = image
            f.neutral = CIVector(x: 6500, y: 0)
            f.targetNeutral = CIVector(x: 7500, y: 0)
            return f.outputImage ?? image
        case "Halo": 
            let f = CIFilter.bloom()
            f.inputImage = image
            f.intensity = 0.5
            f.radius = 5.0
            return f.outputImage ?? image
        case "Nova": 
            let f = CIFilter.colorControls()
            f.inputImage = image
            f.saturation = 1.5
            return f.outputImage ?? image
        case "Radiant": 
            let f = CIFilter.colorControls()
            f.inputImage = image
            f.contrast = 1.5
            return f.outputImage ?? image
        case "Hunter": 
            let f = CIFilter.colorControls()
            f.inputImage = image
            f.saturation = 0.6
            f.contrast = 1.4
            return f.outputImage ?? image
        case "Lyric": 
            let f = CIFilter.temperatureAndTint()
            f.inputImage = image
            f.neutral = CIVector(x: 6500, y: 0)
            f.targetNeutral = CIVector(x: 6000, y: 0)
            return f.outputImage ?? image
        case "Aero": 
            let f = CIFilter.colorMonochrome()
            f.inputImage = image
            f.color = CIColor(red: 0.8, green: 0.9, blue: 1.0)
            f.intensity = 0.5
            return f.outputImage ?? image
        case "Elite Zoom": 
            let f = CIFilter.colorControls()
            f.inputImage = image
            f.contrast = 1.1
            let zoomed = f.outputImage?.transformed(by: CGAffineTransform(scaleX: 1.25, y: 1.25).translatedBy(x: -image.extent.width * 0.1, y: -image.extent.height * 0.1))
            return zoomed?.cropped(to: image.extent) ?? image
        case "Elite Angle (Left)":
            let zoomed = image.transformed(by: CGAffineTransform(scaleX: 1.5, y: 1.5).translatedBy(x: 0, y: -image.extent.height * 0.25))
            return zoomed.cropped(to: image.extent)
        case "Elite Angle (Right)":
            let zoomed = image.transformed(by: CGAffineTransform(scaleX: 1.5, y: 1.5).translatedBy(x: -image.extent.width * 0.33, y: -image.extent.height * 0.25))
            return zoomed.cropped(to: image.extent)
        case "Elite Motion (Pan)":
            let zoomed = image.transformed(by: CGAffineTransform(scaleX: 1.2, y: 1.2).translatedBy(x: -image.extent.width * 0.05, y: -image.extent.height * 0.05))
            return zoomed.cropped(to: image.extent)
        default: 
            return image
        }
    }
}
