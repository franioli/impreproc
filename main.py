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
from easydict import EasyDict as edict


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
    name_pattern: str = None,
    recursive: bool = False,
    case_sensitive: bool = False,
) -> List[Path]:
    data_dir = Path(data_dir)
    assert data_dir.is_dir(), "Error: invalid image directory."

    if image_ext is not None:
        assert any(
            [isinstance(image_ext, list), isinstance(image_ext, str)]
        ), "Invalid input for image extension. It must be a 3 characters string (e.g., 'jpg') or a list of 3 characters strings (e.g., ['jpg', 'png'])"
        if isinstance(image_ext, str):
            image_ext = [image_ext]
        assert all(
            [len(x) == 3 for x in image_ext]
        ), "Wrong extension input. Please, provide extension with 3 characters only (e.g., jpg)"

        if not case_sensitive:
            # Make glob search case-insensitive
            image_ext_lower = [x.lower() for x in image_ext]
            image_ext_upper = [x.upper() for x in image_ext]
            image_ext = image_ext_lower + image_ext_upper

        ext_patt = [f".{x}" for x in image_ext]
    else:
        ext_patt = [""]

        # ext_patt = ",".join(x for x in image_ext)
        # ext_patt = f"{{{ext_patt}}}"

    files = []
    for ext in ext_patt:
        if recursive:
            pattern = f"**/*{ext}"
        else:
            pattern = f"*{ext}"
        files.extend(list(data_dir.glob(pattern)))

    files = sorted(files)

    return files


if __name__ == "__main__":
    # args = parse_command_line()
    # data_dir = args.data_dir

    data_dir = Path("data")
    image_list = read_image_list(data_dir, image_ext=["jpg", "png"], recursive=True)
