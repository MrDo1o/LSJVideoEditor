import AppKit

struct EliteWidgetComponent: View {
    let image: NSImage
    let size: NSSize

    var body: some View {
        Image(nsImage: image)
            .resizable()
            .frame(width: size.width, height: size.height)
    }
}
