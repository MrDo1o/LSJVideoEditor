import SwiftUI

@main
struct MyApp: App {
    var body: some Scene {
        WindowGroup {
            LSJSplashView(scale: 1.0, opacity: 1.0, barWidths: [10, 20, 30])
        }
    }
}
