from pathlib import Path
from typing import Union

import numpy as np

from impreproc.djimrk import mrkread
from impreproc.images import Image, ImageList


def get_dji_id_from_name(fname: str) -> str:
    return fname.stem.split("_")[-1]


def latlonalt_from_exif(exif: dict) -> tuple:
    """
    latlonalt_from_exif _summary_

    Args:
        exif (dict): _description_

    Returns:
        tuple: _description_
    """
    assert (
        exif["GPS GPSLatitudeRef"].values[0] == "N"
    ), "Latitude Reference is not North. Unable to process image."
    assert (
        exif["GPS GPSLongitudeRef"].values[0] == "E"
    ), "Longitude Reference is not East. Unable to process image."
    assert (
        exif["GPS GPSAltitudeRef"].values[0] == 0
    ), "Altitude Reference is not WGS84. Unable to process image."

    lat = (
        np.float32(exif["GPS GPSLatitude"].values[0])
        + np.float32(exif["GPS GPSLatitude"].values[1]) / 60
        + np.float32(exif["GPS GPSLatitude"].values[2]) / 3600
    )
    lon = (
        np.float32(exif["GPS GPSLongitude"].values[0])
        + np.float32(exif["GPS GPSLongitude"].values[1]) / 60
        + np.float32(exif["GPS GPSLongitude"].values[2]) / 3600
    )
    alt = np.float32(exif["GPS GPSAltitude"].values[0])

    return (lat, lon, alt)

def get_images(folder: Union[str, Path], image_ext: str) -> dict:
    """
    get_images _summary_

    Args:
        folder (str): _description_
        image_ext (_type_): _description_

    Returns:
        dict: _description_
    """

    # Get list of files
    files = ImageList(folder, image_ext=image_ext, recursive=False)

    # Initialize dictionary
    n = len(files)
    exifdata = {
        "Name": [None] * n,
        "Path": [None] * n,
        "Id": [None] * n,
        "Date": [None] * n,
        "Time": [None] * n,
        "Lat": [None] * n,
        "Lon": [None] * n,
        "Ellh": [None] * n,
    }

    # Populate dictionary from exif data
    for i, file in enumerate(files):
        img = Image(file)
        exifdata["Name"][i] = file.stem
        exifdata["Path"][i] = str(file)
        exifdata["Id"][i] = get_dji_id_from_name(file)
        exifdata["Date"][i] = img.date
        exifdata["Time"][i] = img.time
        lat, lon, h = latlonalt_from_exif(img.exif)
        exifdata["Lat"][i] = lat
        exifdata["Lon"][i] = lon
        exifdata["Ellh"][i] = h

    return exifdata

if __name__ == "__main__":
    data_dir = "data/matrice/DJI_202303031031_001"
    mkr_file = "data/matrice/DJI_202303031031_001/DJI_202303031031_001_Timestamp.MRK"
    image_ext = "jpg"
    recursive = False

    mrk = mrkread(mkr_file)
    exifdata = get_images(data_dir, image_ext)

    print("Process completed.")
