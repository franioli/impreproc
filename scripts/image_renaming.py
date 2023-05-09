from pathlib import Path

import pandas as pd

from impreproc.images import Image, ImageList
from impreproc.rename import ImageRenamer

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
    overlay_name=overlay_name,
    parallel=parallel,
)

# Rename files
dic = renamer.rename()

# Save renaming dictionary
df = pd.DataFrame.from_dict(dic, orient="index")
df.to_csv(dest_folder/"renaming_dict.csv", index=False)


print("Process completed.")