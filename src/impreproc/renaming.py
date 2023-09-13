import logging
import multiprocessing
import shutil
from functools import partial
from pathlib import Path
from typing import List, Tuple, TypedDict, Union

import cv2
import numpy as np
import pandas as pd
from tqdm import tqdm

# NOTE: Only for make previews. It should be loaded only if needed.
from impreproc.camera import Camera
from impreproc.images import Image, ImageList, latlonalt_from_exif


class RenamingDict(TypedDict):
    """A dictionary for storing metadata about an image being renamed. It maps the old image name to the new one and stores additional metadata about the image.

    Fields:
    old_name (str): The original name of the image file.
    new_name (str): The new name of the image file.
    date (str): The date the image was taken in the format YYYY:MM:DD.
    time (str): The time the image was taken in the format HH:MM:SS.
    camera (str): The camera model that captured the image.
    focal (float): The focal length of the lens that captured the image.
    GPSlat (float): The latitude of the location where the image was taken.
    GPSlon (float): The longitude of the location where the image was taken.
    GPSh (float): The altitude of the location where the image was taken.
    classification (int or None): The classification of the image, if applicable.
    """

    id: int
    old_name: str
    new_name: str
    date: str
    time: str
    camera: str
    focal: float
    GPSlat: float
    GPSlon: float
    GPSh: float
    classification: Union[int, None]


class ImageRenamer:
    """
    A class for renaming a list of images.

    Args:
        image_list (ImageList): A list of images to be renamed.
        dest_folder (Union[str, Path], optional): The destination folder where the renamed images will be saved. Defaults to "renamed".
        base_name (str, optional): The base name for the renamed images. Defaults to "IMG".
        prior_class_file (Union[str, Path], optional): A CSV file containing prior classification data. Defaults to None.
        delete_original (bool, optional): Whether to delete the original image after renaming. Defaults to False.
        parallel (bool, optional): Whether to use multiprocessing for faster renaming. Defaults to False.

    Attributes:
        renaming_dict (dict): A dictionary of the old and new names, if build_dictionary is set to True.

    Methods:
        rename(self) -> pd.DataFrame:
            Renames the images from EXIF data. Returns a Pandas dataframe mapping the old to the new ones, and adding additional information from EXIF and, if provided, prior classification of the images.

            Returns:
                pd.DataFrame: A dataframe mapping the old names to new ones and containing additional information from EXIF and, if provided, prior classification of the images.

            Raises:
                RuntimeError: If an error occurs while renaming an image.

        make_previews(self, dest_folder, preview_size=None, **kwargs) -> None:
            Creates a preview image for each renamed image, using the `make_previews` function with the specified parameters. The previews will be saved in the specified `dest_folder`.

            Args:
                dest_folder (Union[str, Path]): The destination folder for the preview images.
                preview_size (Union[int, Tuple[int, int]], optional): The size of the preview image. Defaults to None.                **kwargs: Additional arguments to be passed to `make_previews`.
    """

    def __init__(
        self,
        image_list: ImageList,
        dest_folder: Union[str, Path] = "renamed",
        base_name: str = "IMG",
        progressive_ids: bool = False,
        # overlay_name: bool = False,
        prior_class_file: Union[str, Path] = None,
        delete_original: bool = False,
        parallel: bool = False,
    ) -> None:
        """Initializes the ImageRenamer class.

        Args:
            image_list (ImageList): A list of paths to the images to be renamed.
            dest_folder (Union[str, Path], optional): The destination folder for the renamed images. Defaults to "renamed".
            base_name (str, optional): The base name for the renamed images. Defaults to "IMG".
            prior_class_file (Union[str, Path], optional): A CSV file containing prior classification data. Defaults to None.
            delete_original (bool, optional): Whether to delete the original images after renaming. Defaults to False.
            parallel (bool, optional): Whether to use multiprocessing. Defaults to False.
        """
        self.image_list = image_list
        self.dest_folder = Path(dest_folder)
        self.base_name = base_name
        self.progressive_ids = progressive_ids
        self.delete_original = delete_original
        self.parallel = parallel

        if self.progressive_ids and self.parallel:
            logging.warning(
                "Unable to do parallel renaming with progressive id.Running renaming in a single process"
            )
            self.parallel = False

        if self.dest_folder.exists():
            logging.warning(
                f"Destination folder {self.dest_folder} already exists. Existing files may be overwritten."
            )
        else:
            self.dest_folder.mkdir(parents=True)

        self.prior_class = None
        if prior_class_file is not None:
            try:
                self.prior_class = pd.read_csv(
                    prior_class_file, names=["name", "class"], header=None
                )
            except:
                logging.warning(
                    f"Unable to read prior class file {prior_class_file}. It must be a two column csv file with the first column containing the image name and the second column containing the class as integer values. No header should be present."
                )

    def rename(self) -> pd.DataFrame:
        """
        Rename the images in `self.image_list`, applying the `copy_and_rename_overlay` function with the specified parameters
        to each image. Return a dictionary mapping the original index of each image in `self.image_list` to its new name
        generated by `copy_and_rename_overlay`.

        Returns:
            A Pandas Dataframe mapping old names of the images with the new ones and adding additional information from exif and, if given as input, prior classification of the images.

        Raises:
            RuntimeError: If an error occurs while renaming an image.

        """
        func = partial(
            copy_and_rename,
            dest_folder=self.dest_folder,
            base_name=self.base_name,
            delete_original=self.delete_original,
        )
        if self.parallel:
            with multiprocessing.Pool() as p:
                out = list(tqdm(p.imap(func, self.image_list)))
            renaming_dict = {k: v for k, v in enumerate(out)}

        else:
            renaming_dict = {}
            for i, file in enumerate(tqdm(self.image_list)):
                if self.progressive_ids:
                    renaming_dict[i] = func(file, progressive_id=i)
                else:
                    renaming_dict[i] = func(file)

        self.renaming_df = pd.DataFrame.from_dict(renaming_dict, orient="index")

        if self.prior_class is not None:
            try:
                self.renaming_df = pd.merge(
                    self.renaming_df,
                    self.prior_class,
                    how="left",
                    left_on="old_name",
                    right_on="name",
                )
                self.renaming_df.drop(["classification", "name"], axis=1, inplace=True)
                self.renaming_df.rename(
                    {
                        "class": "classification",
                    },
                    inplace=True,
                    axis=1,
                )
            except:
                logging.warning("Unable to merge prior class file with renaming dict.")

        return self.renaming_df

    def make_previews(
        self,
        dest_folder: Union[str, Path] = "previews",
        resize_factor: float = -1,
        preview_size=None,
        **kwargs,
    ) -> None:
        """
        Create preview images for all images in the ImageList object.

        Args:
            dest_folder (Union[str, Path], optional): The destination folder where preview images will be saved.
            preview_size (float, optional): The size of the preview image. Defaults to None.
            **kwargs (dict): Additional keyword arguments passed to the `make_previews` function.

        Returns:
            None

        Raises:
            RuntimeError: If unable to rename a file.

        """

        if dest_folder is "previews":
            dest_folder = self.dest_folder / "previews"
        else:
            dest_folder = Path(dest_folder)
        dest_folder.mkdir(parents=True, exist_ok=True)
        func = partial(
            make_previews,
            dest_folder=dest_folder,
            # base_name=self.base_name,
            **kwargs,
        )
        if self.parallel:
            with multiprocessing.Pool() as p:
                list(tqdm(p.imap(func, self.image_list)))

        else:
            for file in tqdm(self.image_list):
                if not func(file):
                    raise RuntimeError(f"Unable to rename file {file.name}")


def name_from_exif(
    fname: Union[str, Path],
    base_name: str = "IMG",
    progressive_id: int = None,
) -> Tuple[str, RenamingDict]:
    fname = Path(fname)
    img = Image(fname)
    exif = img.exif
    date_time = img._date_time
    if date_time is None:
        raise RuntimeError("Unable to get image date-time from exif.")
    try:
        camera_model = exif["Image Model"].printable
        camera_model = camera_model.replace(" ", "_")
    except:
        logging.warning("Unable to get camera model from exif.")
        camera_model = ""
    try:
        focal = float(exif["EXIF FocalLength"].values[0])
    except:
        logging.warning("Unable to get nominal focal length from exif.")
        focal = None
    try:
        lat, lon, h = latlonalt_from_exif(exif)
    except:
        logging.warning(
            f"Unable to get GPS coordinates from exif from image {fname.name}."
        )
        lat, lon, h = None, None, None

    if progressive_id is not None:
        id_str = f"_{str(progressive_id).zfill(4)}"
    else:
        id_str = ""

    date_time_str = date_time.strftime("%Y%m%d_%H%M%S")
    new_name = f"{base_name}{id_str}_{date_time_str}_{camera_model}{fname.suffix}"

    dic = RenamingDict(
        id=progressive_id,
        old_name=fname.name,
        new_name=new_name,
        date=img.date,
        time=img.time,
        camera=camera_model,
        focal=focal,
        GPSlat=lat,
        GPSlon=lon,
        GPSh=h,
        classification=None,
    )

    return new_name, dic


def copy_and_rename(
    fname: Union[str, Path],
    dest_folder: Union[str, Path] = "renamed",
    base_name: str = "IMG",
    progressive_id: int = None,
    delete_original: bool = False,
) -> bool:
    """
    Renames an image file based on its EXIF data and copies it to a specified destination folder.

    Args:
        fname (Union[str, Path]): A string or Path object specifying the file path of the image to rename and copy.
        dest_folder (Union[str, Path], optional): A string or Path object specifying the destination directory path to copy the renamed image to. Defaults to "renamed".
        base_name (str, optional): A string to use as the base name for the renamed image file. Defaults to "IMG".
        delete_original (bool, optional): Whether to delete the original image file after copying the renamed image. Defaults to False.

    Returns:
        dict: A dictionary containing the extracted EXIF data.

    Raises:
        RuntimeError: If the exif data cannot be read or if the image date-time cannot be retrieved from the exif data.
    """
    fname = Path(fname)

    dest_folder = Path(dest_folder)
    dest_folder.mkdir(exist_ok=True, parents=True)

    # Get new name
    new_name, dic = name_from_exif(
        fname=fname, base_name=base_name, progressive_id=progressive_id
    )

    # Do the copy
    dst = dest_folder / new_name
    shutil.copyfile(src=fname, dst=dst)

    # If requested, delete original
    if delete_original:
        fname.unlink()

    return dic


def make_previews(
    fname: Union[str, Path],
    dest_folder: Union[str, Path] = "previews",
    resize_factor: float = -1,
    resize_to: Union[int, Tuple[int]] = -1,
    undistort: bool = False,
    camera: Camera = None,
    overlay_name: bool = True,
    output_format: str = "jpg",
    **kwargs,
) -> True:
    """
    Make image resized image previews for Potree Viewer and overlaying the image names.

    """

    if camera is not None:
        K = camera.K
        dist = camera.dist

    # Read image
    image = cv2.imread(str(fname))

    # Resize image
    if resize_factor != -1:
        if "interpolation_flag" in kwargs.keys():
            intep_flag = kwargs["interpolation_flag"]
        else:
            intep_flag = cv2.INTER_LINEAR
        image = cv2.resize(
            image, None, fx=resize_factor, fy=resize_factor, interpolation=intep_flag
        )
        if camera is not None:
            K_new = cv2.getOptimalNewCameraMatrix()

    if undistort:
        assert camera is not None, "Camera object must be provided for undistortion."
        dist_ = np.array([x for x in dist if x is not None], dtype=np.float64)
        assert len(dist) in [
            4,
            5,
            8,
            12,
            14,
        ], f"Camera must have 4, 5, 8, 12 or 14 distortion coefficients, as in OpenCV. Got {len(camera.dist)}."
        image = cv2.undistort(image, camera.K, dist, camera.K)

    # Overlay name on image
    if overlay_name:
        image = overlay_text(image=image, text=fname.stem, **kwargs)

    # Write image
    cv2.imwrite(str(dest_folder / f"{fname.stem}.{output_format}"), image)

    return True


def overlay_text(
    image: np.ndarray,
    text: str,
    font_scale: int = 5,
    font_color: Tuple[int, int, int] = (255, 255, 255),
    font_thickness: int = 10,
    border_px: int = 50,
    background_color: Union[Tuple[int, int, int], None] = (255, 255, 255),
    background_buffer: int = 20,
) -> np.ndarray:
    """Overlay text onto an image.

    Args:
        image (np.ndarray): The image onto which the text will be overlaid.
        text (str): The text to be overlaid onto the image.
        font_scale (int, optional): The size of the font for the text. Defaults to 5.
        font_color (Tuple[int, int, int], optional): The color of the text in BGR format. Defaults to (255, 255, 255).
        font_thickness (int, optional): The thickness of the text in pixels. Defaults to 10.
        border_px (int, optional): The number of pixels from the edge of the image to use as a margin for the text. Defaults to 50.
        background_color (Union[Tuple[int, int, int], None], optional): The color of the background behind the text. If None, no background is added. Defaults to (255, 255, 255).
        background_buffer (int, optional): The number of pixels of padding to add around the text when a background is added. Defaults to 20.

    Returns:
        np.ndarray: The modified image with text overlaid.
    """

    DEBUG = False

    h, w, _ = image.shape
    font = cv2.FONT_HERSHEY_SIMPLEX  # cv2.FONT_HERSHEY_DUPLEX
    fontScale = int(font_scale)
    fontColor = tuple(font_color)
    thickness = int(font_thickness)
    text_border = int(font_thickness * 0.8)
    lineType = cv2.LINE_8
    text_size, _ = cv2.getTextSize(text, font, fontScale, thickness)

    bottomLeftCornerOfText = (
        border_px,
        text_size[1] + border_px,
    )

    if DEBUG:
        from copy import deepcopy

        image_bk = deepcopy(image)

    if background_color is not None:
        background_color = tuple(background_color)
        if background_color == (255, 255, 255):
            fontColor = (0, 0, 0)
        elif background_color == (0, 0, 0):
            fontColor = (255, 255, 255)

        pt0 = np.array(bottomLeftCornerOfText).astype(np.int32)
        pt0[1] -= text_size[1]
        pt1 = pt0 + np.array(text_size).astype(np.int32)
        pt0 = np.clip(pt0 - background_buffer, 0, None)
        pt1 = np.clip(pt1 + background_buffer, None, np.array([w, h]))
        image = cv2.rectangle(image, pt0, pt1, background_color, -1)

    # Text border
    cv2.putText(
        image,
        text,
        bottomLeftCornerOfText,
        font,
        fontScale,
        (0,),
        thickness + text_border,
        lineType,
    )
    # Inner text
    cv2.putText(
        image,
        text,
        bottomLeftCornerOfText,
        font,
        fontScale,
        fontColor,
        thickness,
        lineType,
    )

    return image
