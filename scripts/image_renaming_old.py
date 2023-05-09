import multiprocessing
import sys
import time
from functools import partial
from pathlib import Path

from easydict import EasyDict as edict
from tqdm import tqdm

from impreproc import utils
from impreproc.images import Image, ImageList
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
    # Image renaming
    opt = edict(
        {
            "data_dir": Path("data/renaming"),
            "image_ext": ["jpg"],
            "dest_folder": Path("res/renamed"),
            "base_name": "IMG",
            "recursive": True,
            "name_pattern": None,
            "delete_original": False,
            "parallel": False,
        }
    )

    # Batch name renaming
    main(opt)

    print("Process completed.")
