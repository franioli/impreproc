import argparse
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Union

import exifread
import numpy as np
import PIL
from PIL import Image
from easydict import EasyDict as edict

from lib.images import Image


def parse_command_line() -> edict:
    """
    parse_command_line Parse command line input

    """
    parser = argparse.ArgumentParser(
        description="""icepy
            Low-cost stereo photogrammetry for 4D glacier monitoring \
            Check -h or --help for options.
        Usage: ./main.py -c config_base.yaml"""
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        help="Path of to root directory containing images",
    )

    # if not len(sys.argv) > 1:
    #     raise ValueError(
    #         "Not enough input arguments. Specify at least the configuration file. Use --help (or -h) for help."
    #     )

    args = parser.parse_args()

    opt = edict({"data_dir": Path(args.directory)})

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


def rename_image(fname: Union[str, Path]) -> bool:
    img = Image(fname)

    return True


if __name__ == "__main__":
    # args = parse_command_line()
    # data_dir = args.data_dir

    data_dir = Path("data")
    image_list = read_image_list(data_dir, image_ext=["jpg", "png"], recursive=True)

    fname = image_list[0]
    img = Image(fname)

    # img = Image.open(fname)
    # exif = img.getexif()

    # with open(fname, "rb") as f:
    #     exif = exifread.process_file(f, details=False)

    print("Done.")
