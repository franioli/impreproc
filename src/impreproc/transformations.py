import numpy as np

from typing import Tuple
from affine import Affine


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
