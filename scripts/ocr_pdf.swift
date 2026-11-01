import Foundation
import Vision
import PDFKit
import AppKit

struct TextItem: Codable {
    let text: String
    let x: Double
    let y: Double
    let w: Double
    let h: Double
}

struct PageResult: Codable {
    let page: Int
    let width: Double
    let height: Double
    let items: [TextItem]
}

struct DocumentResult: Codable {
    let path: String
    let pageCount: Int
    let pages: [PageResult]
}

guard CommandLine.arguments.count > 1 else {
    print("Usage: ocr_pdf <path-to-pdf> [output-json-path]")
    exit(1)
}

let pdfPath = CommandLine.arguments[1]
let outputPath = CommandLine.arguments.count > 2 ? CommandLine.arguments[2] : nil

guard let doc = PDFDocument(url: URL(fileURLWithPath: pdfPath)) else {
    fputs("Error: Cannot open PDF at \(pdfPath)\n", stderr)
    exit(1)
}

var pageResults = [PageResult]()

for pageIndex in 0..<doc.pageCount {
    guard let page = doc.page(at: pageIndex) else { continue }
    let pageRect = page.bounds(for: .mediaBox)
    let scale: CGFloat = 2.0 // render at 2x for sharp text
    let targetSize = NSSize(width: pageRect.width * scale, height: pageRect.height * scale)
    
    let image = NSImage(size: targetSize)
    image.lockFocus()
    if let context = NSGraphicsContext.current?.cgContext {
        context.setFillColor(NSColor.white.cgColor)
        context.fill(CGRect(origin: .zero, size: targetSize))
        context.scaleBy(x: scale, y: scale)
        page.draw(with: .mediaBox, to: context)
    }
    image.unlockFocus()
    
    guard let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        continue
    }
    
    var items = [TextItem]()
    let request = VNRecognizeTextRequest { req, err in
        guard let observations = req.results as? [VNRecognizedTextObservation] else { return }
        for obs in observations {
            guard let candidate = obs.topCandidates(1).first else { continue }
            // obs.boundingBox: origin is bottom-left, y goes up [0,1]
            // Let's convert to top-left coordinate system: top y is 0, bottom y is 1
            let bbox = obs.boundingBox
            let item = TextItem(
                text: candidate.string,
                x: Double(bbox.origin.x),
                y: Double(1.0 - (bbox.origin.y + bbox.size.height)), // top-down y
                w: Double(bbox.size.width),
                h: Double(bbox.size.height)
            )
            items.append(item)
        }
    }
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    request.usesLanguageCorrection = true
    request.recognitionLevel = .accurate
    
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try? handler.perform([request])
    
    // Sort items top-to-bottom, then left-to-right
    items.sort { abs($0.y - $1.y) < 0.012 ? $0.x < $1.x : $0.y < $1.y }
    
    pageResults.append(PageResult(
        page: pageIndex + 1,
        width: Double(pageRect.width),
        height: Double(pageRect.height),
        items: items
    ))
}

let docResult = DocumentResult(path: pdfPath, pageCount: doc.pageCount, pages: pageResults)
let encoder = JSONEncoder()
encoder.outputFormatting = .prettyPrinted
if let data = try? encoder.encode(docResult) {
    if let out = outputPath {
        try? data.write(to: URL(fileURLWithPath: out))
        print("Wrote \(pageResults.count) pages to \(out)")
    } else {
        if let str = String(data: data, encoding: .utf8) {
            print(str)
        }
    }
}
