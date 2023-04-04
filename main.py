import argparse
import logging
import multiprocessing
import shutil
import sys
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import List, Union

from easydict import EasyDict as edict
from tqdm import tqdm

from lib.images import Image


def parse_command_line() -> edict:
    """
    parse_command_line Parse command line input

    """
    parser = argparse.ArgumentParser(
        description="""Rename batch of images recursively. Check -h or --help for options.
        Usage: ./main.py /path/to/images -e jpg,png -r -p *_image*"""
    )
    parser.add_argument(
        "data_dir",
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
        "-o",
        "--output_folder",
        type=str,
        default="renamed",
        help="Destination folder for renamed images (default: 'renamed')",
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
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        default=False,
        help="Search for images recursively in subdirectories (default: False)",
    )
    parser.add_argument(
        "-d",
        "--delete_original",
        action="store_true",
        help="Remove original image after renaming (default: False)",
    )
    parser.add_argument(
        "-cs",
        "--case_sensitive",
        action="store_true",
        default=True,
        help="Make glob search case-sensitive (default: True)",
    )
    parser.add_argument(
        "-par",
        "--parallel",
        action="store_true",
        default=False,
        help="Flag to process images in parallel using multiprocessing (default: False)",
    )

    args = parser.parse_args()

    opt = edict(
        {
            "data_dir": Path(args.data_dir),
            "image_ext": None if args.image_ext is None else args.image_ext.split(","),
            "dest_folder": Path(args.output_folder),
            "recursive": args.recursive,
            "name_pattern": args.name_pattern,
            "base_name": args.base_name,
            "delete_original": args.delete_original,
            "case_sensitive": args.case_sensitive,
            "parallel": args.parallel,
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

    # If delete_original is set to True, delete original image
    if delete_original:
        fname.unlink()

    return True


def main(opt: edict) -> bool:
    files = read_image_list(
        opt.data_dir, image_ext=opt.image_ext, recursive=opt.recursive
    )

    if opt.parallel:
        start_time = time.time()
        with multiprocessing.Pool() as p:
            func = partial(
                rename_image,
                dest_folder=opt.dest_folder,
                base_name=opt.base_name,
                delete_original=opt.delete_original,
            )
            list(tqdm(p.imap(func, files)))
        print(f"Elapsed time: {time.time() - start_time} seconds")

    else:
        start_time = time.time()
        for file in tqdm(files):
            if not rename_image(
                fname=file,
                dest_folder=opt.dest_folder,
                base_name=opt.base_name,
                delete_original=opt.delete_original,
            ):
                raise RuntimeError(f"Unable to rename file {file.name}")
        print(f"Elapsed time: {time.time() - start_time} seconds")

    return True


if __name__ == "__main__":
    custom_opts = edict(
        {
            "data_dir": Path("data"),
            "image_ext": ["jpg"],
            "dest_folder": "renamed",
            "base_name": "IMG",
            "recursive": True,
            "name_pattern": None,
            "delete_original": False,
            "parallel": True,
        }
    )

    # Check if script is launched via command-line and parse input parametrs, use custom_opts specified prev otherwise
    if len(sys.argv) > 1:
        opt = parse_command_line()
    else:
        opt = custom_opts

    if not main(opt):
        raise RuntimeError("Process failed unexpectedly.")

    print("Process completed.")
