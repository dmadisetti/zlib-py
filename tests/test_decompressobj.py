"""DecompressObjectTestCase tests vendored from CPython's Lib/test/test_zlib.py.

Source: https://github.com/python/cpython/blob/5775aa8e295102156de14fd1ba284722c6ede95a/Lib/test/test_zlib.py
Commit: 5775aa8e295102156de14fd1ba284722c6ede95a (3.16-alpha)

CPython groups decompressobj-specific tests inside `CompressObjectTestCase`
alongside the compressobj ones; we split them by feature for readability,
so this file holds the methods that exercise only `decompressobj` /
`Decompress`. Methods that touch `.copy()` are marked
`@requires_Decompress_copy` (= `expectedFailure`) until that feature
lands — drop the decorator the moment libz-rs-sys is wired up.
"""

import copy
import pickle
import unittest

import zlib_py as zlib  # so vendored bodies run against our module unmodified

from tests.test_compressobj import HAMLET_SCENE  # vendored block, reused


# CPython's test module defines this decorator based on whether the C
# extension exposes Decompress.copy. We lack it today (deviation #11 in
# THIRD_PARTY.md), so every decorated test is expected to fail.
requires_Decompress_copy = unittest.expectedFailure


class DecompressObjectTestCase(unittest.TestCase):
    # Lines 535-559 of Lib/test/test_zlib.py @ 5775aa8e
    def test_decompressmaxlen(self, flush=False):
        # Check a decompression object with max_length specified
        data = HAMLET_SCENE * 128
        co = zlib.compressobj()
        bufs = []
        for i in range(0, len(data), 256):
            bufs.append(co.compress(data[i:i+256]))
        bufs.append(co.flush())
        combuf = b''.join(bufs)
        self.assertEqual(data, zlib.decompress(combuf),
                         'compressed data failure')

        dco = zlib.decompressobj()
        bufs = []
        cb = combuf
        while cb:
            max_length = 1 + len(cb)//10
            chunk = dco.decompress(cb, max_length)
            self.assertFalse(len(chunk) > max_length,
                        'chunk too big (%d>%d)' % (len(chunk),max_length))
            bufs.append(chunk)
            cb = dco.unconsumed_tail
        if flush:
            bufs.append(dco.flush())
        else:
            while chunk:
                chunk = dco.decompress(b'', max_length)
                self.assertFalse(len(chunk) > max_length,
                            'chunk too big (%d>%d)' % (len(chunk),max_length))
                bufs.append(chunk)
        self.assertEqual(data, b''.join(bufs), 'Wrong data retrieved')

    # Lines 561-562 of Lib/test/test_zlib.py @ 5775aa8e
    def test_decompressmaxlenflush(self):
        self.test_decompressmaxlen(flush=True)

    # Lines 564-568 of Lib/test/test_zlib.py @ 5775aa8e
    def test_maxlenmisc(self):
        # Misc tests of max_length
        dco = zlib.decompressobj()
        self.assertRaises(ValueError, dco.decompress, b"", -1)
        self.assertEqual(b'', dco.unconsumed_tail)

    # Lines 585-592 of Lib/test/test_zlib.py @ 5775aa8e
    def test_clear_unconsumed_tail(self):
        # Issue #12050: calling decompress() without providing max_length
        # should clear the unconsumed_tail attribute.
        cdata = b"x\x9cKLJ\x06\x00\x02M\x01"    # "abc"
        dco = zlib.decompressobj()
        ddata = dco.decompress(cdata, 1)
        ddata += dco.decompress(dco.unconsumed_tail)
        self.assertEqual(dco.unconsumed_tail, b"")

    # Lines 689-701 of Lib/test/test_zlib.py @ 5775aa8e
    def test_decompress_incomplete_stream(self):
        # This is 'foo', deflated
        x = b'x\x9cK\xcb\xcf\x07\x00\x02\x82\x01E'
        # For the record
        self.assertEqual(zlib.decompress(x), b'foo')
        self.assertRaises(zlib.error, zlib.decompress, x[:-5])
        # Omitting the stream end works with decompressor objects
        # (see issue #8672).
        dco = zlib.decompressobj()
        y = dco.decompress(x[:-5])
        y += dco.flush()
        self.assertEqual(y, b'foo')

    # Lines 703-712 of Lib/test/test_zlib.py @ 5775aa8e
    def test_decompress_eof(self):
        x = b'x\x9cK\xcb\xcf\x07\x00\x02\x82\x01E'  # 'foo'
        dco = zlib.decompressobj()
        self.assertFalse(dco.eof)
        dco.decompress(x[:-5])
        self.assertFalse(dco.eof)
        dco.decompress(x[-5:])
        self.assertTrue(dco.eof)
        dco.flush()
        self.assertTrue(dco.eof)

    # Lines 714-720 of Lib/test/test_zlib.py @ 5775aa8e
    def test_decompress_eof_incomplete_stream(self):
        x = b'x\x9cK\xcb\xcf\x07\x00\x02\x82\x01E'  # 'foo'
        dco = zlib.decompressobj()
        self.assertFalse(dco.eof)
        dco.decompress(x[:-5])
        self.assertFalse(dco.eof)
        dco.flush()
        self.assertFalse(dco.eof)

    # Lines 722-748 of Lib/test/test_zlib.py @ 5775aa8e
    def test_decompress_unused_data(self):
        # Repeated calls to decompress() after EOF should accumulate data in
        # dco.unused_data, instead of just storing the arg to the last call.
        source = b'abcdefghijklmnopqrstuvwxyz'
        remainder = b'0123456789'
        y = zlib.compress(source)
        x = y + remainder
        for maxlen in 0, 1000:
            for step in 1, 2, len(y), len(x):
                dco = zlib.decompressobj()
                data = b''
                for i in range(0, len(x), step):
                    if i < len(y):
                        self.assertEqual(dco.unused_data, b'')
                    if maxlen == 0:
                        data += dco.decompress(x[i : i + step])
                        self.assertEqual(dco.unconsumed_tail, b'')
                    else:
                        data += dco.decompress(
                                dco.unconsumed_tail + x[i : i + step], maxlen)
                data += dco.flush()
                self.assertTrue(dco.eof)
                self.assertEqual(data, source)
                self.assertEqual(dco.unconsumed_tail, b'')
                self.assertEqual(dco.unused_data, remainder)

    # Lines 751-757 of Lib/test/test_zlib.py @ 5775aa8e
    # issue27164
    def test_decompress_raw_with_dictionary(self):
        zdict = b'abcdefghijklmnopqrstuvwxyz'
        co = zlib.compressobj(wbits=-zlib.MAX_WBITS, zdict=zdict)
        comp = co.compress(zdict) + co.flush()
        dco = zlib.decompressobj(wbits=-zlib.MAX_WBITS, zdict=zdict)
        uncomp = dco.decompress(comp) + dco.flush()
        self.assertEqual(zdict, uncomp)

    # Lines 759-769 of Lib/test/test_zlib.py @ 5775aa8e
    def test_flush_with_freed_input(self):
        # Issue #16411: decompressor accesses input to last decompress() call
        # in flush(), even if this object has been freed in the meanwhile.
        input1 = b'abcdefghijklmnopqrstuvwxyz'
        input2 = b'QWERTYUIOPASDFGHJKLZXCVBNM'
        data = zlib.compress(input1)
        dco = zlib.decompressobj()
        dco.decompress(data, 1)
        del data
        data = zlib.compress(input2)
        self.assertEqual(dco.flush(), input1[1:])

    # Lines 822-844 of Lib/test/test_zlib.py @ 5775aa8e
    @requires_Decompress_copy
    def test_decompresscopy(self):
        # Test copying a decompression object
        data = HAMLET_SCENE
        comp = zlib.compress(data)
        # Test type of return value
        self.assertIsInstance(comp, bytes)

        for func in lambda c: c.copy(), copy.copy, copy.deepcopy:
            d0 = zlib.decompressobj()
            bufs0 = []
            bufs0.append(d0.decompress(comp[:32]))

            d1 = func(d0)
            bufs1 = bufs0[:]

            bufs0.append(d0.decompress(comp[32:]))
            s0 = b''.join(bufs0)

            bufs1.append(d1.decompress(comp[32:]))
            s1 = b''.join(bufs1)

            self.assertEqual(s0,s1)
            self.assertEqual(s0,data)

    # Lines 846-854 of Lib/test/test_zlib.py @ 5775aa8e
    @requires_Decompress_copy
    def test_baddecompresscopy(self):
        # Test copying a compression object in an inconsistent state
        data = zlib.compress(HAMLET_SCENE)
        d = zlib.decompressobj()
        d.decompress(data)
        d.flush()
        self.assertRaises(ValueError, d.copy)
        self.assertRaises(ValueError, copy.copy, d)
        self.assertRaises(ValueError, copy.deepcopy, d)

    # Lines 861-864 of Lib/test/test_zlib.py @ 5775aa8e
    def test_decompresspickle(self):
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.assertRaises((TypeError, pickle.PicklingError)):
                pickle.dumps(zlib.decompressobj(), proto)


if __name__ == "__main__":
    unittest.main()
