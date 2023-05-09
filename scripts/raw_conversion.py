from tqdm import tqdm

from impreproc.images import Image, ImageList
from impreproc.raw_conversion import convert_raw

if __name__ == "__main__":
    # Raw Conversion with Rawtherapee
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
