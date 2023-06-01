import logging
import platform
import re
from copy import deepcopy
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import List, TypedDict, Union

import numpy as np
import pyproj
import xlsxwriter

from impreproc.images import Image, ImageList, latlonalt_from_exif
from impreproc.transformations import Transformer

logger = logging.getLogger(__name__)


# Define type hints
class DataDict(TypedDict):
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
    name: str
    path: str
    date: str
    time: str


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


# Functions


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
            logger.error(f"Error reading file {file}: {e}")

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
            logger.warning(f"Image {key} not found in EXIF data.")

    return merged_dict


def project_to_utm(
    epsg_from: int,
    epsg_to: int,
    data_dict: dict,
    fields: List[str] = ["lat", "lon"],
    suffix: str = "",
    in_place: bool = False,
) -> Union[dict, None]:
    """
    Converts geographic coordinates (latitude, longitude) to projected UTM coordinates using the pyproj library.

    Args:
        epsg_from (int): EPSG code of the initial coordinate reference system (pyproj.CRS).
        epsg_to (int): EPSG code of the destination pyproj.CRS.
        data_dict (dict): Dictionary containing the data to be projected.
        fields (List[str], optional): List of two fields specifying the names of the latitude and longitude fields in the data dictionary, respectively. Default is ["lat", "lon"].
        suffix (str): Suffix to be appended to the new fields in the data dictionary. Default is "".
        in_place (bool, optional): If True, the projection is applied in-place to the data_dict. If False, a new dictionary with the projected coordinates is returned. Default is False.

    Returns:
        dict or None: A new dictionary with the projected coordinates or None if in_place is True.

    Raises:
        AssertionError: If epsg_from is equal to epsg_to, if fields has a length other than 3, or if any element in fields is not a string.
    """
    assert epsg_from != epsg_to, "EPSG codes must be different"
    assert len(fields) in [
        2,
        3,
    ], "Two or Three fields must be specified (e.g., ['lat', 'lon'] or ['lat', 'lon', 'h'])"
    assert all(isinstance(i, str) for i in fields), "Fields must be strings"

    if len(fields) == 3:
        logger.info(
            "Height transformation not implemented yet. Hellispoidical height will be used."
        )

    try:
        transformer = Transformer(epsg_from=epsg_from, epsg_to=epsg_to)
        assert (
            transformer.crs_from.is_geographic
        ), "Initial pyproj.CRS must be geographic."
        assert (
            transformer.crs_to.is_projected
        ), "Destination pyproj.CRS to must be projected."

    except Exception as e:
        logger.exception(
            f"Unable to convert coordinate from EPSG:{epsg_from} to EPSG:{epsg_to}: {e}"
        )
        return None

    if not in_place:
        out = deepcopy(data_dict)

    for key, row in data_dict.items():
        # Check if image is present in data_dict
        if row is None:
            logger.warning(
                f"Coordinate transformation failed for Image {key} not found. Input data is None."
            )
            continue

        # Check if all fields are present in data_dict
        for f in fields:
            if f not in row.keys():
                logger.warning(
                    f"Coordinate transformation failed for Image {key} not found. Field {f} not found in data_dict at row {key}"
                )
                continue

        lat = row[fields[0]]
        lon = row[fields[1]]
        x, y = transformer.transform(lat, lon)

        if in_place:
            row[f"E{suffix}"] = x
            row[f"N{suffix}"] = y
            if len(fields) == 3:
                row[f"h{suffix}"] = deepcopy(row[fields[2]])
        else:
            out[key][f"E{suffix}"] = x
            out[key][f"N{suffix}"] = y
            if len(fields) == 3:
                row[f"h{suffix}"] = deepcopy(row[fields[2]])

    if in_place:
        return None
    else:
        return out


def get_epsg_from_utm_zone(utm_zone: str) -> int:
    utm_emisph = utm_zone[-1]
    utm_zone = int(utm_zone[:-1])
    utm_base = 32600 if utm_emisph == "N" else 32700
    epsg_UTM = utm_base + utm_zone

    return epsg_UTM


def dji2csv(
    data_dict: dict,
    foutname: str,
    flag_utm: bool = False,
    utm_zone: str = "32N",
    flag_useImageCoord: bool = False,
    flag_qual: list = [50, 16, 1],
    scale_factors: list = [1, 1, 1],
) -> bool:
    """
    Convert DJI metadata dictionary to CSV file.

    Args:
        data_dict (Dict): Dictionary containing DJI metadata.
        foutname (str): Output CSV file name.
        flag_utm (bool, optional): Flag to indicate UTM projection. Defaults to False.
        utm_zone (str, optional): UTM zone. Defaults to "32N".
        flag_useImageCoord (bool, optional): Flag to use image coordinates. Defaults to False.
        flag_qual (List, optional): Quality flags. Defaults to [50, 16, 1].
        scale_factors (List, optional): Scale factors. Defaults to [1, 1, 1].

    Returns:
        bool: True if the file is created successfully, False otherwise.

    """

    # Make deepcopy of data_dict to NOT modify input data
    data4csv = deepcopy(data_dict)

    # Use either coordinates from image EXIF metadata or from .mrk file
    for k, v in data4csv.items():
        if v is None:
            logger.warning(f"Skipping image {k}: image not present in data folder.")
            continue
        if flag_useImageCoord == False:
            v["lat"] = v["lat_mrk"]
            v["lon"] = v["lon_mrk"]
            v["ellh"] = v["ellh_mrk"]
        else:
            v["lat"] = v["lat_exif"]
            v["lon"] = v["lon_exif"]
            v["ellh"] = v["ellh_exif"]

    # Apply UTM projection to coordinates
    if flag_utm:
        epsg_WGS84 = 4326
        epsg_UTM = get_epsg_from_utm_zone(utm_zone)
        project_to_utm(
            epsg_from=epsg_WGS84,
            epsg_to=epsg_UTM,
            data_dict=data4csv,
            fields=["lat", "lon", "ellh"],
            in_place=True,
        )

    # Apply scaling factors to standard deviations obtained from .mrk file
    for k, v in data4csv.items():
        if v is None:
            continue
        if v["Qual_mrk"] == flag_qual[0]:
            v["stdE"] = scale_factors[0] * v["stdE_mrk"]
            v["stdN"] = scale_factors[0] * v["stdN_mrk"]
            v["stdV"] = scale_factors[0] * v["stdV_mrk"]
        elif v["Qual_mrk"] == flag_qual[1]:
            v["stdE"] = scale_factors[1] * v["stdE_mrk"]
            v["stdN"] = scale_factors[1] * v["stdN_mrk"]
            v["stdV"] = scale_factors[1] * v["stdV_mrk"]
        elif v["Qual_mrk"] == flag_qual[2]:
            v["stdE"] = scale_factors[2] * v["stdE_mrk"]
            v["stdN"] = scale_factors[2] * v["stdN_mrk"]
            v["stdV"] = scale_factors[2] * v["stdV_mrk"]
        else:
            logger.warning(f"Skipping image {k}: invalid quality flag.")

    # define header for csv file
    header = [
        "ID",
        "Image Name",
        "Image Path",
        "Date [yyyy:mm:dd]",
        "Time [hh:mm:ss]",
        "Lon [deg]",
        "Lat [deg]",
        "h [m]",
    ]
    if flag_utm:
        header.extend(
            [
                f"East UTM{utm_zone} [m]",
                f"North UTM{utm_zone} [m]",
                f"h UTM{utm_zone} [m]",
            ]
        )
    header.extend(["stdE [m]", "stdN [m]", "stdV [m]"])

    # write csv file
    with open(foutname, "w") as fout:
        fout.write(",".join(header) + "\n")
        for k, v in data4csv.items():
            if v is None:
                continue
            ln = [
                v["id"],
                Path(v["path_exif"]).name,
                v["path_exif"],
                v["date_exif"],
                v["time_exif"],
                f"{v['lon']:0.8f}",
                f"{v['lat']:0.8f}",
                f"{v['ellh']:0.3f}",
            ]
            if flag_utm:
                ln.extend(
                    [
                        f"{v['E']:.3f}",
                        f"{v['N']:.3f}",
                        f"{v['h']:.3f}",
                    ]
                )
            ln.extend(
                [
                    f"{v['stdE']:.4f}",
                    f"{v['stdN']:.4f}",
                    f"{v['stdV']:.4f}",
                ]
            )
            ln = [str(x) for x in ln]
            fout.write(",".join(ln) + "\n")

    logger.info(f"CSV file {foutname} written successfully.")

    return True


def dji2xlsx(
    data_dict: dict,
    foutname: str,
    flag_utm: int = 0,
    utm_zone: str = "32N",
    flag_qual: list = [50, 16, 1],
    scale_factors: list = [1, 1, 1],
) -> bool:
    """Create an Excel file with both camera and log file original metadata, as
    well as a join file according to user choices.

    Args:
        data_dict (dict): Dictionary of the join jpg-log metadata.
        foutname (str): Output file to be created.
        flag_utm (int, optional): Use UTM coordinates instead of log file ones. Defaults to 0.
        utm_zone (str, optional): UTM zone. Defaults to "32N".
        flag_qual (list, optional): Flag quality. Defaults to [50, 16, 1].
        scale_factors (list, optional): Scale factors. Defaults to [1, 1, 1].

    Returns:
        bool: True if the file is created successfully, False otherwise.

    """
    # Make deepcopy of data_dict to NOT modify input data
    data_dict = deepcopy(data_dict)

    # Create an new Excel file and add a worksheet.
    xbook = xlsxwriter.Workbook(foutname, {"nan_inf_to_errors": True})

    # Write camera data -----------------------------------------------------------
    exif_xsheet = xbook.add_worksheet("EXIF")
    h_exif = [
        "ID",
        "Image Name",
        "Image Path",
        "Date-Time",
        "Lon [deg]",
        "Lat [deg]",
        "h [m]",
    ]
    if flag_utm == 1:
        epsg_WGS84 = 4326
        epsg_UTM = get_epsg_from_utm_zone(utm_zone)
        project_to_utm(
            epsg_from=epsg_WGS84,
            epsg_to=epsg_UTM,
            data_dict=data_dict,
            fields=["lat_exif", "lon_exif", "ellh_exif"],
            suffix="_exif",
            in_place=True,
        )
        h_exif.extend(
            [
                f"East UTM{utm_zone} [m]",
                f"North UTM{utm_zone} [m]",
                f"h UTM{utm_zone} [m]",
            ]
        )

    # header
    for i in range(len(h_exif)):
        exif_xsheet.write(0, i, h_exif[i], xbook.add_format({"bold": True}))

    r = 0
    for key, row in data_dict.items():
        if row is None:
            logger.warning(f"Skipping image {key}: image not present in data folder.")
            r = r + 1
            continue

        r = r + 1
        # image ID
        c = 0
        exif_xsheet.write(r, c, key)
        # image name
        c = c + 1
        exif_xsheet.write(r, c, row["name_exif"])
        # image path
        c = c + 1
        exif_xsheet.write(r, c, row["path_exif"])
        # date-time
        c = c + 1
        date_time = datetime.strptime(
            row["date_exif"].replace(":", "/") + " " + row["time_exif"],
            "%Y/%m/%d %H:%M:%S",
        )
        exif_xsheet.write(
            r, c, date_time, xbook.add_format({"num_format": "yyyy/mm/dd hh:mm:ss"})
        )
        # Longitude
        c = c + 1
        if not (np.isnan(row["lon_exif"])):
            exif_xsheet.write(
                r,
                c,
                row["lon_exif"],
                xbook.add_format({"num_format": "0." + "0" * 8}),
            )
        # Latitude
        c = c + 1
        if not (np.isnan(row["lat_exif"])):
            exif_xsheet.write(
                r,
                c,
                row["lat_exif"],
                xbook.add_format({"num_format": "0." + "0" * 8}),
            )
        # Ellipsoidal height
        c = c + 1
        if not (np.isnan(row["ellh_exif"])):
            exif_xsheet.write(
                r,
                c,
                row["ellh_exif"],
                xbook.add_format({"num_format": "0." + "0" * 3}),
            )
        if flag_utm == 1:
            # East
            c = c + 1
            if not (np.isnan(row["E_exif"])):
                exif_xsheet.write(
                    r,
                    c,
                    row["E_exif"],
                    xbook.add_format({"num_format": "0." + "0" * 3}),
                )
            # North
            c = c + 1
            if not (np.isnan(row["N_exif"])):
                exif_xsheet.write(
                    r,
                    c,
                    row["N_exif"],
                    xbook.add_format({"num_format": "0." + "0" * 3}),
                )
            # height
            c = c + 1
            if not (np.isnan(row["h_exif"])):
                exif_xsheet.write(
                    r,
                    c,
                    row["h_exif"],
                    xbook.add_format({"num_format": "0." + "0" * 3}),
                )

    # Write log data --------------------------------------------------------------
    log_xsheet = xbook.add_worksheet("LOG")
    if flag_utm == 1:
        project_to_utm(
            epsg_from=epsg_WGS84,
            epsg_to=epsg_UTM,
            data_dict=data_dict,
            fields=["lat_mrk", "lon_mrk", "ellh_mrk"],
            suffix="_mrk",
            in_place=True,
        )

        h_log = [
            "ID",
            "Clock time [s]",
            "Lon [deg]",
            "Lat [deg]",
            "h [m]",
            f"East UTM{utm_zone} [m]",
            f"North UTM{utm_zone} [m]",
            f"h UTM{utm_zone} [m]",
            "ESDV [m]",
            "NSDV [m]",
            "VSDV [m]",
            "dE [m]",
            "dN [m]",
            "dV [m]",
            "Quality",
            "Flag",
        ]
    else:
        h_log = [
            "ID",
            "Clock time [s]",
            "Lon [deg]",
            "Lat [deg]",
            "h [m]",
            "ESDV [m]",
            "NSDV [m]",
            "VSDV [m]",
            "dE [m]",
            "dN [m]",
            "dV [m]",
            "Quality",
            "Flag",
        ]
    # header
    for i in range(len(h_log)):
        log_xsheet.write(0, i, h_log[i], xbook.add_format({"bold": True}))

    r = 0
    for key, row in data_dict.items():
        if row is None:
            r = r + 1
            continue

        r = r + 1
        # image ID
        c = 0
        log_xsheet.write(r, c, key)
        # time
        c = c + 1
        log_xsheet.write(
            r,
            c,
            row["clock_time_mrk"],
            xbook.add_format({"num_format": "0." + "0" * 6}),
        )
        # Longitude
        c = c + 1
        if not (np.isnan(row["lon_mrk"])):
            log_xsheet.write(
                r,
                c,
                row["lon_mrk"],
                xbook.add_format({"num_format": "0." + "0" * 8}),
            )
        # Latitude
        c = c + 1
        if not (np.isnan(row["lat_mrk"])):
            log_xsheet.write(
                r,
                c,
                row["lat_mrk"],
                xbook.add_format({"num_format": "0." + "0" * 8}),
            )
        # Ellipsoidal height
        c = c + 1
        if not (np.isnan(row["ellh_mrk"])):
            log_xsheet.write(
                r,
                c,
                row["ellh_mrk"],
                xbook.add_format({"num_format": "0." + "0" * 3}),
            )
        if flag_utm == 1:
            # Longitude
            c = c + 1
            if not (np.isnan(row["E_mrk"])):
                log_xsheet.write(
                    r,
                    c,
                    row["E_mrk"],
                    xbook.add_format({"num_format": "0." + "0" * 3}),
                )
            # Latitude
            c = c + 1
            if not (np.isnan(row["N_mrk"])):
                log_xsheet.write(
                    r,
                    c,
                    row["N_mrk"],
                    xbook.add_format({"num_format": "0." + "0" * 3}),
                )
            # Ellipsoidal height
            c = c + 1
            if not (np.isnan(row["h_mrk"])):
                log_xsheet.write(
                    r,
                    c,
                    row["h_mrk"],
                    xbook.add_format({"num_format": "0." + "0" * 3}),
                )
        # ESDV
        c = c + 1
        if not (np.isnan(row["stdE_mrk"])):
            log_xsheet.write(
                r,
                c,
                row["stdE_mrk"],
                xbook.add_format({"num_format": "0." + "0" * 3}),
            )
        # NSDV
        c = c + 1
        if not (np.isnan(row["stdN_mrk"])):
            log_xsheet.write(
                r,
                c,
                row["stdN_mrk"],
                xbook.add_format({"num_format": "0." + "0" * 3}),
            )
        # VSDV
        c = c + 1
        if not (np.isnan(row["stdV_mrk"])):
            log_xsheet.write(
                r,
                c,
                row["stdV_mrk"],
                xbook.add_format({"num_format": "0." + "0" * 3}),
            )
        # dE
        c = c + 1
        if not (np.isnan(row["dE_mrk"])):
            log_xsheet.write(
                r,
                c,
                row["dE_mrk"] / 1000,
                xbook.add_format({"num_format": "0." + "0" * 3}),
            )
        # dN
        c = c + 1
        if not (np.isnan(row["dN_mrk"])):
            log_xsheet.write(
                r,
                c,
                row["dN_mrk"] / 1000,
                xbook.add_format({"num_format": "0." + "0" * 3}),
            )
        # dH
        c = c + 1
        if not (np.isnan(row["dV_mrk"])):
            log_xsheet.write(
                r,
                c,
                row["dV_mrk"] / 1000,
                xbook.add_format({"num_format": "0." + "0" * 3}),
            )
        # Qual
        c = c + 1
        if not (np.isnan(row["Qual_mrk"])):
            log_xsheet.write(
                r, c, row["Qual_mrk"], xbook.add_format({"num_format": "0"})
            )
        # Flag
        c = c + 1
        log_xsheet.write(r, c, row["Flag_mrk"])

    # Output data
    # --------------------------------------------------------------
    coord_ref_sheets = ["LOG", "EXIF"]
    for coord_ref_sheet in coord_ref_sheets:
        output_xsheet = xbook.add_worksheet("OUTPUT_" + coord_ref_sheet)
        if flag_utm == 1:
            h_output = [
                "Image name",
                "East [m]",
                "North [m]",
                "h [m]",
                "ESDV [m]",
                "NSDV [m]",
                "VSDV [m]",
            ]
        else:
            h_output = [
                "Image Name",
                "Lon [deg]",
                "Lat [deg]",
                "h [m]",
                "ESDV [m]",
                "NSDV [m]",
                "VSDV [m]",
            ]

        # header
        for i in range(len(h_output)):
            output_xsheet.write(0, i, h_output[i], xbook.add_format({"bold": True}))

        # table with scale factors
        output_xsheet.write(
            1, len(h_output) + 1, "FIXED", xbook.add_format({"bold": True})
        )
        output_xsheet.write(
            2, len(h_output) + 1, "FLOAT", xbook.add_format({"bold": True})
        )
        output_xsheet.write(
            3, len(h_output) + 1, "AUTONOMOUS", xbook.add_format({"bold": True})
        )

        output_xsheet.write(
            0, len(h_output) + 2, "FLAG", xbook.add_format({"bold": True})
        )
        output_xsheet.write(
            0, len(h_output) + 3, "FACTOR", xbook.add_format({"bold": True})
        )

        output_xsheet.write(
            1, len(h_output) + 2, flag_qual[0], xbook.add_format({"num_format": "0"})
        )
        output_xsheet.write(
            2, len(h_output) + 2, flag_qual[1], xbook.add_format({"num_format": "0"})
        )
        output_xsheet.write(
            3, len(h_output) + 2, flag_qual[2], xbook.add_format({"num_format": "0"})
        )

        output_xsheet.write(
            1,
            len(h_output) + 3,
            scale_factors[0],
            xbook.add_format({"num_format": "0." + "0" * 3}),
        )
        output_xsheet.write(
            2,
            len(h_output) + 3,
            scale_factors[1],
            xbook.add_format({"num_format": "0." + "0" * 3}),
        )
        output_xsheet.write(
            3,
            len(h_output) + 3,
            scale_factors[2],
            xbook.add_format({"num_format": "0." + "0" * 3}),
        )

        r = 0
        for key in data_dict.keys():
            if data_dict[key] is None:
                logger.warning(
                    f"Skipping image {key}: image not present in data folder."
                )
                r = r + 1
                continue

            r = r + 1

            # image name
            c = 0
            output_xsheet.write_formula(
                r, c, '=CONCATENATE(EXIF!B%d, ".jpg")' % (r + 1)
            )
            if coord_ref_sheet == "LOG":
                llh_cols = ["C", "D", "E"]
                enh_cols = ["F", "G", "H"]
            else:
                llh_cols = ["E", "F", "G"]
                enh_cols = ["H", "I", "J"]

            if flag_utm == 1:
                # East
                c = c + 1
                output_xsheet.write_formula(
                    r,
                    c,
                    "=%s!%s%d" % (coord_ref_sheet, enh_cols[0], r + 1),
                    xbook.add_format({"num_format": "0." + "0" * 3}),
                )
                # North
                c = c + 1
                output_xsheet.write_formula(
                    r,
                    c,
                    "=%s!%s%d" % (coord_ref_sheet, enh_cols[1], r + 1),
                    xbook.add_format({"num_format": "0." + "0" * 3}),
                )
                # h
                c = c + 1
                output_xsheet.write_formula(
                    r,
                    c,
                    "=%s!%s%d" % (coord_ref_sheet, enh_cols[2], r + 1),
                    xbook.add_format({"num_format": "0." + "0" * 3}),
                )
            else:
                # Lon
                c = c + 1
                output_xsheet.write_formula(
                    r,
                    c,
                    "=%s!%s%d" % (coord_ref_sheet, llh_cols[0], r + 1),
                    xbook.add_format({"num_format": "0." + "0" * 8}),
                )
                # Lat
                c = c + 1
                output_xsheet.write_formula(
                    r,
                    c,
                    "=%s!%s%d" % (coord_ref_sheet, llh_cols[1], r + 1),
                    xbook.add_format({"num_format": "0." + "0" * 8}),
                )
                # h
                c = c + 1
                output_xsheet.write_formula(
                    r,
                    c,
                    "=%s!%s%d" % (coord_ref_sheet, llh_cols[2], r + 1),
                    xbook.add_format({"num_format": "0." + "0" * 3}),
                )
            # ESDV, NSDV, VSDV
            cols = ["I", "J", "K"]  # columns with stds in LOG file
            for col in cols:
                c = c + 1
                if_auton = "IF(LOG!O%d<=$J$4,%s!%s%d*$K$4," % (r + 1, "LOG", col, r + 1)
                if_float = "IF(LOG!O%d<=$J$3,%s!%s%d*$K$3," % (r + 1, "LOG", col, r + 1)
                if_fixed = "IF(LOG!O%d<=$J$2,%s!%s%d*$K$2," % (r + 1, "LOG", col, r + 1)
                output_xsheet.write_formula(
                    r,
                    c,
                    "="
                    + if_auton
                    + if_float
                    + if_fixed
                    + "%s!%s%d)))" % (coord_ref_sheet, col, r + 1),
                    xbook.add_format({"num_format": "0." + "0" * 3}),
                )

    xbook.close()

    system = platform.system()
    if system == "Windows":
        try:
            win32 = import_module("win32com.client")
            excel = win32.Dispatch("Excel.Application")
            excel.Visible = 0
            wb = excel.Workbooks.Open(foutname)
            ws = wb.Worksheets("EXIF")
            ws.Columns.AutoFit()
            ws = wb.Worksheets("LOG")
            ws.Columns.AutoFit()
            for coord_ref_sheet in coord_ref_sheets:
                ws = wb.Worksheets("OUTPUT_" + coord_ref_sheet)
                ws.Columns.AutoFit()
            wb.Save()
            wb.Close()
            # excel.Application.Quit()
        except:
            logger.warning("Problem while resizing columns!")
    else:
        logger.warning(
            f"Unable to resize columns on {system} systems. Please resize columns manually."
        )

    logger.info("Excel file created successfully.")

    return True
