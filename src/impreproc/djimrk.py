import re
from copy import deepcopy
from pathlib import Path
from typing import List, TypedDict, Union

import numpy as np
import pyproj

from impreproc.images import Image, ImageList, latlonalt_from_exif
from impreproc.transformations import Transformer


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
    fname = Path(fname)
    return int(fname.stem.split("_")[-1])


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
            exifdata[id] = None
            print(f"Error reading file {file}: {e}")

    return exifdata


def merge_mrk_exif_data(mrk_dict: dict, exif_dict: dict) -> dict:
    """Merge MRK and EXIF data dictionaries.

    This function takes two dictionaries, `mrk_dict` and `exif_dict`, and returns a new dictionary with
    merged data. The keys of both dictionaries must match, and the output dictionary will have the same
    keys as the input dictionaries.

    Args:
        mrk_dict (dict): A dictionary containing MRK data.
        exif_dict (dict): A dictionary containing EXIF data.

    Returns:
        dict: A dictionary containing merged MRK and EXIF data.

    Raises:
        None.
    """
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
            merged_dict[key] = None
            print(f"Image {key} not found in EXIF data.")

    return merged_dict


def project_to_utm(
    epsg_from: int,
    epsg_to: int,
    data_dict: dict,
    fields: List[str] = ["lat", "lon"],
    in_place: bool = False,
) -> Union[dict, None]:
    """
    Converts geographic coordinates (latitude, longitude) to projected UTM coordinates using the pyproj library.

    Args:
        epsg_from (int): EPSG code of the initial coordinate reference system (pyproj.CRS).
        epsg_to (int): EPSG code of the destination pyproj.CRS.
        data_dict (dict): Dictionary containing the data to be projected.
        fields (List[str], optional): List of two fields specifying the names of the latitude and longitude fields in the data dictionary, respectively. Default is ["lat", "lon"].
        in_place (bool, optional): If True, the projection is applied in-place to the data_dict. If False, a new dictionary with the projected coordinates is returned. Default is False.

    Returns:
        dict or None: A new dictionary with the projected coordinates or None if in_place is True.

    Raises:
        AssertionError: If epsg_from is equal to epsg_to, if fields has a length other than 3, or if any element in fields is not a string.
    """
    assert epsg_from != epsg_to, "EPSG codes must be different"
    assert len(fields) == 2, "Two fields must be specified (e.g., ['lat', 'lon'])"
    assert all(isinstance(i, str) for i in fields), "Fields must be strings"

    try:
        transformer = Transformer(epsg_from=epsg_from, epsg_to=epsg_to)
        assert (
            transformer.crs_from.is_geographic
        ), "Initial pyproj.CRS must be geographic."
        assert (
            transformer.crs_to.is_projected
        ), "Destination pyproj.CRS to must be projected."

    except Exception as e:
        print(
            f"Unable to convert coordinate from EPSG:{epsg_from} to EPSG:{epsg_to}: {e}"
        )
        return False

    for key in data_dict.keys():
        if data_dict[key] is None:
            print(f"Image {key} not found in data.")
            continue

        lat = data_dict[key][fields[0]]
        lon = data_dict[key][fields[1]]
        x, y = transformer.transform(lat, lon)

        if in_place:
            data_dict[key]["E"] = x
            data_dict[key]["N"] = y
            return None
        else:
            out = deepcopy(data_dict)
            out[key]["E"] = x
            out[key]["N"] = y
            return out
