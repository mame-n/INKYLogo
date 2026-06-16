import AppKit
import Foundation

let output = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "lighthouse_kanji.png"
let source = CommandLine.arguments.count > 2
    ? CommandLine.arguments[2]
    : "/Users/nakauchishouichi/Library/Mobile Documents/com~apple~CloudDocs/那須野崎プログラミング倶楽部/Logo/494267D0-2390-4BDB-903F-D782C6A5ABAC-E.png"

let canvasSize = NSSize(width: 250, height: 122)
let image = NSImage(size: canvasSize)

func alphaBounds(_ bitmap: NSBitmapImageRep) -> CGRect {
    var minX = bitmap.pixelsWide
    var minY = bitmap.pixelsHigh
    var maxX = -1
    var maxY = -1

    for y in 0..<bitmap.pixelsHigh {
        for x in 0..<bitmap.pixelsWide {
            let alpha = bitmap.colorAt(x: x, y: y)?.alphaComponent ?? 0
            if alpha >= 0.125 {
                minX = min(minX, x)
                minY = min(minY, y)
                maxX = max(maxX, x)
                maxY = max(maxY, y)
            }
        }
    }

    if maxX < minX || maxY < minY {
        return CGRect(x: 0, y: 0, width: bitmap.pixelsWide, height: bitmap.pixelsHigh)
    }
    return CGRect(x: minX, y: minY, width: maxX - minX + 1, height: maxY - minY + 1)
}

guard let sourceImage = NSImage(contentsOfFile: source),
      let tiff = sourceImage.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff) else {
    fatalError("Could not load source image: \(source)")
}

let crop = alphaBounds(bitmap)
let logoSize: CGFloat = 108
let scale = min(logoSize / crop.width, logoSize / crop.height)
let logoWidth = crop.width * scale
let logoHeight = crop.height * scale
let logoX = CGFloat(4) + (CGFloat(108) - logoWidth) / 2
let logoY = (canvasSize.height - logoHeight) / 2

image.lockFocus()
NSColor.white.setFill()
NSRect(origin: .zero, size: canvasSize).fill()

sourceImage.draw(
    in: NSRect(x: logoX, y: logoY, width: logoWidth, height: logoHeight),
    from: crop,
    operation: .sourceOver,
    fraction: 1
)

let title = "那須野崎" as NSString
let subtitle = "プロクラ" as NSString
let titleFont = NSFont(name: "HiraginoSans-W6", size: 29)
    ?? NSFont(name: "Hiragino Kaku Gothic ProN", size: 29)
    ?? NSFont.systemFont(ofSize: 29, weight: .semibold)
let subtitleFont = NSFont(name: "HiraginoSans-W6", size: 28)
    ?? NSFont(name: "Hiragino Kaku Gothic ProN", size: 28)
    ?? NSFont.systemFont(ofSize: 28, weight: .semibold)
let titleAttributes: [NSAttributedString.Key: Any] = [
    .font: titleFont,
    .foregroundColor: NSColor.black
]
let subtitleAttributes: [NSAttributedString.Key: Any] = [
    .font: subtitleFont,
    .foregroundColor: NSColor.black
]
let textAreaLeft: CGFloat = 112
let textAreaRight: CGFloat = 248
let titleSize = title.size(withAttributes: titleAttributes)
let subtitleSize = subtitle.size(withAttributes: subtitleAttributes)
let titleX = textAreaLeft + (textAreaRight - textAreaLeft - titleSize.width) / 2
let subtitleX = textAreaLeft + (textAreaRight - textAreaLeft - subtitleSize.width) / 2
title.draw(at: NSPoint(x: titleX, y: 68), withAttributes: titleAttributes)
subtitle.draw(at: NSPoint(x: subtitleX, y: 22), withAttributes: subtitleAttributes)

image.unlockFocus()

guard let resultTiff = image.tiffRepresentation,
      let resultBitmap = NSBitmapImageRep(data: resultTiff),
      let png = resultBitmap.representation(using: .png, properties: [:]) else {
    fatalError("Could not encode PNG")
}

try png.write(to: URL(fileURLWithPath: output))
print(output)
