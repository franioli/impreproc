import logging
import re
from copy import deepcopy
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import List, TypedDict, Union
import platform

import numpy as np
import pyproj
import xlsxwriter

from impreproc.images import Image, ImageList, latlonalt_from_exif
from impreproc.transformations import Transformer

logger = logging.getLogger(__name__)


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
            logging.error(f"Error reading file {file}: {e}")

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
            logging.warning(f"Image {key} not found in EXIF data.")

    return merged_dict


def project_to_utm(
    epsg_from: int,
    epsg_to: int,
    data_dict: dict,
    fields: List[str] = ["lat", "lon"],
    suffix: str = "utm",
    in_place: bool = False,
) -> Union[dict, None]:
    """
    Converts geographic coordinates (latitude, longitude) to projected UTM coordinates using the pyproj library.

    Args:
        epsg_from (int): EPSG code of the initial coordinate reference system (pyproj.CRS).
        epsg_to (int): EPSG code of the destination pyproj.CRS.
        data_dict (dict): Dictionary containing the data to be projected.
        fields (List[str], optional): List of two fields specifying the names of the latitude and longitude fields in the data dictionary, respectively. Default is ["lat", "lon"].
        suffix (str): Suffix to be appended to the new fields in the data dictionary. Default is "utm".
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
        logging.warning(
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
        logging.exception(
            f"Unable to convert coordinate from EPSG:{epsg_from} to EPSG:{epsg_to}: {e}"
        )
        return None

    if not in_place:
        out = deepcopy(data_dict)

    for key, row in data_dict.items():
        # Check if image is present in data_dict
        if row is None:
            logging.warning(
                f"Coordinate transformation failed for Image {key} not found. Input data is None."
            )
            continue

        # Check if all fields are present in data_dict
        for f in fields:
            if f not in row.keys():
                logging.warning(
                    f"Coordinate transformation failed for Image {key} not found. Field {f} not found in data_dict at row {key}"
                )
                continue

        lat = row[fields[0]]
        lon = row[fields[1]]
        x, y = transformer.transform(lat, lon)

        if in_place:
            row[f"E_{suffix}"] = x
            row[f"N_{suffix}"] = y
            if len(fields) == 3:
                row[f"h_{suffix}"] = deepcopy(row[fields[2]])
        else:
            out[key][f"E_{suffix}"] = x
            out[key][f"N_{suffix}"] = y

    if in_place:
        return None
    else:
        return out


def dji2xlsx(
    data_dict,
    foutname,
    flag_utm=0,
    utm_zone="32N",
    flag_qual=[50, 16, 1],
    scale_factors=[1, 1, 1],
):
    """Create excel file with both camera and log file original metadata, as
    well as a join file according to user choices

    SYNTAX:
        dji2xlsx(data_dict, foutname, flag_camera = 0, flag_utm = 0, utm_zone = "32N")

    INPUT:
    - data_dict   --> dictionary of the join jpg-log metadata
    - foutname    --> output file to be created
    - flag_camera --> use jpg coordinates instead of log file ones (default = 0)
    - flag_utm    --> convert output coordinates in utm (default = 0)
    - utm_zone    --> utm zone (default = "32N")

    Lorenzo Rossi
    v 1.0
    2023-05-18
    """

    if flag_utm == 1:
        epsg_WGS84 = 4326

        utm_emisph = utm_zone[-1]
        utm_zone = int(utm_zone[:-1])
        if utm_emisph == "N":
            utm_base = 32600
        elif utm_emisph == "S":
            utm_base = 32700
        epsg_UTM = utm_base + utm_zone

    # Create an new Excel file and add a worksheet.
    xbook = xlsxwriter.Workbook(foutname, {"nan_inf_to_errors": True})

    # Write camera data -----------------------------------------------------------
    exif_xsheet = xbook.add_worksheet("EXIF")

    if flag_utm == 1:
        project_to_utm(
            epsg_from=epsg_WGS84,
            epsg_to=epsg_UTM,
            data_dict=data_dict,
            fields=["lat_exif", "lon_exif", "ellh_exif"],
            suffix="exif",
            in_place=True,
        )

        h_exif = [
            "ID",
            "Image Name",
            "Image Path",
            "Date-Time",
            "Lon [deg]",
            "Lat [deg]",
            "h [m]",
            "East UTM%s%s [m]" % (utm_zone, utm_emisph),
            "North UTM%s%s [m]" % (utm_zone, utm_emisph),
            "h UTM%s%s [m]" % (utm_zone, utm_emisph),
        ]
    else:
        h_exif = [
            "ID",
            "Image Name",
            "Image Path",
            "Date-Time",
            "Lon [deg]",
            "Lat [deg]",
            "h [m]",
        ]

    # header
    for i in range(len(h_exif)):
        exif_xsheet.write(0, i, h_exif[i], xbook.add_format({"bold": True}))

    r = 0
    for key, row in data_dict.items():
        if row is None:
            logging.warning(f"Skipping image {key}: image not present in data folder.")
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
            suffix="mrk",
            in_place=True,
        )

        h_log = [
            "ID",
            "Clock time [s]",
            "Lon [deg]",
            "Lat [deg]",
            "h [m]",
            "East UTM%s%s [m]" % (utm_zone, utm_emisph),
            "North UTM%s%s [m]" % (utm_zone, utm_emisph),
            "h UTM%s%s [m]" % (utm_zone, utm_emisph),
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

    # Output data --------------------------------------------------------------
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
                logging.warning(
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
    if system != "Windows":
        logging.warning(
            f"Unable to resize columns on {system} systems. Please resize columns manually."
        )
    else:
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
            logging.warning("Problem while resizing columns!")
