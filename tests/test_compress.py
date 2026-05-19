"""Compress tests vendored from CPython's Lib/test/test_zlib.py.

Source: https://github.com/python/cpython/blob/5775aa8e295102156de14fd1ba284722c6ede95a/Lib/test/test_zlib.py
Commit: 5775aa8e295102156de14fd1ba284722c6ede95a (3.16-alpha)
"""

import unittest

import zlib as cpython_zlib
import zlib_py


# Vendored verbatim from Lib/test/test_zlib.py:17-77 @ 5775aa8e
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


class CompressTestCase(unittest.TestCase):
    # Lines 580-583 of Lib/test/test_zlib.py @ 5775aa8e
    def test_speech(self):
        x = zlib_py.compress(HAMLET_SCENE)
        self.assertEqual(zlib_py.decompress(x), HAMLET_SCENE)

    # Lines 585-595 of Lib/test/test_zlib.py @ 5775aa8e
    def test_keywords(self):
        x = zlib_py.compress(HAMLET_SCENE, level=3)
        self.assertEqual(zlib_py.decompress(x), HAMLET_SCENE)
        with self.assertRaises(TypeError):
            zlib_py.compress(data=HAMLET_SCENE, level=3)
        self.assertEqual(zlib_py.decompress(x,
                                                 wbits=zlib_py.MAX_WBITS,
                                                 bufsize=zlib_py.DEF_BUF_SIZE),
                         HAMLET_SCENE)

    # Lines 597-606 of Lib/test/test_zlib.py @ 5775aa8e
    # (the HW_ACCELERATED guard is dropped — zlib-rs is deterministic.)
    def test_speech128(self):
        # compress more data
        data = HAMLET_SCENE * 128
        x = zlib_py.compress(data)
        self.assertEqual(zlib_py.compress(bytearray(data)), x)
        for ob in x, bytearray(x):
            self.assertEqual(zlib_py.decompress(ob), data)

class ByteParityWithStdlib(unittest.TestCase):
    """Byte-for-byte equality with the C zlib implementation.

    Not part of CPython's vendored test suite — these probe how close
    zlib-rs's deflate decisions track the C zlib reference. Round-trip
    correctness is asserted in `CompressTestCase`; this class is purely
    informational: where it fails, the two implementations diverge in
    their compressed representation (still valid deflate streams, just
    a different encoding).

    These failures are an engine-level property of zlib-rs, not a bug
    in our wrapper. zlib-rs documents itself as "compatible with the
    zlib API" (format and API parity, no byte-for-byte claim), and the
    v0.6.3 release notes explicitly state "this fix can change the
    output of compression slightly" — output isn't pinned even across
    patch versions of the engine itself. See:
        https://github.com/trifectatechfoundation/zlib-rs/releases/tag/v0.6.3

    Levels 0 (store-only) and 9 (saturated for highly compressible
    inputs) hit deterministic code paths and do match; intermediate
    levels diverge.
    """

    # Level 0 (store-only) — deterministic: deflate emits raw blocks
    # with no compression, so output must match stdlib byte-for-byte.
    def test_level_0_byte_equal(self):
        self.assertEqual(zlib_py.compress(HAMLET_SCENE, 0),
                         cpython_zlib.compress(HAMLET_SCENE, 0))

    # Level 9 on HAMLET_SCENE — both implementations saturate to the
    # same optimal encoding for this input, so output matches.
    def test_level_9_byte_equal_on_hamlet(self):
        self.assertEqual(zlib_py.compress(HAMLET_SCENE, 9),
                         cpython_zlib.compress(HAMLET_SCENE, 9))

    @unittest.expectedFailure
    def test_default_level(self):
        self.assertEqual(zlib_py.compress(HAMLET_SCENE),
                         cpython_zlib.compress(HAMLET_SCENE))

    @unittest.expectedFailure
    def test_intermediate_levels(self):
        # Levels 1-8 diverge from stdlib — zlib-rs's deflate makes
        # different micro-decisions than C zlib at intermediate
        # settings. Marked expectedFailure to record the gap; if
        # zlib-rs ever closes it, this test will start passing.
        for level in range(1, 9):
            with self.subTest(level=level):
                self.assertEqual(
                    zlib_py.compress(HAMLET_SCENE, level),
                    cpython_zlib.compress(HAMLET_SCENE, level),
                )


if __name__ == "__main__":
    unittest.main()
