# Third-party attributions

## farhaanaliii/zlib-rs-python

The pyo3 bindings in `src/lib.rs` are adapted from
[farhaanaliii/zlib-rs-python](https://github.com/farhaanaliii/zlib-rs-python),
an earlier pyo3 port of the [`zlib-rs`](https://crates.io/crates/zlib-rs)
crate. We use the algorithmic core (zlib-rs API call patterns, buffer
sizing, streaming loop shapes) as a starting point and rewrite the
Python-facing surface to match CPython's spec at the rev we target
(`5775aa8e295102156de14fd1ba284722c6ede95a`, 3.16-alpha).

The reference port deviates from the stdlib `zlib` spec in several
places. The corrections we apply when porting are:

| # | Area | Reference behavior | Our behavior (matches CPython spec) |
|---|------|---|---|
| 1 | Buffer type | `&[u8]` (bytes-only) | `PyBuffer<u8>` — accepts any object supporting the buffer protocol |
| 2 | `compress` signature | `(data, level=-1)` | `(data, level=Z_DEFAULT_COMPRESSION, wbits=MAX_WBITS, /)` |
| 3 | Positional-only args | Keyword-allowed | All public functions positional-only |
| 4 | `compressobj` kwarg | `mem_level` | `memLevel` (matches CPython's AC clinic name) |
| 5 | `compressobj` memLevel/strategy | Silently ignored | Currently ignored with a TODO; `libz-rs-sys` follow-up for full coverage |
| 6 | `wbits` validation | Silently clamps invalid values | Errors for out-of-range wbits |
| 7 | `decompress` buffer growth | Starts at `bufsize.max(data.len()*4)`, hard 256 MB cap | Spec: starts at `bufsize`, doubles on `BufError`, no fixed cap |
| 8 | `Compress.flush(Z_NO_FLUSH)` | Loops calling `compress` | Returns empty bytes immediately (spec no-op) |
| 9 | `Decompress.flush(length<=0)` | Coerces with `length.max(4096)` | Raises `ValueError` |
| 10 | `decompressobj` `zdict` default | `None` | `b''` (matches CPython introspection) |
| 11 | `Compress.copy` / `__copy__` / `__deepcopy__` | Not implemented | Implemented (separate slice, may require `libz-rs-sys`) |
| 12 | `needs_input` on Decompress | Not exposed | Exposed (CPython HEAD exposes unconditionally) |
| 13 | Non-spec attrs | Adds `total_in`, `total_out`, `__repr__` on Compress/Decompress | Omitted — not in stdlib |
| 14 | `Z_DEFLATED` constant | Defined | Omitted — stdlib has `DEFLATED` only |
| 15 | `error` exception | Imported from stdlib `zlib` | Defined in our module |
| 16 | `ZLIB_VERSION` | Hardcoded `"1.2.11"` | `"1.3.1.zlib-rs-0.6.3"` (honest about the underlying engine) |
| 17 | gzip streaming | n/a (reference omits gzip support entirely) | `decompressobj()` and `_ZlibDecompressor` reject gzip wbits (24..=31) and auto-detect (40..=47) with an honest error; zlib-rs 0.6.3's stable `Inflate::new` only does zlib/raw. Use one-shot `decompress()` for gzip — it routes through `decompress_slice` which accepts the full `InflateConfig`. |

See `CONVERSION.md` for the full mapping from `zlibmodule.c` to
`zlib-rs`. License compatibility for the adaptation is recorded in the
project `LICENSE` file.

## zlib-rs

The underlying engine is [`zlib-rs`](https://crates.io/crates/zlib-rs)
(`0.6.3`), a pure-Rust reimplementation of zlib. Licensed under
Zlib/Apache-2.0/MIT (tri-license); see the crate for details.
