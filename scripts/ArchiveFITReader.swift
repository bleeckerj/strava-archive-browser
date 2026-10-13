import Foundation
import FITSwiftSDK

private final class ArchiveRecordListener: MesgListener {
    var points: [[Any]] = []
    private var segment = 0
    private let formatter = ISO8601DateFormatter()

    func onMesg(_ mesg: Mesg) throws {
        switch mesg.mesgNum {
        case MesgNum.record.rawValue:
            let record = RecordMesg(mesg: mesg)
            guard let lat = record.getPositionLat(), let lon = record.getPositionLong(),
                  lat != Int32.max, lon != Int32.max,
                  let coordinate = RouteCoordinate(latitude: Double(lat) * 180.0 / 2_147_483_648.0,
                                                   longitude: Double(lon) * 180.0 / 2_147_483_648.0) else {
                segment += 1
                return
            }
            var timestamp: Any = NSNull()
            if let value = record.getTimestamp(), value.timestamp != DateTime.invalid {
                timestamp = formatter.string(from: Date(timeIntervalSince1970: Double(value.timestamp) + Double(DateTime.unixEpochToFITEpoch)))
            }
            var altitude: Any = NSNull()
            if let value = record.getEnhancedAltitude() ?? record.getAltitude(), value.isFinite { altitude = Double(value) }
            points.append([coordinate.latitude, coordinate.longitude, timestamp, altitude, segment])
        case MesgNum.session.rawValue:
            segment += 1
        case MesgNum.event.rawValue:
            let event = EventMesg(mesg: mesg)
            if event.getEvent() == .timer, let type = event.getEventType(),
               [.stop, .stopAll, .stopDisable, .stopDisableAll].contains(type) { segment += 1 }
        default:
            break
        }
    }
}

@main
struct ArchiveFITReader {
    static func main() {
        do {
            guard CommandLine.arguments.count == 2 else { throw FITPreviewError.unreadable }
            let url = URL(fileURLWithPath: CommandLine.arguments[1])
            let summary = try FITRouteDecoder.decode(url: url)
            let normalized = try FITTimestampExpander.expand(Data(contentsOf: url))
            let decoder = Decoder(stream: FITSwiftSDK.InputStream(data: normalized))
            let listener = ArchiveRecordListener()
            decoder.addMesgListener(listener)
            try decoder.read()
            guard listener.points.count == summary.pointCount else { throw FITPreviewError.malformed }
            let data = try JSONSerialization.data(withJSONObject: ["points": listener.points, "source": "FIT Preview native decoder"])
            FileHandle.standardOutput.write(data)
        } catch {
            let data = try! JSONSerialization.data(withJSONObject: ["error": error.localizedDescription])
            FileHandle.standardOutput.write(data)
        }
    }
}
