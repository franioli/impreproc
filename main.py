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
import subprocess

from easydict import EasyDict as edict
from tqdm import tqdm

from impreproc.images import ImageList, Image
from impreproc.parser import parse_command_line


def make_new_name():
    pass


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


def convert_raw(
    fname: Union[str, Path],
    output_dir: Union[str, Path] = None,
    profile_path: Union[str, Path] = None,
    *args,
) -> bool:
    # Get path to RawTherapee executable (works only on Linux!)
    rawtherapee_path = subprocess.run(
        ["which", "rawtherapee-cli"], capture_output=True, text=True
    ).stdout.replace("\n", "")

    Path(output_dir).mkdir(exist_ok=True)

    # Define base command
    cmd = [
        rawtherapee_path,
        "-o",
        str(output_dir),
    ]

    # Add option for processing a pp3 profile
    if profile_path is not None:
        assert Path(
            profile_path
        ).exists(), f"Input profile {profile_path} does not exist"
        cmd.append("-p")
        cmd.append(profile_path)

    # Add additional options specified as **kwargs.
    # **kwargs is a tuple of additonal options as
    # # Rawtherapee options are described at  https://rawpedia.rawtherapee.com/Command-Line_Options
    # e.g., ("-j100", "-js3")
    for arg in args:
        cmd.append(arg)

    # Add input file as last parameter
    cmd.append("-c")
    cmd.append(str(fname))

    # Run Conversion with RawTherapee
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if res.returncode == 0:
        return True
    else:
        return False


def main(opt: edict) -> bool:
    files = ImageList(opt.data_dir, image_ext=opt.image_ext, recursive=opt.recursive)

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
            "data_dir": Path("data/mantova"),
            "image_ext": ["dng"],  # ["jpg"]
            "dest_folder": Path("converted"),
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

    # if not main(opt):
    #     raise RuntimeError("Process failed unexpectedly.")

    # Test new class
    data_dir = "data/mantova"
    image_ext = "dng"
    output_dir = "converted"
    recursive = False
    files = ImageList(data_dir, image_ext=image_ext, recursive=recursive)

    # Conversion
    data_dir = "/mnt/labmgf/2023/Volta_Mantovana_UniMI/IMG/P1/DJI_202303301417_002/raw/"
    image_ext = "dng"
    output_dir = "/mnt/p/voltamantovana2023/img"
    recursive = False
    pp3_path = "data/dji_p1_lightContrast_amaze0px.pp3"
    rawtherapee_opts = ("-j100", "-js3", "-Y")

    files = ImageList(data_dir, image_ext=image_ext, recursive=recursive)
    # files = read_image_list(data_dir, image_ext=image_ext, recursive=recursive)

    # ret = convert_raw(files[0], pp3_path, "-j100", "-js3", "-Y")

    for file in tqdm(files):
        if not convert_raw(file, output_dir, pp3_path, *rawtherapee_opts):
            raise RuntimeError(f"Unable to convert file {file.name}")

    print("Process completed.")
