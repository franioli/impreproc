import re
from pathlib import Path
from typing import TypedDict, Union

import numpy as np

from impreproc.images import Image, ImageList


class ExifData(TypedDict):
    id: int
    name: str
    path: str
    date: str
    time: str
    lat: float
    lon: float
    ellh: float


class MrkData(TypedDict):
    id: int
    clock_time: float
    lat: float
    lon: float
    ellh: float
    stdE: float
    stdN: float
    stdV: float
    dE: float
    dN: float
    dV: float
    Qual: float
    Flag: float


def get_dji_id_from_name(fname: str) -> int:
    """Extracts the DJI image progressive ID from the given image filename.

    Args:
        fname (str): The image filename from which to extract the DJI image ID.

    Returns:
        int: The extracted DJI image ID.
    """
    return int(fname.stem.split("_")[-1])


def latlonalt_from_exif(exif: dict) -> tuple:
    """Extracts the latitude, longitude, and altitude from the given EXIF data.

    Args:
        exif (dict): The EXIF data from which to extract the latitude, longitude, and altitude.

    Returns:
        tuple: A tuple containing the latitude (float), longitude (float), and altitude (float).

    Raises:
        AssertionError: If the latitude or longitude reference is not North or East, respectively, or if the altitude reference is not WGS84.
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


def mrkread(fname: Union[Path, str]) -> dict:
    """Parse a .mrk file and return a dictionary with the data.

    Args:
        fname (Union[Path, str]): Path to the .mrk file.

    Returns:
        dict: Dictionary containing the data parsed from the .mrk file. The dictionary keys are the
        point IDs and the values are instances of the MrkData class.

    Raises:
        AssertionError: If the file does not exist or is not a .mrk file.

    """
    # check if the file exists and is a .mrk file
    fname = Path(fname)
    assert fname.exists(), f"File {fname} does not exist"
    assert fname.suffix.lower() == ".mrk", f"File {fname} is not a .mrk file"

    # open the file and parse each row using , as separator
    with open(fname, "r") as fid:
        indata = [re.split(",|\t|[|]|\n", i) for i in fid.readlines()]

    outdata = {}
    for line in indata:
        id = int("%03d" % np.float_(line[0]))
        data = MrkData(
            id=id,
            clock_time=np.float_(line[1]),
            lat=np.float_(line[9]),
            lon=np.float_(line[11]),
            ellh=np.float_(line[13]),
            stdE=np.float_(line[15]),
            stdN=np.float_(line[16]),
            stdV=np.float_(line[17]),
            dE=np.float_(line[3]),
            dN=np.float_(line[5]),
            dV=np.float_(line[7]),
            Qual=np.float_(line[18]),
            Flag=line[19],
        )
        outdata[id] = data

    return outdata


def get_images(folder: Union[str, Path], image_ext: str) -> dict:
    """Read image files and extract EXIF data from them.

    Args:
        folder (Union[str, Path]): Path to the folder containing the images.
        image_ext (str): Extension of the image files to read.

    Returns:
        dict: Dictionary containing the EXIF data extracted from the images. The dictionary keys are the
        point IDs and the values are instances of the ExifData class.

    """
    files = ImageList(folder, image_ext=image_ext, recursive=False)

    exifdata = {}
    for file in files:
        try:
            img = Image(file)
            id = get_dji_id_from_name(file)
            lat, lon, ellh = latlonalt_from_exif(img.exif)
            data = ExifData(
                id=id,
                name=file.stem,
                path=str(file),
                date=img.date,
                time=img.time,
                lat=lat,
                lon=lon,
                ellh=ellh,
            )
            exifdata[id] = data
        except Exception as e:
            print(f"Error reading file {file}: {e}")

    return exifdata


def merge_mrk_exif_data(mrk_dict: dict, exif_dict: dict) -> dict:
    merged_dict = {}
    for key in mrk_dict.keys():
        if key in exif_dict.keys():
            data = {
                "id": mrk_dict[key]["id"],
                "clock_time_mrk": mrk_dict[key]["clock_time"],
                "lat_mrk": mrk_dict[key]["lat"],
                "lon_mrk": mrk_dict[key]["lon"],
                "ellh_mrk": mrk_dict[key]["ellh"],
                "stdE_mrk": mrk_dict[key]["stdE"],
                "stdN_mrk": mrk_dict[key]["stdN"],
                "stdV_mrk": mrk_dict[key]["stdV"],
                "dE_mrk": mrk_dict[key]["dE"],
                "dN_mrk": mrk_dict[key]["dN"],
                "dV_mrk": mrk_dict[key]["dV"],
                "Qual_mrk": mrk_dict[key]["Qual"],
                "Flag_mrk": mrk_dict[key]["Flag"],
                "name_exif": exif_dict[key]["name"],
                "path_exif": exif_dict[key]["path"],
                "date_exif": exif_dict[key]["date"],
                "time_exif": exif_dict[key]["time"],
                "lat_exif": exif_dict[key]["lat"],
                "lon_exif": exif_dict[key]["lon"],
                "ellh_exif": exif_dict[key]["ellh"],
            }
            merged_dict[key] = data
        else:
            print(f"Image {key} not found in EXIF data.")

    return merged_dict


def project_to_utm(epsg_from: int, epsg_to: int, data_dict: dict):
    from pyproj import CRS
    from pyproj import Transformer

    assert epsg_from != epsg_to, "EPSG codes must be different"

    try:
        crs_from = CRS.from_epsg(epsg_from)
        crs_to = CRS.from_epsg(epsg_to)
        transformer = Transformer.from_crs(crs_from=crs_from, crs_to=crs_to)
    except Exception as e:
        print(
            f"Unable to convert coordinate from EPSG:{epsg_from} to EPSG:{epsg_to}: {e}"
        )

    for key in data_dict.keys():
        lat = data_dict[key]["lat"]
        lon = data_dict[key]["lon"]
        ellh = data_dict[key]["ellh"]
        x, y, z = transformer.transform(lat, lon, ellh)
        data_dict[key]["E"] = x
        data_dict[key]["N"] = y
        data_dict[key]["h"] = z

def project_to_utm(epsg_from: int, epsg_to: int, data_dict: dict):
    from pyproj import CRS
    from pyproj import Transformer

    assert epsg_from != epsg_to, "EPSG codes must be different"

    try:
        crs_from = CRS.from_epsg(epsg_from)
        crs_to = CRS.from_epsg(epsg_to)
        transformer = Transformer.from_crs(crs_from=crs_from, crs_to=crs_to)
    except Exception as e:
        print(
            f"Unable to convert coordinate from EPSG:{epsg_from} to EPSG:{epsg_to}: {e}"
        )

    for key in data_dict.keys():
        lat = data_dict[key]["lat"]
        lon = data_dict[key]["lon"]
        ellh = data_dict[key]["ellh"]
        x, y, z = transformer.transform(lat, lon, ellh)
        data_dict[key]["E"] = x
        data_dict[key]["N"] = y
        data_dict[key]["h"] = z


if __name__ == "__main__":
    data_dir = "data/matrice/DJI_202303031031_001"
    mkr_file = "data/matrice/DJI_202303031031_001/DJI_202303031031_001_Timestamp.MRK"
    image_ext = "jpg"

    mrk_dict = mrkread(mkr_file)
    exif_dict = get_images(data_dir, image_ext)
    merged_data = merge_mrk_exif_data(mrk_dict, exif_dict)

    project_to_utm(4326, 32632, exif_dict)

    # Projecting to UTM

    from pyproj import CRS
    from pyproj import Transformer

    crs_4326 = CRS.from_epsg(4326)
    crs_32632 = CRS.from_epsg(32632)

    transformer = Transformer.from_crs(crs_from=crs_4326, crs_to=crs_32632)

    id = 1
    lat, lon, ellh = exif_dict[id]["lat"], exif_dict[id]["lon"], exif_dict[id]["ellh"]
    transformer.transform(lat, lon)

    print("Process completed.")
