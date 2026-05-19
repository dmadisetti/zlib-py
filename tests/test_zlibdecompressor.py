"""ZlibDecompressorTest vendored from CPython's Lib/test/test_zlib.py.

Source: https://github.com/python/cpython/blob/5775aa8e295102156de14fd1ba284722c6ede95a/Lib/test/test_zlib.py
Commit: 5775aa8e295102156de14fd1ba284722c6ede95a (3.16-alpha)

Two tests are skipped because they depend on CPython's `test.support`
harness (`bigmemtest`, `refcount_test`):

- `testDecompress4G` — needs the bigmem allocator decorator.
- `test_refleaks_in___init__` — needs `sys.gettotalrefcount` (debug build).

Otherwise the bodies are verbatim apart from rebinding `zlib` → `zlib_py`.
"""

import pickle
import unittest

import zlib_py as zlib  # so vendored bodies run against our module unmodified

from tests.test_compressobj import HAMLET_SCENE  # vendored block, reused


# Lines 1048-1208 of Lib/test/test_zlib.py @ 5775aa8e
class ZlibDecompressorTest(unittest.TestCase):
    # Test adopted from test_bz2.py
    TEXT = HAMLET_SCENE
    DATA = zlib.compress(HAMLET_SCENE)
    BAD_DATA = b"Not a valid deflate block"
    BIG_TEXT = DATA * ((128 * 1024 // len(DATA)) + 1)
    BIG_DATA = zlib.compress(BIG_TEXT)

    def test_Constructor(self):
        self.assertRaises(TypeError, zlib._ZlibDecompressor, "ASDA")
        self.assertRaises(TypeError, zlib._ZlibDecompressor, -15, "notbytes")
        self.assertRaises(TypeError, zlib._ZlibDecompressor, -15, b"bytes", 5)

    def testDecompress(self):
        zlibd = zlib._ZlibDecompressor()
        self.assertRaises(TypeError, zlibd.decompress)
        text = zlibd.decompress(self.DATA)
        self.assertEqual(text, self.TEXT)

    def testDecompressChunks10(self):
        zlibd = zlib._ZlibDecompressor()
        text = b''
        n = 0
        while True:
            str = self.DATA[n*10:(n+1)*10]
            if not str:
                break
            text += zlibd.decompress(str)
            n += 1
        self.assertEqual(text, self.TEXT)

    def testDecompressUnusedData(self):
        zlibd = zlib._ZlibDecompressor()
        unused_data = b"this is unused data"
        text = zlibd.decompress(self.DATA+unused_data)
        self.assertEqual(text, self.TEXT)
        self.assertEqual(zlibd.unused_data, unused_data)

    def testEOFError(self):
        zlibd = zlib._ZlibDecompressor()
        text = zlibd.decompress(self.DATA)
        self.assertRaises(EOFError, zlibd.decompress, b"anything")
        self.assertRaises(EOFError, zlibd.decompress, b"")

    @unittest.skip("requires CPython test.support.bigmemtest harness")
    def testDecompress4G(self, size=None):
        # "Test zlib._ZlibDecompressor.decompress() with >4GiB input"
        pass

    def testPickle(self):
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.assertRaises(TypeError):
                pickle.dumps(zlib._ZlibDecompressor(), proto)

    def testDecompressorChunksMaxsize(self):
        zlibd = zlib._ZlibDecompressor()
        max_length = 100
        out = []

        # Feed some input
        len_ = len(self.BIG_DATA) - 64
        out.append(zlibd.decompress(self.BIG_DATA[:len_],
                                  max_length=max_length))
        self.assertFalse(zlibd.needs_input)
        self.assertEqual(len(out[-1]), max_length)

        # Retrieve more data without providing more input
        out.append(zlibd.decompress(b'', max_length=max_length))
        self.assertFalse(zlibd.needs_input)
        self.assertEqual(len(out[-1]), max_length)

        # Retrieve more data while providing more input
        out.append(zlibd.decompress(self.BIG_DATA[len_:],
                                  max_length=max_length))
        self.assertLessEqual(len(out[-1]), max_length)

        # Retrieve remaining uncompressed data
        while not zlibd.eof:
            out.append(zlibd.decompress(b'', max_length=max_length))
            self.assertLessEqual(len(out[-1]), max_length)

        out = b"".join(out)
        self.assertEqual(out, self.BIG_TEXT)
        self.assertEqual(zlibd.unused_data, b"")

    def test_decompressor_inputbuf_1(self):
        # Test reusing input buffer after moving existing
        # contents to beginning
        zlibd = zlib._ZlibDecompressor()
        out = []

        # Create input buffer and fill it
        self.assertEqual(zlibd.decompress(self.DATA[:100],
                                        max_length=0), b'')

        # Retrieve some results, freeing capacity at beginning
        # of input buffer
        out.append(zlibd.decompress(b'', 2))

        # Add more data that fits into input buffer after
        # moving existing data to beginning
        out.append(zlibd.decompress(self.DATA[100:105], 15))

        # Decompress rest of data
        out.append(zlibd.decompress(self.DATA[105:]))
        self.assertEqual(b''.join(out), self.TEXT)

    def test_decompressor_inputbuf_2(self):
        # Test reusing input buffer by appending data at the
        # end right away
        zlibd = zlib._ZlibDecompressor()
        out = []

        # Create input buffer and empty it
        self.assertEqual(zlibd.decompress(self.DATA[:200],
                                        max_length=0), b'')
        out.append(zlibd.decompress(b''))

        # Fill buffer with new data
        out.append(zlibd.decompress(self.DATA[200:280], 2))

        # Append some more data, not enough to require resize
        out.append(zlibd.decompress(self.DATA[280:300], 2))

        # Decompress rest of data
        out.append(zlibd.decompress(self.DATA[300:]))
        self.assertEqual(b''.join(out), self.TEXT)

    def test_decompressor_inputbuf_3(self):
        # Test reusing input buffer after extending it

        zlibd = zlib._ZlibDecompressor()
        out = []

        # Create almost full input buffer
        out.append(zlibd.decompress(self.DATA[:200], 5))

        # Add even more data to it, requiring resize
        out.append(zlibd.decompress(self.DATA[200:300], 5))

        # Decompress rest of data
        out.append(zlibd.decompress(self.DATA[300:]))
        self.assertEqual(b''.join(out), self.TEXT)

    def test_failure(self):
        zlibd = zlib._ZlibDecompressor()
        self.assertRaises(Exception, zlibd.decompress, self.BAD_DATA * 30)
        # Previously, a second call could crash due to internal inconsistency
        self.assertRaises(Exception, zlibd.decompress, self.BAD_DATA * 30)

    @unittest.skip("requires sys.gettotalrefcount (CPython debug build)")
    def test_refleaks_in___init__(self):
        pass


if __name__ == "__main__":
    unittest.main()
