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


if __name__ == "__main__":
    pass
    # data_dir = "data/matrice/DJI_202303031031_001"
    # image_ext = "JPG"
    # files = ImageList(data_dir, image_ext=image_ext, recursive=False)
    # img = Image(files[0])
    # exif = img.exif

    # test_project_to_utm()
