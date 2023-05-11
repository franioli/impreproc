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

# Test for img calibration


id = 0
img = Image(files[id])
exif = img.exif
K = img.get_intrinsics_from_exif()


path = "data/d800_opencv.xml"
path = Path(path)
assert Path(path).suffix == ".xml", "File must be .xml"

calib = Calibration()
cam = calib.camera_from_file(filename=path)
print(cam)

w, h, K, dist = Calibration.read_agisoft_xml_opencv(path)
print(w, h, K, dist)

w, h, K, dist = Calibration.get_intrinsics_from_exif(exif)
print(w, h, K, dist)
