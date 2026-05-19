#![allow(non_camel_case_types, non_snake_case, unused_variables)]

//! zlib-rs bindings for Python.
//!
//! Stub phase: every name CPython's `zlib` exposes is present, but the
//! callable bodies all raise `NotImplementedError`. Filled in
//! function-by-function in subsequent commits — see CONVERSION.md.

use pyo3::buffer::PyBuffer;
use pyo3::create_exception;
use pyo3::exceptions::{PyBufferError, PyException, PyNotImplementedError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

/// Validate wbits for one-shot compress / streaming compressobj.
/// Accepts -15..=-8 (raw), 8..=15 (zlib), 25..=31 (gzip).
fn validate_compress_wbits(wbits: i32) -> PyResult<()> {
    if (-15..=-8).contains(&wbits) || (8..=15).contains(&wbits) || (25..=31).contains(&wbits) {
        Ok(())
    } else {
        Err(error::new_err("Invalid initialization option"))
    }
}

/// Get a contiguous `&[u8]` view of a buffer-protocol object.
/// Caller must keep the PyBuffer alive for the slice's lifetime.
fn buffer_as_slice<'a>(buf: &'a PyBuffer<u8>) -> PyResult<&'a [u8]> {
    if !buf.is_c_contiguous() {
        return Err(PyBufferError::new_err("buffer must be C-contiguous"));
    }
    Ok(unsafe { std::slice::from_raw_parts(buf.buf_ptr() as *const u8, buf.item_count()) })
}

create_exception!(zlib_py, error, PyException);

fn stub<T>() -> PyResult<T> {
    Err(PyNotImplementedError::new_err(
        "zlib_py: not yet implemented",
    ))
}

// ---- module-level functions -------------------------------------------------

#[pyfunction]
#[pyo3(signature = (data, value=1, /))]
fn adler32(data: &Bound<'_, PyAny>, value: u32) -> PyResult<u32> {
    let buf = PyBuffer::<u8>::get(data)?;
    if !buf.is_c_contiguous() {
        return Err(PyBufferError::new_err(
            "buffer must be C-contiguous",
        ));
    }
    // PyBuffer keeps the underlying storage pinned for its lifetime, so this
    // slice is safe to read from. We don't release the GIL: adler32 is a
    // tight SIMD loop and the overhead of releasing+re-acquiring dwarfs the
    // compute for any input small enough to be common.
    let slice = unsafe {
        std::slice::from_raw_parts(buf.buf_ptr() as *const u8, buf.item_count())
    };
    Ok(zlib_rs::adler32::adler32(value, slice))
}

#[pyfunction]
#[pyo3(signature = (data, value=0, /))]
fn crc32(data: &Bound<'_, PyAny>, value: u32) -> PyResult<u32> {
    let buf = PyBuffer::<u8>::get(data)?;
    if !buf.is_c_contiguous() {
        return Err(PyBufferError::new_err(
            "buffer must be C-contiguous",
        ));
    }
    let slice = unsafe {
        std::slice::from_raw_parts(buf.buf_ptr() as *const u8, buf.item_count())
    };
    Ok(zlib_rs::crc32::crc32(value, slice))
}

#[pyfunction]
#[pyo3(signature = (adler1, adler2, len2, /))]
fn adler32_combine(adler1: u32, adler2: u32, len2: i64) -> PyResult<u32> {
    stub()
}

#[pyfunction]
#[pyo3(signature = (crc1, crc2, len2, /))]
fn crc32_combine(crc1: u32, crc2: u32, len2: i64) -> PyResult<u32> {
    stub()
}

#[pyfunction]
#[pyo3(signature = (data, /, level=-1, wbits=15))]
fn compress(
    py: Python<'_>,
    data: &Bound<'_, PyAny>,
    level: i32,
    wbits: i32,
) -> PyResult<Py<PyBytes>> {
    if level != -1 && !(0..=9).contains(&level) {
        return Err(PyValueError::new_err("Bad compression level"));
    }
    validate_compress_wbits(wbits)?;

    let buf = PyBuffer::<u8>::get(data)?;
    let input = buffer_as_slice(&buf)?;

    let mut config = zlib_rs::DeflateConfig::new(level);
    config.window_bits = wbits;

    let bound = zlib_rs::compress_bound(input.len());
    let mut output = vec![0u8; bound];
    let (compressed, rc) = zlib_rs::compress_slice(&mut output, input, config);
    match rc {
        zlib_rs::ReturnCode::Ok | zlib_rs::ReturnCode::StreamEnd => {
            let n = compressed.len();
            Ok(PyBytes::new(py, &output[..n]).unbind())
        }
        _ => Err(error::new_err(format!(
            "Error {:?} while compressing data",
            rc
        ))),
    }
}

#[pyfunction]
#[pyo3(signature = (data, /, wbits=15, bufsize=16384))]
fn decompress(data: &Bound<'_, PyAny>, wbits: i32, bufsize: usize) -> PyResult<Py<PyBytes>> {
    stub()
}

#[pyfunction]
#[pyo3(signature = (level=-1, method=8, wbits=15, memLevel=8, strategy=0, zdict=None))]
fn compressobj(
    level: i32,
    method: i32,
    wbits: i32,
    memLevel: i32,
    strategy: i32,
    zdict: Option<&Bound<'_, PyAny>>,
) -> PyResult<Compress> {
    stub()
}

#[pyfunction]
#[pyo3(signature = (wbits=15, zdict=None))]
fn decompressobj(wbits: i32, zdict: Option<&Bound<'_, PyAny>>) -> PyResult<Decompress> {
    stub()
}

// ---- streaming objects ------------------------------------------------------

// Stdlib `zlib` doesn't expose `Compress`/`Decompress` as module attrs — you
// only get them via `type(compressobj())`. We expose them under underscore
// names so they're available for testing while staying out of the public
// surface. Renames to plain `Compress`/`Decompress` once `compressobj` is
// implemented and tests can reach them via `type(compressobj())`.

#[pyclass(name = "_Compress")]
pub struct Compress;

#[pymethods]
impl Compress {
    #[new]
    fn new() -> Self {
        Self
    }

    fn compress(&self, data: &Bound<'_, PyAny>) -> PyResult<Py<PyBytes>> {
        stub()
    }

    #[pyo3(signature = (mode=4, /))]
    fn flush(&self, mode: i32) -> PyResult<Py<PyBytes>> {
        stub()
    }

    fn copy(&self) -> PyResult<Compress> {
        stub()
    }
}

#[pyclass(name = "_Decompress")]
pub struct Decompress;

#[pymethods]
impl Decompress {
    #[new]
    fn new() -> Self {
        Self
    }

    #[pyo3(signature = (data, max_length=0, /))]
    fn decompress(&self, data: &Bound<'_, PyAny>, max_length: usize) -> PyResult<Py<PyBytes>> {
        stub()
    }

    #[pyo3(signature = (length=16384, /))]
    fn flush(&self, length: usize) -> PyResult<Py<PyBytes>> {
        stub()
    }

    fn copy(&self) -> PyResult<Decompress> {
        stub()
    }

    #[getter]
    fn unused_data(&self) -> PyResult<Py<PyBytes>> {
        stub()
    }

    #[getter]
    fn unconsumed_tail(&self) -> PyResult<Py<PyBytes>> {
        stub()
    }

    #[getter]
    fn eof(&self) -> PyResult<bool> {
        stub()
    }

    #[getter]
    fn needs_input(&self) -> PyResult<bool> {
        stub()
    }
}

// ---- module registration ----------------------------------------------------

#[pymodule]
fn zlib_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();

    m.add("error", py.get_type::<error>())?;

    // Compression levels.
    m.add("Z_NO_COMPRESSION", 0i32)?;
    m.add("Z_BEST_SPEED", 1i32)?;
    m.add("Z_BEST_COMPRESSION", 9i32)?;
    m.add("Z_DEFAULT_COMPRESSION", -1i32)?;

    // Strategies.
    m.add("Z_FILTERED", 1i32)?;
    m.add("Z_HUFFMAN_ONLY", 2i32)?;
    m.add("Z_RLE", 3i32)?;
    m.add("Z_FIXED", 4i32)?;
    m.add("Z_DEFAULT_STRATEGY", 0i32)?;

    // Flush modes.
    m.add("Z_NO_FLUSH", 0i32)?;
    m.add("Z_PARTIAL_FLUSH", 1i32)?;
    m.add("Z_SYNC_FLUSH", 2i32)?;
    m.add("Z_FULL_FLUSH", 3i32)?;
    m.add("Z_FINISH", 4i32)?;
    m.add("Z_BLOCK", 5i32)?;
    m.add("Z_TREES", 6i32)?;

    // Misc.
    m.add("MAX_WBITS", 15i32)?;
    m.add("DEFLATED", 8i32)?;
    m.add("DEF_BUF_SIZE", 16384i32)?;
    m.add("DEF_MEM_LEVEL", 8i32)?;

    // Version strings (placeholders — we don't link libz).
    m.add("ZLIB_VERSION", "1.3.1.zlib-rs-0.6.3")?;
    m.add("ZLIB_RUNTIME_VERSION", "1.3.1.zlib-rs-0.6.3")?;

    m.add_class::<Compress>()?;
    m.add_class::<Decompress>()?;

    m.add_function(wrap_pyfunction!(adler32, m)?)?;
    m.add_function(wrap_pyfunction!(crc32, m)?)?;
    m.add_function(wrap_pyfunction!(adler32_combine, m)?)?;
    m.add_function(wrap_pyfunction!(crc32_combine, m)?)?;
    m.add_function(wrap_pyfunction!(compress, m)?)?;
    m.add_function(wrap_pyfunction!(decompress, m)?)?;
    m.add_function(wrap_pyfunction!(compressobj, m)?)?;
    m.add_function(wrap_pyfunction!(decompressobj, m)?)?;

    Ok(())
}
