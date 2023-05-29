import logging
from importlib import import_module
from pathlib import Path
from typing import List, Tuple, Union

import numpy as np
import pyproj
import rasterio
from rasterio import Affine


class Transformer:
    """
    A class for performing coordinate transformations between two different EPSG projections.

    Args:
        epsg_from (int): EPSG code of the source projection.
        epsg_to (int): EPSG code of the target projection.
        transform3d (bool, optional): Flag indicating whether to perform 3D transformations. Defaults to False.
        geoid_path (Union[str, Path], optional): Path to a raster file containing geoid undulation data.
            Required if `transform3d` is True. Defaults to None.

    Raises:
        AssertionError: If `epsg_from` and `epsg_to` are the same or not of integer type.

    Attributes:
        epsg_from (int): EPSG code of the source projection.
        epsg_to (int): EPSG code of the target projection.
        crs_from (pyproj.crs.CRS): CRS object of the source projection.
        crs_to (pyproj.crs.CRS): CRS object of the target projection.
        _transformer (pyproj.transformer.Transformer): Transformer object for performing the coordinate transformation.
        transform3d (bool): Flag indicating whether to perform 3D transformations.
        geoid_path (Union[str, Path]): Path to a raster file containing geoid undulation data.

    Methods:
        transform(lat: float, lon: float, ellh: float = None) -> Tuple[float, float] or Tuple[float, float, float]:
            Transforms a given set of latitude, longitude, and, optionally, ellipsoidal height coordinates from the source projection to the target projection.

            Args:
                lat (float): Latitude coordinate in decimal degrees.
                lon (float): Longitude coordinate in decimal degrees.
                ellh (float, optional): Ellipsoidal height coordinate in meters. Required if `transform3d` is True.

            Returns:
                A tuple containing the transformed x, y, and z (if transform3d` is True) coordinates.

            Raises:
                ValueError: If `transform3d` is True but `geoid_path` is not provided.
    """

    def __init__(
        self,
        epsg_from: int,
        epsg_to: int,
        transfrom3d: bool = False,
        geoid_path: Union[str, Path] = None,
    ) -> None:
        """Initializes a Transformer object for coordinate transformations.

        Args:
            epsg_from (int): EPSG code of the input coordinate reference system (CRS).
            epsg_to (int): EPSG code of the output CRS.
            transform3d (bool, optional): Indicates whether the transform should include a height component. Defaults to False.
            geoid_path (Union[str, Path], optional): Path to a geoid undulation raster file for height correction. Defaults to None.

        Raises:
            AssertionError: Raised if `epsg_from` and `epsg_to` are the same integer value.

        """
        assert epsg_from != epsg_to, "EPSG codes must be different"
        assert isinstance(epsg_from, int), "epsg_from must be an integer"
        assert isinstance(epsg_to, int), "epsg_to must be an integer"

        self.epsg_from = epsg_from
        self.epsg_to = epsg_to
        self.crs_from = pyproj.CRS.from_epsg(epsg_from)
        self.crs_to = pyproj.CRS.from_epsg(epsg_to)
        self._transformer = pyproj.Transformer.from_crs(
            crs_from=self.crs_from, crs_to=self.crs_to
        )

        if transfrom3d:
            # TODO: Add checks on 3D CRS!
            self.transform3d = transfrom3d
            self.crs_from.to_3d()
            self.crs_to.to_3d()
        else:
            self.transform3d = False

        self.geoid_path = geoid_path

    def transform(
        self, lat: float, lon: float, ellh: float = None
    ) -> Tuple[float, float, float]:
        """
        Transforms a given set of latitude, longitude, and, optionally, ellipsoidal height coordinates from the source projection to the target projection.

        Args:
            lat (float): Latitude coordinate in decimal degrees.
            lon (float): Longitude coordinate in decimal degrees.
            ellh (float, optional): Ellipsoidal height coordinate in meters. Required if `transform3d` is True.

        Returns:
            A tuple containing the transformed x, y, and z (if `transform3d` is True) coordinates.

        Raises:
            ValueError: If `transform3d` is True but `geoid_path` is not provided.
            AssertionError: If `ellh` is not provided for 3D transformations.
        """
        if not self.transform3d:
            x, y = self._transformer.transform(lat, lon, direction="FORWARD")
            return x, y
        else:
            assert ellh is not None, "ellh must be provided for 3D transformations"
            x, y, z_ellh = self._transformer.transform(
                lat, lon, ellh, direction="FORWARD"
            )
            return x, y, z_ellh


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


def bilinear_interpolate(im: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
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


def get_geoid_undulation(geoid_path: Union[str, Path]) -> Tuple[np.ndarray, Affine]:
    """
    Returns the geoid undulation and its affine transformation matrix from a geoid raster file.

    Args:
        geoid_path (Union[str, Path]): Path to the geoid raster file.

    Returns:
        Tuple[np.ndarray, Affine]: A tuple containing the geoid undulation as a NumPy array and its affine transformation matrix as a Rasterio Affine object.

    Raises:
        ImportError: Raised if rasterio is not installed in the system.
    """
    with rasterio.open(geoid_path) as src:
        geoid = src.read(1)
        tform = src.transform

    return geoid, tform


if __name__ == "__main__":
    import pyproj

    try:
        rasterio = import_module("rasterio")
    except ImportError as e:
        logging.error(
            "Unable to import rasterio for loading geoid undulation. Please install it using `pip install rasterio`"
        )
        raise e

    lat, lon, ellh = 45.463873, 9.190653, 100.0
    epsg_from = 4326  # ETRS89
    epsg_to = 32632  # UTM zone 32N

    transformer = Transformer(epsg_from, epsg_to, geoid_path="data/ITALGEO05_E00.tif")
    x, y = transformer.transform(lat, lon)

    assert np.isclose(x, 514904.631, rtol=1e-4)
    assert np.isclose(y, 5034500.589, rtol=1e-4)

    x, y, z_ellh = transformer.transform(lat, lon, ellh)
    assert np.isclose(z_ellh, 100.0, rtol=1e-5)

    # crs_from = pyproj.CRS.from_epsg(epsg_from)
    # crs_to = pyproj.CRS.from_epsg(epsg_to)
    # transformer = pyproj.Transformer.from_crs(crs_from=crs_from, crs_to=crs_to)
    # x, y, z_ellh = transformer.transform(lat, lon, ellh, direction="FORWARD")

    # Load geoid heights from geotiff
    fname = "data/ITALGEO05_E00.tif"
    with rasterio.open(fname) as src:
        # Convert lat/lon to row/col
        row, col = xy2rc(src.transform, lon, lat)
        # Intepolate geoid height
        geoid_undulation = bilinear_interpolate(src.read(1), col, row)
