import argparse
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Union
import sys

from easydict import EasyDict as edict

from lib.images import Image


def parse_command_line() -> edict:
    """
    parse_command_line Parse command line input

    """
    parser = argparse.ArgumentParser(
        description="""Rename batch of images recursively. Check -h or --help for options.
        Usage: ./main.py -d /path/to/images -e jpg,png -r -p *_image*"""
    )
    parser.add_argument(
        "-d",
        "--data_dir",
        type=str,
        help="Path to root directory containing images",
    )
    parser.add_argument(
        "-e",
        "--image_ext",
        type=str,
        help="Image file extensions, separated by commas (e.g., jpg,png)",
    )
    parser.add_argument(
        "-f",
        "--dest_folder",
        type=str,
        default="renamed",
        help="Destination folder for renamed images",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        default=False,
        help="Search for images recursively in subdirectories",
    )
    parser.add_argument(
        "-p",
        "--name_pattern",
        type=str,
        default=None,
        help="File name pattern to match (e.g., *_image*)",
    )
    parser.add_argument(
        "-b",
        "--base_name",
        type=str,
        default="IMG",
        help="Base name for renamed images (default: 'IMG')",
    )

    args = parser.parse_args()

    opt = edict(
        {
            "data_dir": Path(args.data_dir),
            "image_ext": None if args.image_ext is None else args.image_ext.split(","),
            "dest_folder": Path(args.dest_folder),
            "recursive": args.recursive,
            "pattern": args.pattern,
            "base_name": args.base_name,
        }
    )

    return opt


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
    assert data_dir.is_dir(), "Error: invalid image directory."

    if image_ext is not None:
        msg = "Invalid input for image extension. It must be a 3 characters string (e.g., 'jpg') or a list of 3 characters strings (e.g., ['jpg', 'png'])"
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


def rename_image(
    fname: Union[str, Path],
    dest_folder: Union[str, Path] = "renamed",
    base_name: str = "IMG",
    remove_original: bool = False,
) -> bool:
    """
    Renames an image file based on its exif data and copies it to a specified destination folder.

    Args:
        fname (Union[str, Path]): A string or Path object specifying the file path of the image to rename and copy.
        dest_folder (Union[str, Path], optional): A string or Path object specifying the destination directory path to copy the renamed image to. Defaults to "renamed".
        base_name (str, optional): A string to use as the base name for the renamed image file. Defaults to "IMG".
        remove_original (bool, optional): Whether to delete the original image file after copying the renamed image. Defaults to False.

    Returns:
        bool: Returns True if the image was successfully renamed and copied to the destination folder.

    Raises:
        RuntimeError: If the exif data cannot be read or if the image date-time cannot be retrieved from the exif data.
    """
    fname = Path(fname)
    dest_folder = Path(dest_folder)
    dest_folder.mkdir(exist_ok=True, parents=True)

    img = Image(fname)

    try:
        exif = img.exif
    except:
        raise RuntimeError("Unable to read exif data")
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

    # Do actual copy
    dst = dest_folder / new_name
    shutil.copyfile(src=fname, dst=dst)

    # If remove_original is set to True, delete original image
    if remove_original:
        fname.unlink()

    return True


if __name__ == "__main__":
    custom_opts = edict(
        {
            "data_dir": Path("data"),
            "image_ext": ["jpg", "png"],
            "dest_folder": "renamed",
            "base_name": "IMG",
            "recursive": True,
            "pattern": None,
        }
    )

    # Check if script is launched via command-line and parse input parametrs, use custom_opts specified prev otherwise
    if len(sys.argv) > 1:
        opt = parse_command_line()
    else:
        opt = custom_opts

    data_dir = opt.data_dir
    image_ext = opt.image_ext
    dest_folder = opt.dest_folder
    recursive = opt.recursive
    pattern = opt.pattern
    base_name = opt.base_name

    image_list = read_image_list(data_dir, image_ext=image_ext, recursive=recursive)
    for file in image_list:
        if not rename_image(fname=file, dest_folder=dest_folder, base_name=base_name):
            raise RuntimeError(f"Unable to rename file {file.name}")

    print("Done.")
