from typing import List, Tuple
from pyproj import CRS, Transformer

import numpy as np
from affine import Affine


def project_to_utm(
    epsg_from: int,
    epsg_to: int,
    data_dict: dict,
    fields: List[str] = ["lat", "lon", "ellh"],
) -> bool:
    """
    Converts geographic coordinates (latitude, longitude, ellipsoid height) to projected UTM coordinates
    using the pyproj library.

    Args:
        epsg_from (int): EPSG code of the initial coordinate reference system (CRS).
        epsg_to (int): EPSG code of the destination CRS.
        data_dict (dict): Dictionary containing the data to be projected.
        fields (List[str], optional): List of three fields specifying the names of the latitude, longitude,and ellipsoid height fields in the data dictionary, respectively. Default is ["lat", "lon", "ellh"].

    Returns:
        bool: True if the projection was successful, False otherwise.

    Raises:
        AssertionError: If epsg_from is equal to epsg_to, if fields has a length other than 3, or if any element in fields is not a string.
    """
    assert epsg_from != epsg_to, "EPSG codes must be different"
    assert len(fields) == 3, "Three fields must be specified"
    assert all(isinstance(i, str) for i in fields), "Fields must be strings"

    try:
        crs_from = CRS.from_epsg(epsg_from)
        assert crs_from.is_geographic, "Initial CRS must be geographic."
        crs_to = CRS.from_epsg(epsg_to)
        assert crs_to.is_projected, "Destination CRS to must be projected."
        transformer = Transformer.from_crs(crs_from=crs_from, crs_to=crs_to)
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
        ellh = data_dict[key][fields[2]]
        x, y = transformer.transform(lat, lon)
        data_dict[key]["E"] = x
        data_dict[key]["N"] = y
        # data_dict[key]["h"] = z

    return True


def xy2rc(tform: Affine, x: float, y: float) -> Tuple[float, float]:
    """Converts x, y coordinates to row, column coordinates using an affine transformation, as stored in the rasterio dataset (i.e., the transformation that maps pixel coordinates to world coordinates)

    Args:
        tform (Affine): The affine transformation matrix.
        x (float): The x coordinate.
        y (float): The y coordinate.

    Returns:
        Tuple[float, float]: The row, column coordinates.
    """
    p = np.array([x, y]).reshape(2, -1)
    rc = ~tform * p
    return rc[1][0], rc[0][0]


def rc2xy(tform: Affine, row: float, col: float) -> Tuple[float, float]:
    """Converts row, column coordinates to x, y coordinates using an affine transformation, as stored in the rasterio dataset (i.e., the transformation that maps pixel coordinates to world coordinates)

    Args:
        tform (Affine): The affine transformation matrix.
        row (float): The row coordinate.
        col (float): The column coordinate.

    Returns:
        Tuple[float, float]: The x, y coordinates.
    """
    p = np.array([col, row]).reshape(2, -1)
    xy = tform * p
    return xy[0][0], xy[1][0]


def bilinear_interpolate(im, x, y):
    """Performs bilinear interpolation on a 2D array (single channel image given x, y arrays of unstructured query points.
    Args:
        im (np.ndarray): Single channel image.
        x (np.ndarray): nx1 array of x coordinates of query points.
        y (np.ndarray): nx1 array of y coordinates of query points.

    Returns:
        np.ndarray: nx1 array of the interpolated color.
    """
    x = np.asarray(x)
    y = np.asarray(y)

    x0 = np.floor(x).astype(int)
    x1 = x0 + 1
    y0 = np.floor(y).astype(int)
    y1 = y0 + 1

    x0 = np.clip(x0, 0, im.shape[1] - 1)
    x1 = np.clip(x1, 0, im.shape[1] - 1)
    y0 = np.clip(y0, 0, im.shape[0] - 1)
    y1 = np.clip(y1, 0, im.shape[0] - 1)

    Ia = im[y0, x0]
    Ib = im[y1, x0]
    Ic = im[y0, x1]
    Id = im[y1, x1]

    wa = (x1 - x) * (y1 - y)
    wb = (x1 - x) * (y - y0)
    wc = (x - x0) * (y1 - y)
    wd = (x - x0) * (y - y0)

    return wa * Ia + wb * Ib + wc * Ic + wd * Id


def get_geoid_undulation():
    pass
