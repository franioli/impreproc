import logging
import shutil

from pathlib import Path
from typing import List, Union

from impreproc.images import Image


def name_from_exif(
    fname: Union[str, Path],
    base_name: str = "IMG",
) -> Path:
    """
    Define new name for an image file based on its exif data.

    Args:
        fname (Union[str, Path]): A string or Path object specifying the file path of the image to rename and copy.
        base_name (str, optional): A string to use as the base name for the renamed image file. Defaults to "IMG".

    Returns:
        Path: New image name as a Pathlib object.

    Raises:
        RuntimeError: If the exif data cannot be read or if the image date-time cannot be retrieved from the exif data.
    """
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
        focal = exif["EXIF FocalLength"].printable
    except:
        logging.warning("Unable to get nominal focal length from exif.")
        focal = ""

    date_time_str = date_time.strftime("%Y%m%d_%H%M%S")
    new_name = f"{base_name}_{date_time_str}_{camera_model}{fname.suffix}"

    return new_name


def rename_image(
    fname: Union[str, Path],
    dest_folder: Union[str, Path] = "renamed",
    base_name: str = "IMG",
    delete_original: bool = False,
) -> bool:
    """
    Renames an image file based on its exif data and copies it to a specified destination folder.

    Args:
        fname (Union[str, Path]): A string or Path object specifying the file path of the image to rename and copy.
        dest_folder (Union[str, Path], optional): A string or Path object specifying the destination directory path to copy the renamed image to. Defaults to "renamed".
        base_name (str, optional): A string to use as the base name for the renamed image file. Defaults to "IMG".
        delete_original (bool, optional): Whether to delete the original image file after copying the renamed image. Defaults to False.

    Returns:
        bool: Returns True if the image was successfully renamed and copied to the destination folder.

    Raises:
        RuntimeError: If the exif data cannot be read or if the image date-time cannot be retrieved from the exif data.
    """
    fname = Path(fname)
    dest_folder = Path(dest_folder)
    dest_folder.mkdir(exist_ok=True, parents=True)

    new_name = name_from_exif(fname=fname, base_name=base_name)

    # Do actual copy
    dst = dest_folder / new_name
    shutil.copyfile(src=fname, dst=dst)

    # If delete_original is set to True, delete original image
    if delete_original:
        fname.unlink()

    return True
