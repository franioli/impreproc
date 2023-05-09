import multiprocessing
import time
from functools import partial
from pathlib import Path

from easydict import EasyDict as edict
from tqdm import tqdm

from impreproc.images import ImageList, Image
from impreproc.raw_conversion import convert_raw
from impreproc.rename import rename_image


def main(opt: edict) -> bool:
    files = ImageList(opt.data_dir, image_ext=opt.image_ext, recursive=opt.recursive)

    if opt.parallel:
        start_time = time.time()
        func = partial(
            rename_image,
            dest_folder=opt.dest_folder,
            base_name=opt.base_name,
            delete_original=opt.delete_original,
        )
        with multiprocessing.Pool() as p:
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
    # Run image renaming
    # custom_opts = edict(
    #     {
    #         "data_dir": Path("data/mantova"),
    #         "image_ext": ["dng"],  # ["jpg"]
    #         "dest_folder": Path("converted"),
    #         "base_name": "IMG",
    #         "recursive": True,
    #         "name_pattern": None,
    #         "delete_original": False,
    #         "parallel": True,
    #     }
    # )

    # # Check if script is launched via command-line and parse input parametrs, use custom_opts specified prev otherwise
    # if len(sys.argv) > 1:
    #     opt = utils.parse_command_line()
    # else:
    #     opt = custom_opts

    # Batch name renaming
    # main(opt)

    # Conversion
    data_dir = "/mnt/labmgf/2023/Volta_Mantovana_UniMI/IMG/P1/DJI_202303301417_002/raw/"
    image_ext = "dng"
    output_dir = "/mnt/p/voltamantovana2023/img"
    recursive = False
    pp3_path = "data/dji_p1_lightContrast_amaze0px.pp3"
    rawtherapee_opts = ("-j100", "-js3", "-Y")

    # Get list of files
    files = ImageList(data_dir, image_ext=image_ext, recursive=recursive)

    # Build Image object to extract exif data
    img = Image(files[0])
    exif = img.exif

    # Convert raw files
    # ret = convert_raw(files[0], pp3_path, "-j100", "-js3", "-Y")
    for file in tqdm(files):
        if not convert_raw(file, output_dir, pp3_path, *rawtherapee_opts):
            raise RuntimeError(f"Unable to convert file {file.name}")

    print("Process completed.")
