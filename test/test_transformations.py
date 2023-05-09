import pytest
from affine import Affine
from typing import Tuple
import numpy as np

from impreproc.transformations import xy2rc, rc2xy, bilinear_interpolate


@pytest.fixture
def tform():
    return Affine(
        0.033333333333333326,
        0.0,
        4.983333333333333,
        0.0,
        -0.033333333333333326,
        48.016666666666666,
    )


def test_xy2rc(tform):
    x, y = 9.190653, 45.463873
    expected = (76.58381000000008, 126.21959000000001)
    assert all(np.isclose(xy2rc(tform, x, y), expected, rtol=1e-9)), "xy2rc failed"


def test_rc2xy(tform):
    row, col = 76, 126
    expected = (9.183333333333334, 45.483333333333334)
    assert all(
        np.isclose(rc2xy(tform, row, col), expected, rtol=1e-9)
    ), "  rc2xy failed"


# def test_bilinear_interpolate():
#     # Create a simple test image
#     im = np.array([[0, 1, 2], [3, 4, 5], [6, 7, 8]], dtype=np.float32)

#     # Test a single point
#     x = np.array([1.5])
#     y = np.array([1.5])
#     result = bilinear_interpolate(im, x, y)
#     expected = np.array([4.0])
#     assert np.allclose(result, expected)

#     # Test multiple points
#     x = np.array([0.5, 1.5, 2.5])
#     y = np.array([0.5, 1.5, 2.5])
#     result = bilinear_interpolate(im, x, y)
#     expected = np.array([1.0, 4.0, 7.0])
#     assert np.allclose(result, expected)
