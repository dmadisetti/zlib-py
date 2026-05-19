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
