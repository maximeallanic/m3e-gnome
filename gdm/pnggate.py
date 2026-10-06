"""PNG structure check of the m3e-gnome GDM helper. Standard library only; imported by ingest.py.

The image is never decoded or inflated here (so there is no decompression bomb to survive): the file is walked chunk by
chunk. Every chunk must fit in the file and carry a correct CRC; the first is IHDR with sane fields, at least one IDAT
exists, IEND is the last chunk and nothing follows it. The decoded size is bounded by the caller's dimension cap.
"""
import struct
import zlib

MAGIC = b"\x89PNG\r\n\x1a\n"
VALID_DEPTHS = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}


class PngRejected(Exception):
    pass


def check_png(data, max_w, max_h, name):
    def bad(msg):
        raise PngRejected(f"{name}: {msg}")

    if data[:8] != MAGIC:
        bad("not a PNG (bad magic)")
    pos, n, seen_idat, first = 8, len(data), False, True
    while pos < n:
        if pos + 12 > n:
            bad("truncated chunk header")
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        end = pos + 8 + length + 4
        if length > 0x7FFFFFFF or end > n:
            bad("chunk length runs past the end of the file")
        if not all(65 <= c <= 90 or 97 <= c <= 122 for c in ctype):
            bad("invalid chunk type")
        body = data[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", data[end - 4:end])
        if zlib.crc32(ctype + body) & 0xFFFFFFFF != crc:
            bad(f"{ctype.decode()} chunk checksum mismatch")
        if first:
            if ctype != b"IHDR" or length != 13:
                bad("first chunk is not a 13-byte IHDR")
            width, height, depth, color, comp, filt, interlace = struct.unpack(">IIBBBBB", body)
            if not (1 <= width <= max_w and 1 <= height <= max_h):
                bad(f"dimensions {width}x{height} outside 1..{max_w}x1..{max_h}")
            if depth not in VALID_DEPTHS.get(color, ()) or comp != 0 or filt != 0 or interlace not in (0, 1):
                bad("invalid IHDR fields")
            first = False
        elif ctype == b"IHDR":
            bad("repeated IHDR")
        elif ctype == b"IDAT":
            seen_idat = True
        elif ctype == b"IEND":
            if length != 0:
                bad("IEND with data")
            if not seen_idat:
                bad("no IDAT chunk")
            if end != n:
                bad("data after IEND")
            return
        pos = end
    bad("no IEND chunk")
