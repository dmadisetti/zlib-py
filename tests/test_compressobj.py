"""CompressObjectTestCase tests vendored from CPython's Lib/test/test_zlib.py.

Source: https://github.com/python/cpython/blob/5775aa8e295102156de14fd1ba284722c6ede95a/Lib/test/test_zlib.py
Commit: 5775aa8e295102156de14fd1ba284722c6ede95a (3.16-alpha)

Methods that round-trip through `decompressobj` or call `.copy()` are
vendored as-is and marked `@unittest.expectedFailure` until those pieces
land — they'll become unexpected-passes (pytest will flag them) the
moment the supporting code arrives, which is the signal to drop the
decorator. Methods that exercise only `compressobj`/`Compress` should
pass on landing.
"""

import copy
import pickle
import random
import unittest

import zlib as cpython_zlib
import zlib_py as zlib  # so vendored bodies run against our module unmodified


# Lines 17-77 vendored verbatim from Lib/test/test_zlib.py @ 5775aa8e.
HAMLET_SCENE = b"""
LAERTES

       O, fear me not.
       I stay too long: but here my father comes.

       Enter POLONIUS

       A double blessing is a double grace,
       Occasion smiles upon a second leave.

LORD POLONIUS

       Yet here, Laertes! aboard, aboard, for shame!
       The wind sits in the shoulder of your sail,
       And you are stay'd for. There; my blessing with thee!
       And these few precepts in thy memory
       See thou character. Give thy thoughts no tongue,
       Nor any unproportioned thought his act.
       Be thou familiar, but by no means vulgar.
       Those friends thou hast, and their adoption tried,
       Grapple them to thy soul with hoops of steel;
       But do not dull thy palm with entertainment
       Of each new-hatch'd, unfledged comrade. Beware
       Of entrance to a quarrel, but being in,
       Bear't that the opposed may beware of thee.
       Give every man thy ear, but few thy voice;
       Take each man's censure, but reserve thy judgment.
       Costly thy habit as thy purse can buy,
       But not express'd in fancy; rich, not gaudy;
       For the apparel oft proclaims the man,
       And they in France of the best rank and station
       Are of a most select and generous chief in that.
       Neither a borrower nor a lender be;
       For loan oft loses both itself and friend,
       And borrowing dulls the edge of husbandry.
       This above all: to thine ownself be true,
       And it must follow, as the night the day,
       Thou canst not then be false to any man.
       Farewell: my blessing season this in thee!

LAERTES

       Most humbly do I take my leave, my lord.

LORD POLONIUS

       The time invites you; go; your servants tend.

LAERTES

       Farewell, Ophelia; and remember well
       What I have said to you.

OPHELIA

       'Tis in my memory lock'd,
       And you yourself shall keep the key of it.

LAERTES

       Farewell.
"""

# Stubs for module-level names CPython's test_zlib.py defines and the
# vendored tests reference. None of these gates change semantics — they
# just make the verbatim test bodies importable.
HW_ACCELERATED = False  # zlib-rs is deterministic; CPython's HW guard is moot.
ZLIB_RUNTIME_VERSION_TUPLE = tuple(
    int(p) for p in zlib.ZLIB_RUNTIME_VERSION.split(".")[:4] if p.isdigit()
)
# CPython's test module defines these decorators based on whether the C
# extension exposes Compress.copy / Decompress.copy. We always lack them
# today (deviation #11 in THIRD_PARTY.md), so every decorated test is
# expected to fail.
requires_Compress_copy = unittest.expectedFailure
requires_Decompress_copy = unittest.expectedFailure


class CompressObjectTestCase(unittest.TestCase):
    # Lines 514-535 of Lib/test/test_zlib.py @ 5775aa8e
    def test_pair(self):
        # straightforward compress/decompress objects
        datasrc = HAMLET_SCENE * 128
        datazip = zlib.compress(datasrc)
        # should compress both bytes and bytearray data
        for data in (datasrc, bytearray(datasrc)):
            co = zlib.compressobj()
            x1 = co.compress(data)
            x2 = co.flush()
            self.assertRaises(zlib.error, co.flush) # second flush should not work
            # With hardware acceleration, the compressed bytes might not
            # be identical.
            if not HW_ACCELERATED:
                self.assertEqual(x1 + x2, datazip)
        for v1, v2 in ((x1, x2), (bytearray(x1), bytearray(x2))):
            dco = zlib.decompressobj()
            y1 = dco.decompress(v1 + v2)
            y2 = dco.flush()
            self.assertEqual(data, y1 + y2)
            self.assertIsInstance(dco.unconsumed_tail, bytes)
            self.assertIsInstance(dco.unused_data, bytes)

    # Lines 537-558 of Lib/test/test_zlib.py @ 5775aa8e
    @requires_Compress_copy
    def test_compresscopy(self):
        # Test copying a compression object
        data0 = HAMLET_SCENE
        data1 = bytes(str(HAMLET_SCENE, "ascii").swapcase(), "ascii")
        for func in lambda c: c.copy(), copy.copy, copy.deepcopy:
            c0 = zlib.compressobj(zlib.Z_BEST_COMPRESSION)
            bufs0 = []
            bufs0.append(c0.compress(data0))

            c1 = func(c0)
            bufs1 = bufs0[:]

            bufs0.append(c0.compress(data0))
            bufs0.append(c0.flush())
            s0 = b''.join(bufs0)

            bufs1.append(c1.compress(data1))
            bufs1.append(c1.flush())
            s1 = b''.join(bufs1)

            self.assertEqual(zlib.decompress(s0),data0+data0)
            self.assertEqual(zlib.decompress(s1),data0+data1)

    # Lines 560-568 of Lib/test/test_zlib.py @ 5775aa8e
    @requires_Compress_copy
    def test_badcompresscopy(self):
        # Test copying a compression object in an inconsistent state
        c = zlib.compressobj()
        c.compress(HAMLET_SCENE)
        c.flush()
        self.assertRaises(ValueError, c.copy)
        self.assertRaises(ValueError, copy.copy, c)
        self.assertRaises(ValueError, copy.deepcopy, c)

    # Lines 579-583 of Lib/test/test_zlib.py @ 5775aa8e
    def test_compresspickle(self):
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.assertRaises((TypeError, pickle.PicklingError)):
                pickle.dumps(zlib.compressobj(zlib.Z_BEST_COMPRESSION), proto)

    # Lines 600-623 of Lib/test/test_zlib.py @ 5775aa8e
    # (uses one-shot zlib.decompress for round-trip — works today)
    def test_flushes(self):
        # Test flush() with the various options, using all the
        # different levels in order to provide more variations.
        sync_opt = ['Z_NO_FLUSH', 'Z_SYNC_FLUSH', 'Z_FULL_FLUSH',
                    'Z_PARTIAL_FLUSH']

        # Z_BLOCK has a known failure prior to 1.2.5.3
        if ZLIB_RUNTIME_VERSION_TUPLE >= (1, 2, 5, 3):
            sync_opt.append('Z_BLOCK')

        sync_opt = [getattr(zlib, opt) for opt in sync_opt
                    if hasattr(zlib, opt)]
        data = HAMLET_SCENE * 8

        for sync in sync_opt:
            for level in range(10):
                with self.subTest(sync=sync, level=level):
                    obj = zlib.compressobj( level )
                    a = obj.compress( data[:3000] )
                    b = obj.flush( sync )
                    c = obj.compress( data[3000:] )
                    d = obj.flush()
                    self.assertEqual(zlib.decompress(b''.join([a,b,c,d])),
                                     data, ("Decompress failed: flush "
                                            "mode=%i, level=%i") % (sync, level))
                    del obj

    # Lines 625-647 of Lib/test/test_zlib.py @ 5775aa8e
    @unittest.skipUnless(hasattr(zlib, 'Z_SYNC_FLUSH'),
                         'requires zlib.Z_SYNC_FLUSH')
    def test_odd_flush(self):
        # Test for odd flushing bugs noted in 2.0, and hopefully fixed in 2.1
        import random
        # Testing on 17K of "random" data

        # Create compressor and decompressor objects
        co = zlib.compressobj(zlib.Z_BEST_COMPRESSION)
        dco = zlib.decompressobj()

        # Try 17K of data
        # generate random data stream
        data = random.randbytes(17 * 1024)

        # compress, sync-flush, and decompress
        first = co.compress(data)
        second = co.flush(zlib.Z_SYNC_FLUSH)
        expanded = dco.decompress(first + second)

        # if decompressed data is different from the input data, choke.
        self.assertEqual(expanded, data, "17K random source doesn't match")

    # Lines 649-657 of Lib/test/test_zlib.py @ 5775aa8e
    def test_empty_flush(self):
        # Test that calling .flush() on unused objects works.
        # (Bug #1083110 -- calling .flush() on decompress objects
        # caused a core dump.)

        co = zlib.compressobj(zlib.Z_BEST_COMPRESSION)
        self.assertTrue(co.flush())  # Returns a zlib header
        dco = zlib.decompressobj()
        self.assertEqual(dco.flush(), b"") # Returns nothing

    # Lines 659-672 of Lib/test/test_zlib.py @ 5775aa8e
    def test_dictionary(self):
        h = HAMLET_SCENE
        # Build a simulated dictionary out of the words in HAMLET.
        words = h.split()
        random.shuffle(words)
        zdict = b''.join(words)
        # Use it to compress HAMLET.
        co = zlib.compressobj(zdict=zdict)
        cd = co.compress(h) + co.flush()
        # Verify that it will decompress with the dictionary.
        dco = zlib.decompressobj(zdict=zdict)
        self.assertEqual(dco.decompress(cd) + dco.flush(), h)
        # Verify that it fails when not given the dictionary.
        dco = zlib.decompressobj()
        self.assertRaises(zlib.error, dco.decompress, cd)

    # Lines 413-432 of Lib/test/test_zlib.py @ 5775aa8e
    def test_keywords(self):
        level = 2
        method = zlib.DEFLATED
        wbits = -12
        memLevel = 9
        strategy = zlib.Z_FILTERED
        co = zlib.compressobj(level=level,
                              method=method,
                              wbits=wbits,
                              memLevel=memLevel,
                              strategy=strategy,
                              zdict=b"")
        do = zlib.decompressobj(wbits=wbits, zdict=b"")
        with self.assertRaises(TypeError):
            co.compress(data=HAMLET_SCENE)
        with self.assertRaises(TypeError):
            do.decompress(data=zlib.compress(HAMLET_SCENE))
        x = co.compress(HAMLET_SCENE) + co.flush()
        y = do.decompress(x, max_length=len(HAMLET_SCENE)) + do.flush()
        self.assertEqual(HAMLET_SCENE, y)

    # Lines 434-447 of Lib/test/test_zlib.py @ 5775aa8e
    def test_compressoptions(self):
        # specify lots of options to compressobj()
        level = 2
        method = zlib.DEFLATED
        wbits = -12
        memLevel = 9
        strategy = zlib.Z_FILTERED
        co = zlib.compressobj(level, method, wbits, memLevel, strategy)
        x1 = co.compress(HAMLET_SCENE)
        x2 = co.flush()
        dco = zlib.decompressobj(wbits)
        y1 = dco.decompress(x1 + x2)
        y2 = dco.flush()
        self.assertEqual(HAMLET_SCENE, y1 + y2)

    # Lines 449-462 of Lib/test/test_zlib.py @ 5775aa8e
    def test_compressincremental(self):
        # compress object in steps, decompress object as one-shot
        data = HAMLET_SCENE * 128
        co = zlib.compressobj()
        bufs = []
        for i in range(0, len(data), 256):
            bufs.append(co.compress(data[i:i+256]))
        bufs.append(co.flush())
        combuf = b''.join(bufs)

        dco = zlib.decompressobj()
        y1 = dco.decompress(b''.join(bufs))
        y2 = dco.flush()
        self.assertEqual(data, y1 + y2)

    # Lines 464-503 of Lib/test/test_zlib.py @ 5775aa8e
    def test_decompinc(self, flush=False, source=None, cx=256, dcx=64):
        # compress object in steps, decompress object in steps
        source = source or HAMLET_SCENE
        data = source * 128
        co = zlib.compressobj()
        bufs = []
        for i in range(0, len(data), cx):
            bufs.append(co.compress(data[i:i+cx]))
        bufs.append(co.flush())
        combuf = b''.join(bufs)

        decombuf = zlib.decompress(combuf)
        # Test type of return value
        self.assertIsInstance(decombuf, bytes)

        self.assertEqual(data, decombuf)

        dco = zlib.decompressobj()
        bufs = []
        for i in range(0, len(combuf), dcx):
            bufs.append(dco.decompress(combuf[i:i+dcx]))
            self.assertEqual(b'', dco.unconsumed_tail, ########
                             "(A) uct should be b'': not %d long" %
                                       len(dco.unconsumed_tail))
            self.assertEqual(b'', dco.unused_data)
        if flush:
            bufs.append(dco.flush())
        else:
            while True:
                chunk = dco.decompress(b'')
                if chunk:
                    bufs.append(chunk)
                else:
                    break
        self.assertEqual(b'', dco.unconsumed_tail, ########
                         "(B) uct should be b'': not %d long" %
                                       len(dco.unconsumed_tail))
        self.assertEqual(b'', dco.unused_data)
        self.assertEqual(data, b''.join(bufs))
        # Failure means: "decompressobj with init options failed"

    # Lines 505-506 of Lib/test/test_zlib.py @ 5775aa8e
    def test_decompincflush(self):
        self.test_decompinc(flush=True)

    # Lines 508-533 of Lib/test/test_zlib.py @ 5775aa8e
    def test_decompimax(self, source=None, cx=256, dcx=64):
        # compress in steps, decompress in length-restricted steps
        source = source or HAMLET_SCENE
        # Check a decompression object with max_length specified
        data = source * 128
        co = zlib.compressobj()
        bufs = []
        for i in range(0, len(data), cx):
            bufs.append(co.compress(data[i:i+cx]))
        bufs.append(co.flush())
        combuf = b''.join(bufs)
        self.assertEqual(data, zlib.decompress(combuf),
                         'compressed data failure')

        dco = zlib.decompressobj()
        bufs = []
        cb = combuf
        while cb:
            #max_length = 1 + len(cb)//10
            chunk = dco.decompress(cb, dcx)
            self.assertFalse(len(chunk) > dcx,
                    'chunk too big (%d>%d)' % (len(chunk), dcx))
            bufs.append(chunk)
            cb = dco.unconsumed_tail
        bufs.append(dco.flush())
        self.assertEqual(data, b''.join(bufs), 'Wrong data retrieved')

    # Lines 919-973 of Lib/test/test_zlib.py @ 5775aa8e
    # xfail: streaming gzip / auto-detect wbits (16+15, 32+15, 32+9) are
    # rejected by our compressobj/decompressobj since zlib-rs 0.6.3 stable
    # API can't reach those wrap modes. The `decompressobj(wbits=14)`
    # error-message assertion ('invalid window size') also won't match
    # our wording. Both flip when zlib-rs exposes Deflate/Inflate
    # with_config or we wire up libz-rs-sys (see THIRD_PARTY.md
    # deviations #5 and #11).
    @unittest.expectedFailure
    def test_wbits(self):
        # wbits=0 only supported since zlib v1.2.3.5
        supports_wbits_0 = ZLIB_RUNTIME_VERSION_TUPLE >= (1, 2, 3, 5)

        co = zlib.compressobj(level=1, wbits=15)
        zlib15 = co.compress(HAMLET_SCENE) + co.flush()
        self.assertEqual(zlib.decompress(zlib15, 15), HAMLET_SCENE)
        if supports_wbits_0:
            self.assertEqual(zlib.decompress(zlib15, 0), HAMLET_SCENE)
        self.assertEqual(zlib.decompress(zlib15, 32 + 15), HAMLET_SCENE)
        with self.assertRaisesRegex(zlib.error, 'invalid window size'):
            zlib.decompress(zlib15, 14)
        dco = zlib.decompressobj(wbits=32 + 15)
        self.assertEqual(dco.decompress(zlib15), HAMLET_SCENE)
        dco = zlib.decompressobj(wbits=14)
        with self.assertRaisesRegex(zlib.error, 'invalid window size'):
            dco.decompress(zlib15)

        co = zlib.compressobj(level=1, wbits=9)
        zlib9 = co.compress(HAMLET_SCENE) + co.flush()
        self.assertEqual(zlib.decompress(zlib9, 9), HAMLET_SCENE)
        self.assertEqual(zlib.decompress(zlib9, 15), HAMLET_SCENE)
        if supports_wbits_0:
            self.assertEqual(zlib.decompress(zlib9, 0), HAMLET_SCENE)
        self.assertEqual(zlib.decompress(zlib9, 32 + 9), HAMLET_SCENE)
        dco = zlib.decompressobj(wbits=32 + 9)
        self.assertEqual(dco.decompress(zlib9), HAMLET_SCENE)

        co = zlib.compressobj(level=1, wbits=-15)
        deflate15 = co.compress(HAMLET_SCENE) + co.flush()
        self.assertEqual(zlib.decompress(deflate15, -15), HAMLET_SCENE)
        dco = zlib.decompressobj(wbits=-15)
        self.assertEqual(dco.decompress(deflate15), HAMLET_SCENE)

        co = zlib.compressobj(level=1, wbits=-9)
        deflate9 = co.compress(HAMLET_SCENE) + co.flush()
        self.assertEqual(zlib.decompress(deflate9, -9), HAMLET_SCENE)
        self.assertEqual(zlib.decompress(deflate9, -15), HAMLET_SCENE)
        dco = zlib.decompressobj(wbits=-9)
        self.assertEqual(dco.decompress(deflate9), HAMLET_SCENE)

        co = zlib.compressobj(level=1, wbits=16 + 15)
        gzip = co.compress(HAMLET_SCENE) + co.flush()
        self.assertEqual(zlib.decompress(gzip, 16 + 15), HAMLET_SCENE)
        self.assertEqual(zlib.decompress(gzip, 32 + 15), HAMLET_SCENE)
        dco = zlib.decompressobj(32 + 15)
        self.assertEqual(dco.decompress(gzip), HAMLET_SCENE)

        for wbits in (-15, 15, 31):
            with self.subTest(wbits=wbits):
                expected = HAMLET_SCENE
                actual = zlib.decompress(
                    zlib.compress(HAMLET_SCENE, wbits=wbits), wbits=wbits
                )
                self.assertEqual(expected, actual)

    # Lines 674-686 of Lib/test/test_zlib.py @ 5775aa8e
    def test_dictionary_streaming(self):
        # This simulates the reuse of a compressor object for compressing
        # several separate data streams.
        co = zlib.compressobj(zdict=HAMLET_SCENE)
        do = zlib.decompressobj(zdict=HAMLET_SCENE)
        piece = HAMLET_SCENE[1000:1500]
        d0 = co.compress(piece) + co.flush(zlib.Z_SYNC_FLUSH)
        d1 = co.compress(piece[100:]) + co.flush(zlib.Z_SYNC_FLUSH)
        d2 = co.compress(piece[:-100]) + co.flush(zlib.Z_SYNC_FLUSH)
        self.assertEqual(do.decompress(d0), piece)
        self.assertEqual(do.decompress(d1), piece[100:])
        self.assertEqual(do.decompress(d2), piece[:-100])


if __name__ == "__main__":
    unittest.main()
