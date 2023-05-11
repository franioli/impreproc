from typing import Any

import numpy as np
import pytest

from impreproc.djimrk import (
    get_dji_id_from_name,
    get_images,
    latlonalt_from_exif,
    merge_mrk_exif_data,
    mrkread,
)
from impreproc.transformations import project_to_utm
from impreproc.images import Image, ImageList


class ExifTag:
    def __init__(self, values) -> None:
        self._values = values

    @property
    def values(self) -> str:
        return self._values

    @values.setter
    def values(self, values) -> None:
        self._values = values

    @values.deleter
    def values(self) -> None:
        del self._values

    @property
    def printable(self) -> str:
        return str(self._values)

    def __repr__(self) -> str:
        return str(self._values)


@pytest.fixture
def sample_exif():
    # Example EXIF data
    exif = {
        "GPS GPSLatitudeRef": ExifTag(["N"]),
        "GPS GPSLatitude": ExifTag(["37", "49", "30.312"]),
        "GPS GPSLongitudeRef": ExifTag(["E"]),
        "GPS GPSLongitude": ExifTag(["122", "28", "5.937"]),
        "GPS GPSAltitudeRef": ExifTag([0]),
        "GPS GPSAltitude": ExifTag(["17.4"]),
    }

    return exif


def test_get_dji_id_from_name():
    assert get_dji_id_from_name("DJI_0001.JPG") == 1
    assert get_dji_id_from_name("DJI_0123.JPG") == 123
    assert get_dji_id_from_name("IMG_0123.JPG") == 123
    assert get_dji_id_from_name("dji_0001.JPG") == 1


def test_latlonalt_from_exif(sample_exif):
    lat, lon, alt = latlonalt_from_exif(sample_exif)
    assert lat == pytest.approx(37.825087, rel=1e-6)
    assert lon == pytest.approx(122.468316, rel=1e-6)
    assert alt == pytest.approx(17.4, rel=1e-6)

    with pytest.raises(AssertionError):
        # Test with invalid latitude reference
        sample_exif["GPS GPSLatitudeRef"].values = ["S"]
        latlonalt_from_exif(sample_exif)

    with pytest.raises(AssertionError):
        # Test with invalid longitude reference
        sample_exif["GPS GPSLatitudeRef"].values = ["N"]
        sample_exif["GPS GPSLongitudeRef"].values = ["W"]
        latlonalt_from_exif(sample_exif)

    with pytest.raises(AssertionError):
        # Test with invalid altitude reference
        sample_exif["GPS GPSLatitudeRef"].values = ["N"]
        sample_exif["GPS GPSLongitudeRef"].values = ["W"]
        sample_exif["GPS GPSAltitudeRef"].values = [1]
        latlonalt_from_exif(sample_exif)


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


if __name__ == "__main__":
    pass
    # data_dir = "data/matrice/DJI_202303031031_001"
    # image_ext = "JPG"
    # files = ImageList(data_dir, image_ext=image_ext, recursive=False)
    # img = Image(files[0])
    # exif = img.exif

    # test_project_to_utm()
