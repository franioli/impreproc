"""
MIT License

Copyright (c) 2022 Francesco Ioli

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import logging
import os
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import List, Union

import cv2
import exifread
import numpy as np


class ImageList:
    def __init__(
        self,
        data_dir: Union[str, Path],
        image_ext: Union[str, List[str]] = None,
        # name_pattern: str = None,
        recursive: bool = False,
        case_sensitive: bool = False,
    ) -> None:
        """
        Initialize a new ImageList object by specifying the directory containing image files.

        Args:
            data_dir (Union[str, Path]): A string or Path object specifying the directory path containing image files.
            image_ext (Union[str, List[str]], optional): A string or list of strings specifying the image file extensions to search for. Defaults to None, which searches for all file types.
            name_pattern (str, optional): A string pattern to search for within image file names. Defaults to None.
            recursive (bool, optional): Whether to search for image files recursively in subdirectories. Defaults to False.
            case_sensitive (bool, optional): Whether to search for image files with case sensitivity. Defaults to False.

        Example:

        >>> from pathlib import Path
        >>> from impreproc.images import ImageList
        >>> data_dir = Path("/path/to/image/directory")
        >>> image_list = ImageList(data_dir, image_ext=["jpg", "png"], recursive=True)

        """
        self._files = read_image_list(
            data_dir=data_dir,
            image_ext=image_ext,
            recursive=recursive,
            case_sensitive=case_sensitive,
        )
        self._current_idx = 0

    def __len__(self):
        return len(self._files)

    def __getitem__(self, idx):
        return self._files[idx]

    def __iter__(self):
        return self

    def __next__(self):
        if self._current_idx >= len(self._files):
            self._current_idx = 0
            raise StopIteration
        cur = self._current_idx
        self._current_idx += 1
        return self._files[cur]

    def __repr__(self):
        return f"ImageList with {len(self._files)} images."

    @property
    def files(self):
        return self._files

    @property
    def head(self) -> None:
        for file in self._files[:5]:
            print(file)
        return None

    def get_image_name(self, idx):
        return self._files[idx].name

    def get_image_path(self, idx):
        return self._files[idx]

    def get_image_folder(self, idx):
        return self._files[idx].parent

    def get_image_stem(self, idx):
        return self._files[idx].stem


class Image:
    """A class representing an image.

    Attributes:
        _path (Path): The path to the image file.
        _value_array (np.ndarray): Numpy array containing pixel values. If available, it can be accessed with `Image.value`.
        _width (int): The width of the image in pixels.
        _height (int): The height of the image in pixels.
        _exif_data (dict): The EXIF metadata of the image, if available.
        _date_time (datetime): The date and time the image was taken, if available.

    """

    def __init__(self, path: Union[str, Path], image: np.ndarray = None) -> None:
        """
        __init__ Create Image object

        Args:
            path (Union[str, Path]): path to the image
            image (np.ndarray, optional): Numpy array containing pixel values. If provided, they are stored in self._value_array and they are accessible from outside the class with Image.value. Defaults to None.
        """

        self._path = Path(path)
        self._value_array = None
        self._width = None
        self._height = None
        self._exif_data = None
        self._date_time = None
        self.read_exif()

        if image:
            self._value_array = image

    @property
    def height(self) -> int:
        """Returns the height of the image"""
        if self._height:
            return int(self._height)
        else:
            logging.error("Image height not available. Read it from exif first")
            return None

    @property
    def width(self) -> int:
        """Returns the width of the image"""
        if self._width:
            return int(self._width)
        else:
            logging.error("Image width not available. Read it from exif first")
            return None

    @property
    def name(self) -> str:
        """Returns the name of the image (including extension)"""
        return self._path.name

    @property
    def stem(self) -> str:
        """Returns the name of the image (excluding extension)"""
        return self._path.stem

    @property
    def path(self) -> str:
        """Path of the image"""
        return self._path

    @property
    def parent(self) -> str:
        """Path to the parent folder of the image"""
        return self._path.parent

    @property
    def extension(self) -> str:
        """Returns the extension  of the image"""
        return self._path.suffix

    @property
    def exif(self) -> dict:
        """
        exif Returns the exif of the image

        Returns:
            dict: Dictionary containing Exif information
        """
        return self._exif_data

    @property
    def date(self) -> str:
        """
        Returns the date and time of the image in a string format.
        If the information is not available in the EXIF metadata, it returns None.

        Returns:
            str or None: The date and time of the image in the format "YYYY:MM:DD HH:MM:SS", or None if not available.
        """
        if self._date_time is not None:
            return self._date_time.strftime("%Y:%m:%d")
        else:
            logging.error("No exif data available.")
            return

    @property
    def time(self) -> str:
        """
        time Returns the time of the image from exif as a string

        """
        if self._date_time is not None:
            return self._date_time.strftime("%H:%M:%S")
        else:
            logging.error("No exif data available.")
            return None

    @property
    def value(self) -> np.ndarray:
        """
        Returns the image (pixel values) as numpy array
        """
        if self._value_array is not None:
            return self._value_array
        else:
            return self.read_image(self._path)

    def get_datetime(self) -> datetime:
        """
        Returns the date and time of the image in a string format.
        If the information is not available in the EXIF metadata, it returns None.

        Returns:
            datetime: The date and time of the image as datetime object
        """
        if self._date_time is not None:
            return self._date_time
        else:
            logging.error("No exif data available.")
            return

    def read_image(
        self,
        # path: Union[str, Path],
        col: bool = True,
        resize: List[int] = [-1],
        crop: List[int] = None,
    ) -> None:
        """Wrapper around the function read_image to be a class method."""
        # path = Path(path)
        if self.path.exists():
            self._value_array = read_image(self.path, col, resize, crop)
            self.read_exif()
        else:
            logging.error(f"Input paht {self.path} not valid.")

    def reset_image(self) -> None:
        self._value_array = None

    def read_exif(self) -> None:
        """Reads the Exchangeable image file format (EXIF) metadata of an image file and stores them in a dictionary.

        This function reads the EXIF data of an image file using the exifread library, and then stores the metadata
        in a dictionary. The image path is specified by the `_path` attribute of the Image object.

        If no EXIF data is available for the image, an error message will be logged.

        If the EXIF data contains the image size information, this function extracts the width and height of the image
        from the EXIF data and stores them in the `_width` and `_height` attributes of the Image object.

        If the image size information is not available in the EXIF data, this function tries to load the image file and
        obtain the image size from the Numpy array. If the image size cannot be obtained from either the EXIF data or the
        Numpy array, a runtime error is raised.

        Returns:
            None
        """
        try:
            f = open(self._path, "rb")
            self._exif_data = exifread.process_file(f, details=False)
            f.close()
        except:
            logging.error("No exif data available.")

        # Get image size
        if (
            "Image ImageWidth" in self._exif_data.keys()
            and "Image ImageLength" in self._exif_data.keys()
        ):
            self._width = self._exif_data["Image ImageWidth"].printable
            self._height = self._exif_data["Image ImageLength"].printable
        elif (
            "EXIF ExifImageWidth" in self._exif_data.keys()
            and "EXIF ExifImageLength" in self._exif_data.keys()
        ):
            self._width = self._exif_data["EXIF ExifImageWidth"].printable
            self._height = self._exif_data["EXIF ExifImageLength"].printable
        else:
            logging.error(
                "Image width and height found in exif. Try to load the image and get image size from numpy array"
            )
            try:
                img = Image(self.path)
                self.height, self.width = img.height, img.width

            except:
                raise RuntimeError("Unable to get image dimensions.")

        # Get Image Date and Time
        self._date_time_fmt = "%Y:%m:%d %H:%M:%S"
        if "Image DateTime" in self._exif_data.keys():
            date_str = self._exif_data["Image DateTime"].printable
        elif "EXIF DateTimeOriginal" in self._exif_data.keys():
            date_str = self._exif_data["EXIF DateTimeOriginal"].printable
        else:
            logging.error("Date not available in exif.")
            return
        self._date_time = datetime.strptime(date_str, self._date_time_fmt)

    def extract_patch(self, limits: List[int]) -> np.ndarray:
        """
        Extract a patch from the image.

        Args:
            limits (List[int]): A list containing the bounding box coordinates [xmin, ymin, xmax, ymax].

        Returns:
            np.ndarray: The image patch extracted from the image.
        """
        image = read_image(self._path)
        patch = image[
            limits[1] : limits[3],
            limits[0] : limits[2],
        ]
        return patch

    def get_intrinsics_from_exif(self) -> np.ndarray:
        """Constructs the camera intrinsics from exif tag.

        Equation: focal_px=max(w_px,h_px)*focal_mm / ccdw_mm

        Note:
            References for this functions can be found:

            * https://github.com/colmap/colmap/blob/e3948b2098b73ae080b97901c3a1f9065b976a45/src/util/bitmap.cc#L282
            * https://openmvg.readthedocs.io/en/latest/software/SfM/SfMInit_ImageListing/
            * https://photo.stackexchange.com/questions/40865/how-can-i-get-the-image-sensor-dimensions-in-mm-to-get-circle-of-confusion-from # noqa: E501

        Returns:
            K (np.ndarray): intrinsics matrix (3x3 numpy array).
        """
        sens_db = import_module("impreproc.utils.sensor_width_database")

        if self._exif_data is None or len(self._exif_data) == 0:
            try:
                self.read_exif()
            except OSError:
                logging.error("Unable to read exif data.")
                return None
        try:
            focal_length_mm = float(self._exif_data["EXIF FocalLength"].printable)
        except OSError:
            logging.error("Focal length non found in exif data.")
            return None
        try:
            sensor_width_db = sens_db.SensorWidthDatabase()
            sensor_width_mm = sensor_width_db.lookup(
                self._exif_data["Image Make"].printable,
                self._exif_data["Image Model"].printable,
            )
        except OSError:
            logging.error("Unable to get sensor size in mm from sensor database")
            return None

        img_w_px = self.width
        img_h_px = self.height
        focal_length_px = max(img_h_px, img_w_px) * focal_length_mm / sensor_width_mm
        center_x = img_w_px / 2
        center_y = img_h_px / 2
        K = np.array(
            [
                [focal_length_px, 0.0, center_x],
                [0.0, focal_length_px, center_y],
                [0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        return K

    def undistort_image(
        self, K: np.ndarray, dist: np.ndarray, out_path: str = None
    ) -> np.ndarray:
        """
        Wrapper around OpenCV's `cv2.undistort` function to undistort the image.

        Args:
            K (np.ndarray): Camera intrinsic matrix.
            dist (np.ndarray): Camera distortion coefficients.
            out_path (str, optional): Path for writing the undistorted image to disk. If out_path is None, undistorted image is not saved to disk. Defaults to None.

        Returns:
            np.ndarray: Undistorted image as a numpy array.
        """

        self.read_image()

        image_und = cv2.undistort(
            cv2.cvtColor(self._value_array, cv2.COLOR_RGB2BGR),
            K,
            dist,
            None,
            K,
        )
        if out_path is not None:
            cv2.imwrite(out_path, image_und)
        return image_und


def read_image_list(
    data_dir: Union[str, Path],
    image_ext: Union[str, List[str]] = None,
    # name_pattern: str = None,
    recursive: bool = False,
    case_sensitive: bool = False,
) -> List[Path]:
    """
    Returns a list of Path objects for all image files in a directory.

    Args:
        data_dir (Union[str, Path]): A string or Path object specifying the directory path containing image files.
        image_ext (Union[str, List[str]], optional): A string or list of strings specifying the image file extensions to search for. Defaults to None, which searches for all file types.
        name_pattern (str, optional): A string pattern to search for within image file names. Defaults to None.
        recursive (bool, optional): Whether to search for image files recursively in subdirectories. Defaults to False.
        case_sensitive (bool, optional): Whether to search for image files with case sensitivity. Defaults to False.

    Returns:
        [Path]: A list of Path objects for all image files found in the specified directory with the specified file extensions and name pattern.

    Raises:
        AssertionError: If the specified directory path is not valid.
        AssertionError: If the specified image extension is not a string or list of strings with three characters each.

    TODO:
        Implement custom name patterns.

    """
    data_dir = Path(data_dir)
    assert (
        data_dir.is_dir()
    ), f"Invalid input '{data_dir}' for data directory. It must be a valid directory path."

    if image_ext is not None:
        msg = "Invalid input for image extension. It must be a 3 characters string without the 'dot' (e.g., 'jpg') or a list of 3 characters strings (e.g., ['jpg', 'png'])"
        assert any([isinstance(image_ext, list), isinstance(image_ext, str)]), msg
        if isinstance(image_ext, str):
            image_ext = [image_ext]
        assert all([len(x) == 3 for x in image_ext]), msg
        if not case_sensitive:
            # Make glob search case-insensitive
            image_ext_lower = [x.lower() for x in image_ext]
            image_ext_upper = [x.upper() for x in image_ext]
            image_ext = image_ext_lower + image_ext_upper

        ext_patt = [f".{x}" for x in image_ext]
    else:
        ext_patt = [""]

    files = []
    for ext in ext_patt:
        if recursive:
            pattern = f"**/*{ext}"
        else:
            pattern = f"*{ext}"
        files.extend(list(data_dir.glob(pattern)))

    files = sorted(files)

    return files


# @TODO: remove variable number of outputs
def read_image(
    path: Union[str, Path],
    color: bool = True,
    resize: List[int] = [-1],
    crop: List[int] = None,
) -> np.ndarray:
    """
    Reads image with OpenCV and returns it as a NumPy array.

    Args:
        path (Union[str, Path]): The path of the image.
        color (bool, optional): Whether to read the image as color (RGB) or grayscale. Defaults to True.
        resize (List[int], optional): If not [-1], image is resized at [width, height] dimensions. Defaults to [-1].
        crop (List[int], optional): If not None, a List containing the bounding box for cropping the image as [xmin, xmax, ymin, ymax]. Defaults to None.

    Returns:
        np.ndarray: The image as a NumPy array.
    """

    if color:
        flag = cv2.IMREAD_COLOR
    else:
        flag = cv2.IMREAD_GRAYSCALE

    try:
        image = cv2.imread(str(path), flag)
    except:
        logging.error(f"Impossible to load image {path}")
        return None, None

    if color:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    if image is None:
        if len(resize) == 1 and resize[0] == -1:
            return None
        else:
            return None, None

    w, h = image.shape[1], image.shape[0]
    w_new, h_new = process_resize(w, h, resize)
    scales = (float(w) / float(w_new), float(h) / float(h_new))
    image = cv2.resize(image, (w_new, h_new))
    if crop:
        image = image[crop[1] : crop[3], crop[0] : crop[2]]

    if len(resize) == 1 and resize[0] == -1:
        return image
    else:
        return image, scales


def process_resize(w, h, resize):
    assert len(resize) > 0 and len(resize) <= 2
    if len(resize) == 1 and resize[0] > -1:
        scale = resize[0] / max(h, w)
        w_new, h_new = int(round(w * scale)), int(round(h * scale))
    elif len(resize) == 1 and resize[0] == -1:
        w_new, h_new = w, h
    else:  # len(resize) == 2:
        w_new, h_new = resize[0], resize[1]
    return w_new, h_new


def read_opencv_calibration(path: Union[str, Path], verbose: bool = False):
    """
    Reads camera internal orientation from a file and returns them. The file must contain the full K matrix and
    distortion vector according to OpenCV standards, and should be organized on one line in the following format:

    width height fx 0. cx 0. fy cy 0. 0. 1. k1 k2 p1 p2 [k3 [k4 k5 k6]]

    All values must be float, and separated by a white space.

    Args:
        path (Union[str, Path]): The path to the calibration file.
        verbose (bool, optional): Prints verbose output. Defaults to False.

    Returns:
        Tuple: Returns a tuple containing:
            - w: width of the calibration image.
            - h: height of the calibration image.
            - K: 3x3 matrix containing the intrinsic camera parameters.
            - dist: distortion parameters.
    Raises:
        ValueError: If the calibration file is not found or if the file is not formatted correctly.
    """
    path = Path(path)
    if not path.exists():
        raise ValueError("Calibration filed does not exist.")
    with open(path, "r") as f:
        data = np.loadtxt(f)
        w = data[0]
        h = data[1]
        K = data[2:11].astype(float).reshape(3, 3, order="C")
        if len(data) == 15:
            if verbose:
                logging.info("Using OPENCV camera model.")
            dist = data[11:15].astype(float)
        elif len(data) == 16:
            if verbose:
                logging.info("Using OPENCV camera model + k3")
            dist = data[11:16].astype(float)
        elif len(data) == 19:
            if verbose:
                logging.info("Using FULL OPENCV camera model")
            dist = data[11:19].astype(float)
        else:
            raise ValueError(
                "Invalid intrinsics data. Calibration file must be formatted as follows:\nwidth height fx 0. cx 0. fy cy 0. 0. 1. k1, k2, p1, p2, [k3, [k4, k5, k6"
            )

    return w, h, K, dist


if __name__ == "__main__":
    # Test ImageList class
    data_dir = "data"
    image_ext = "dng"
    recursive = True
    files = ImageList(data_dir, image_ext=image_ext, recursive=recursive)
    print(files)
