"""Pure helpers of the cursor builder (no network, no files): VectorDrawable -> SVG, PNG decoding, Xcursor encoding."""
import struct
import subprocess
import zlib
import xml.etree.ElementTree as ET

A = '{http://schemas.android.com/apk/res/android}'
XCURSOR_IMAGE = 0xfffd0002


def vector_to_svg(vec, colors):
    """Android VectorDrawable (path / group, fillColor, fillType) -> SVG text.
    `colors` maps the ?attr/pointerIconVector<Name> theme attributes to colours."""
    def color(c):
        if c.startswith('?attr/pointerIconVector'):
            c = colors[c[len('?attr/pointerIconVector'):]]
        if len(c) == 9:
            return f'#{c[3:]}', int(c[1:3], 16) / 255        # #AARRGGBB
        return c, 1

    def body(el):
        s = ''
        for e in el:
            if e.tag == 'group':
                s += f'<g>{body(e)}</g>'
            elif e.tag == 'path':
                c, opacity = color(e.get(A + 'fillColor', '#000'))
                rule = 'evenodd' if e.get(A + 'fillType') == 'evenOdd' else 'nonzero'
                s += f'<path d="{e.get(A + "pathData")}" fill="{c}" fill-opacity="{opacity}" fill-rule="{rule}"/>'
        return s
    vw, vh = vec.get(A + 'viewportWidth'), vec.get(A + 'viewportHeight')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}">{body(vec)}</svg>'


def png_to_argb(png, px):
    """8-bit RGBA non-interlaced PNG (rsvg-convert output) of px x px -> premultiplied ARGB bytes, little-endian
    (B, G, R, A per pixel), as Xcursor wants them."""
    if png[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG')
    pos, idat = 8, b''
    while pos < len(png):
        n, typ = struct.unpack('>I4s', png[pos:pos + 8])
        if typ == b'IHDR':
            width, height, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', png[pos + 8:pos + 8 + 13])
            if (width, height, depth, ctype, interlace) != (px, px, 8, 6, 0):
                raise ValueError(f'unexpected PNG format: {(width, height, depth, ctype, interlace)}')
        if typ == b'IDAT':
            idat += png[pos + 8:pos + 8 + n]
        pos += 12 + n
    raw, stride = zlib.decompress(idat), px * 4
    prev, out = bytearray(stride), bytearray()
    for y in range(px):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        if f > 4:
            raise ValueError(f'bad PNG filter {f}')
        for i in range(stride):
            a = line[i - 4] if i >= 4 else 0
            b = prev[i]
            c = prev[i - 4] if i >= 4 else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = line
        for x in range(px):
            r, g, bl, al = line[x * 4:x * 4 + 4]
            out += bytes((bl * al // 255, g * al // 255, r * al // 255, al))
    return bytes(out)


def render(svg_text, px):
    """SVG -> Xcursor image bytes at px x px."""
    png = subprocess.run(['rsvg-convert', '-w', str(px), '-h', str(px)], input=svg_text.encode(),
                         capture_output=True, check=True).stdout
    return png_to_argb(png, px)


def xcursor(images):
    """images: [(nominal size, px, hotspot x, hotspot y, delay ms, ARGB bytes)] -> Xcursor file bytes."""
    n = len(images)
    pos = 16 + 12 * n
    headers, body = b'', b''
    for size, px, hx, hy, delay, data in images:
        headers += struct.pack('<III', XCURSOR_IMAGE, size, pos + len(body))
        body += struct.pack('<9I', 36, XCURSOR_IMAGE, size, 1, px, px, hx, hy, delay) + data
    return b'Xcur' + struct.pack('<III', 16, 0x10000, n) + headers + body


def parse_xml(path):
    return ET.parse(path).getroot()
