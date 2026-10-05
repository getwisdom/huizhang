"""imaging：32 位 PNG 往返读写（alpha 保持）与高质量缩放。"""

import numpy as np

from koutu.core.imaging import load_rgba, resize_rgba, save_rgba


def _sample() -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.integers(0, 256, size=(40, 60, 4), dtype=np.uint8)


def test_rgba_roundtrip_keeps_alpha(tmp_path):
    arr = _sample()
    p = tmp_path / "x.png"
    save_rgba(p, arr)
    got = load_rgba(p)
    assert got.shape == arr.shape
    assert np.array_equal(got, arr)


def test_resize_rgba_shape_and_dtype():
    arr = _sample()
    out = resize_rgba(arr, (120, 80))
    assert out.shape == (80, 120, 4)
    assert out.dtype == np.uint8
