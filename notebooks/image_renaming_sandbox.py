import logging
from importlib import import_module
from pathlib import Path
from typing import List, Union

import numpy as np
import pandas as pd

from impreproc.camera import Calibration, Camera
from impreproc.images import Image, ImageList
from impreproc.renaming import ImageRenamer

# Define parameters
data_dir = Path("data/renaming")
image_ext = ["jpg"]
dest_folder = Path("res/renamed")
base_name = "IMG"
recursive = True
delete_original = False
overlay_name = True
parallel = True

# Get list of files
files = ImageList(data_dir, image_ext=image_ext, recursive=recursive)

imid = 6
fname = files[imid]

img = Image(fname)
exif = img.exif

from PIL import Image as PILImage
import PIL.ExifTags

img = PILImage.open(fname)

exif = {
    PIL.ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in PIL.ExifTags.TAGS
}


exif_data = img.getexif()

import exiftool

with exiftool.ExifToolHelper() as et:
    metadata = et.get_metadata(fname)
    for d in metadata:
        print("{:20.20} {:20.20}".format(d["SourceFile"],
                                         d["EXIF:DateTimeOriginal"]))


# Create ImageRenamer object
renamer = ImageRenamer(
    image_list=files,
    dest_folder=dest_folder,
    base_name=base_name,
    delete_original=delete_original,
    parallel=parallel,
    prior_class_file=data_dir / "prior_classes.csv",
)

# Rename files and get Pandas Dataframe with old and new names
df = renamer.rename()
renamer.make_previews(dest_folder / "previews")

# Save Pandas Dataframe as .csv and .parquet file
df.to_csv(dest_folder / "renaming_dict.csv")
df.to_parquet(dest_folder / "renaming_dict.parquet")
