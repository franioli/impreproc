from impreproc.images import Image, ImageList
from impreproc.raw_conversion import convert_raw, RawConverter

if __name__ == "__main__":
    # Raw Conversion with Rawtherapee
    data_dir = "data/conversion/mantova"
    image_ext = "dng"
    output_dir = "res/converted"
    recursive = False
    pp3_path = "data/conversion/dji_p1_lightContrast_amaze0px.pp3"
    rawtherapee_opts = ("-j100", "-js3", "-Y")

    # Get list of files
    files = ImageList(data_dir, image_ext=image_ext, recursive=recursive)

    # Convert raw files
    # ret = convert_raw(files[0], pp3_path, "-j100", "-js3", "-Y")
    converter = RawConverter(
        image_list=files,
        output_dir=output_dir,
        pp3_path=pp3_path,
        # *rawtherapee_opts,
    )
    converter.convert(*rawtherapee_opts)

    print("Process completed.")
