// Cut the subject out of a photo with macOS Vision (macOS 14+) — the "lift subject" of Photos:
// local, free, no model to download. Writes a PNG with alpha, the reference fidelity_check needs.
//
//     swift tools/cutout.swift photo.jpg ref.png        # exit 0; 3 when no subject is found
//
// Measured (2026-10-12): a white ghost on a white wall, where a border fill on the corner colour
// leaked everywhere — 0.965 IoU against an outline traced by hand; a pumpkin on white, 0.921
// against the border fill; a cat filling the frame, clean. Look at the result before using it:
// it keeps everything it takes for the subject.
import Foundation
import Vision
import CoreImage
import ImageIO
import UniformTypeIdentifiers

let a = CommandLine.arguments
guard a.count == 3 else { FileHandle.standardError.write("usage: cutout in out.png\n".data(using: .utf8)!); exit(2) }
let url = URL(fileURLWithPath: a[1])
guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
      let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else { FileHandle.standardError.write("cannot read \(a[1])\n".data(using: .utf8)!); exit(1) }
let req = VNGenerateForegroundInstanceMaskRequest()
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do { try handler.perform([req]) } catch { FileHandle.standardError.write("vision: \(error)\n".data(using: .utf8)!); exit(1) }
guard let obs = req.results?.first, !obs.allInstances.isEmpty else { FileHandle.standardError.write("no subject found\n".data(using: .utf8)!); exit(3) }
let buf = try obs.generateMaskedImage(ofInstances: obs.allInstances, from: handler, croppedToInstancesExtent: false)
let ci = CIImage(cvPixelBuffer: buf)
let ctx = CIContext()
guard let outCG = ctx.createCGImage(ci, from: ci.extent),
      let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: a[2]) as CFURL, UTType.png.identifier as CFString, 1, nil) else { exit(1) }
CGImageDestinationAddImage(dest, outCG, nil)
guard CGImageDestinationFinalize(dest) else { exit(1) }
print("instances \(obs.allInstances.count) size \(outCG.width)x\(outCG.height)")
