import struct
import sys
import unittest
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import xcursor as xc  # noqa: E402


def make_png(px, rgba_rows, filter_type=0):
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    raw = b''.join(bytes([filter_type]) + bytes(r) for r in rgba_rows)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', px, px, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


class PngTest(unittest.TestCase):
    def test_premultiplied_bgra(self):
        png = make_png(1, [[255, 128, 0, 128]])
        self.assertEqual(xc.png_to_argb(png, 1), bytes((0, 64, 128, 128)))

    def test_sub_filter(self):
        # filter 1 (Sub): second pixel is stored as a delta from the first
        png = make_png(2, [[10, 20, 30, 255, 1, 1, 1, 0], [0] * 8], filter_type=1)
        out = xc.png_to_argb(png, 2)
        self.assertEqual(out[:8], bytes((30, 20, 10, 255, 31, 21, 11, 255)))

    def test_rejects_wrong_size_and_non_png(self):
        with self.assertRaises(ValueError):
            xc.png_to_argb(make_png(1, [[0, 0, 0, 0]]), 2)
        with self.assertRaises(ValueError):
            xc.png_to_argb(b'nope', 1)


class XcursorTest(unittest.TestCase):
    def test_layout(self):
        data = xc.xcursor([(24, 1, 3, 4, 0, b'\x00\x00\x00\xff')])
        self.assertEqual(data[:4], b'Xcur')
        header, version, n = struct.unpack('<III', data[4:16])
        self.assertEqual((header, version, n), (16, 0x10000, 1))
        typ, size, offset = struct.unpack('<III', data[16:28])
        self.assertEqual((typ, size, offset), (0xfffd0002, 24, 28))
        chunk = struct.unpack('<9I', data[offset:offset + 36])
        self.assertEqual(chunk, (36, 0xfffd0002, 24, 1, 1, 1, 3, 4, 0))
        self.assertEqual(data[offset + 36:], b'\x00\x00\x00\xff')


class SvgTest(unittest.TestCase):
    def test_vector_to_svg(self):
        a = xc.A
        xml = (f'<vector xmlns:android="http://schemas.android.com/apk/res/android" '
               f'android:viewportWidth="24" android:viewportHeight="24">'
               f'<path android:pathData="M0,0" android:fillColor="?attr/pointerIconVectorFill"/>'
               f'<group><path android:pathData="M1,1" android:fillColor="#80FF0000" android:fillType="evenOdd"/></group>'
               f'</vector>')
        vec = ET.fromstring(xml)
        svg = xc.vector_to_svg(vec, {'Fill': '#000'})
        self.assertIn('viewBox="0 0 24 24"', svg)
        self.assertIn('fill="#000" fill-opacity="1" fill-rule="nonzero"', svg)
        self.assertIn('<g><path d="M1,1" fill="#FF0000"', svg)
        self.assertIn('fill-rule="evenodd"', svg)
        self.assertAlmostEqual(float(svg.split('fill-opacity="')[2].split('"')[0]), 128 / 255)


if __name__ == '__main__':
    unittest.main()
