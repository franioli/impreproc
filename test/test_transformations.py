import pytest
from affine import Affine
from typing import Tuple
import numpy as np

from impreproc.transformations import xy2rc, rc2xy, project_to_utm, bilinear_interpolate


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


def test_project_to_utm():
    data_dict = {
        1: {"id": 1, "lat": 45.477059, "lon": 9.186755, "ellh": 100.0},
    }

    epsg_from = 4326  # WGS84
    epsg_to = 32632  # UTM zone 32N

    # Test for successful conversion
    assert project_to_utm(epsg_from, epsg_to, data_dict)
    assert np.isclose(data_dict[1]["N"], 5035964.792, rtol=1e-3)
    assert np.isclose(data_dict[1]["E"], 514596.494, rtol=1e-3)
    assert np.isclose(data_dict[1]["ellh"], 100.0, rtol=1e-5)

    # # Test inverse transformation
    # lat_, lon_, ellh_ = transformer.transform(x, y, z, direction="INVERSE")
    # np.isclose(lat, lat_, atol=1e-8)
    # np.isclose(lon, lon_, atol=1e-8)
    # np.isclose(ellh, ellh_, atol=1e-8)

    # Test for invalid EPSG codes
    epsg_from = 4326
    epsg_to = 4326
    try:
        project_to_utm(epsg_from, epsg_to, data_dict)
    except AssertionError as e:
        assert str(e) == "EPSG codes must be different"

    # Test for invalid fields
    epsg_from = 4326
    epsg_to = 32632
    fields = ["lat", "lon"]
    try:
        project_to_utm(epsg_from, epsg_to, data_dict, fields)
    except AssertionError as e:
        assert str(e) == "Three fields must be specified"

    # Test for non-string fields
    epsg_from = 4326
    epsg_to = 32632
    fields = ["lat", "lon", 123]
    try:
        project_to_utm(epsg_from, epsg_to, data_dict, fields)
    except AssertionError as e:
        assert str(e) == "Fields must be strings"


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
