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
data_dir = Path("data/renaming/matrice/DJI_202303031031_001")
image_ext = ["jpg"]
dest_folder = Path("res/preview")
base_name = "IMG"
recursive = False
delete_original = False
overlay_name = True
parallel = False

# get only images from P1
files = ImageList(
    data_dir=data_dir,
    image_ext=image_ext,
    recursive=recursive,
)


# id = 0
# img = Image(files[id])
# exif = img.exif
# K = img.get_intrinsics_from_exif()

calib_path = "data/dji_p1_voltaMant2023_opencv.xml"
path = Path(calib_path)
assert Path(path).suffix == ".xml", "File must be .xml"

w, h, K, dist = Calibration.read_agisoft_xml_opencv(path)
# w, h, K, dist = Calibration.get_intrinsics_from_exif(exif)
cam = Camera(w, h, K, dist)


from impreproc.renaming import make_previews

file = files[0]

make_previews()

print("done")
