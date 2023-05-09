import re
from pathlib import Path
from typing import TypedDict, Union, List

import numpy as np

from impreproc.images import Image, ImageList
from impreproc.djimrk import mrkread, get_images, merge_mrk_exif_data, project_to_utm

if __name__ == "__main__":
    data_dir = "data/matrice/DJI_202303031031_001"
    mkr_file = "data/matrice/DJI_202303031031_001/DJI_202303031031_001_Timestamp.MRK"
    image_ext = "jpg"

    mrk_dict = mrkread(mkr_file)
    exif_dict = get_images(data_dir, image_ext)
    merged_data = merge_mrk_exif_data(mrk_dict, exif_dict)

    if not project_to_utm(
        epsg_from=4326,
        epsg_to=32632,
        data_dict=merged_data,
        fields=["lat_mrk", "lon_mrk", "ellh_mrk"],
    ):
        raise RuntimeError("Unable to data project to UTM.")

    print("Process completed.")
