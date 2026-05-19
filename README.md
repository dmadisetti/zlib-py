# zlib-py

<p align="center">
  <a href="https://github.com/Rust-for-CPython">
    <img src="https://rust-for-cpython.com/r4p.svg" alt="Rust for CPython" width="160" />
  </a>
</p>

A small pyo3 extension that exposes [`zlib-rs`](https://crates.io/crates/zlib-rs) to Python.
As a small proof of concept for the [Rust for CPython](https://github.com/Rust-for-CPython) effort.

## Building

### With Nix

```sh
nix build              # Python env with zlib_py importable, at ./result
nix run .#python -- -c 'import zlib_py; print(zlib_py.compress(...))'
nix develop            # cargo + rustc + maturin + the pinned python on PATH
```

The flake fetches CPython and pyo3 at the pinned revs (we'll attempt to keep
this close to HEAD in both cases), then builds the extension with
`maturinBuildHook`. The cargo registry is vendored in a fixed-output derivation
so the actual build runs offline.

### Without Nix

```sh
uv sync
uv run maturin develop
uv run python -c 'import zlib_py; print(zlib_py.compress(...))'
```

This uses whatever CPython + pyo3 your environment resolves (no guarantees of working).


## Benchmarks

The benchmark script (vendored from `farhaanaliii/zlib-rs-python`) compares
`zlib_py` against the stdlib `zlib` on the same interpreter. Run with:

```sh
./result-test/bin/python benchmarks/bench_zlib.py
```

Sample numbers from Darwin arm64 / CPython 3.16.0a0 (median of N iterations
per upstream's schedule; sub-millisecond rows are noisy):

| Operation | Size | CPython `zlib` | `zlib_py` | Speedup |
|---|---|---:|---:|---:|
| decompress | 1 MB (L6) | 464 µs | 91 µs | **5.1× faster** |
| decompress | 10 MB (L6) | 5.24 ms | 868 µs | **6.0× faster** |
| stream compress | 1 MB (L6) | 1.52 ms | 292 µs | **5.2× faster** |
| stream compress | 10 MB (L6) | 15.42 ms | 2.77 ms | **5.6× faster** |
| stream decompress | 1 MB (L6) | 469 µs | 127 µs | **3.7× faster** |
| compress | 10 MB (L9) | 14.82 ms | 8.12 ms | **1.8× faster** |
| adler32 | 1 MB | 273 µs | 28 µs | **9.7× faster** |
| adler32 | 10 MB | 2.77 ms | 281 µs | **9.9× faster** |
| crc32 | 1 MB | 34 µs | 99 µs | 2.9× slower |
| crc32 | 10 MB | 343 µs | 1.00 ms | 2.9× slower |
| compress binary | 1 MB (L6) | 14.63 ms | 12.03 ms | 1.2× faster |

`crc32` regresses on payloads ≥64 KB because CPython's implementation uses
Intel CRC32 intrinsics that `zlib-rs` 0.6.3 doesn't hit on aarch64-darwin.

Output bytes match stdlib exactly at level 9 and diverge at intermediate
levels — engine-level property of `zlib-rs`, documented in `THIRD_PARTY.md`.

## Rust for CPython — links

- [Official GitHub org](https://github.com/Rust-for-CPython)
- [Pre-PEP discussion thread](https://discuss.python.org/t/pre-pep-rust-for-cpython/104906)
- [Latest progress update (2026-04)](https://blog.python.org/2026/04/rust-for-cpython-2026-04/)

## Acknowledgements

Prior art and inspiration:
[`farhaanaliii/zlib-rs-python`](https://github.com/farhaanaliii/zlib-rs-python)
a separate pyo3 binding to `zlib-rs`.

## License

[MIT](./LICENSE)
