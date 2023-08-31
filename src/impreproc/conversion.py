import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import List, Union

from tqdm import tqdm

from impreproc.images import ImageList


class RawConverter:
    """
    A class for converting a list of raw image files to JPEG or other formats
    using RawTherapee command line interface.

    Args:
        image_list (ImageList): A list of paths to raw image files.
        output_dir (Union[str, Path], optional): The directory where the converted images will be saved. Defaults to "./converted".
        pp3_path (Union[str, Path], optional): The path to a pp3 file containing processing instructions for RawTherapee. Defaults to None.
        keep_dir_tree (bool, optional): A flag indicating whether to preserve the directory structure of the input files in the output directory. If True, the converted images will be saved in subdirectories of the output directory corresponding to the relative paths of the input files. Defaults to False.

    Examples:
        To convert a list of raw images to JPEG format with default parameters and save them in the "converted":
        >>> from pathlib import Path
        >>> from impreproc.raw_conversion import RawConverter
        >>> image_list = ImageList("path/to/raw/images", image_ext = "DNG")
        >>> converter = RawConverter(image_list, output_dir="converted")
        >>> converter.convert()

        To preserve the directory structure of the input files in the output directory, use the following code:
        >>> converter = RawConverter(image_list, output_dir="converted", keep_dir_tree=True)
        >>> converter.convert()

        To add a processing profile to the conversion, use the following code:
        >>> converter = RawConverter(image_list, output_dir="converted", pp3_path="path/to/pp3_profile.pp3")
        >>> converter.convert()

        To add additional parameters to RawTherapee, use the following code. See the documentation of convert_raw function for all the details.
        >>> converter = RawConverter(image_list, output_dir="converted", pp3_path="path/to/pp3_profile.pp3")
        >>> converter.convert("-j100", "-js3", "-Y")

    """

    def __init__(
        self,
        output_dir: Union[str, Path] = "./converted",
        pp3_path: Union[str, Path] = None,
        opts: List[str] = [],
        keep_dir_tree: bool = False,
        image_list: ImageList = None,
    ):
        """
        Initializes the RawConverter object.

        Args:
            output_dir (Union[str, Path], optional): The directory where the converted images will be saved. Defaults to "converted".
            pp3_path (Union[str, Path], optional): The path to a pp3 file containing processing instructions for RawTherapee. Defaults to None.
            keep_dir_tree (bool, optional): A flag indicating whether to preserve the directory structure of the input files in the output directory. If True, the converted images will be saved in subdirectories of the output directory corresponding to the relative paths of the input files. Defaults to False.
            image_list (ImageList): A list of paths to raw image files. Defaults to None.
            opts: Additional options to pass to RawTherapee, e.g. ("-j100", "-Y"). See the documentation of convert_raw function for all the details.

        NOTE:
            image_list shuld be set only in convert method. Kept int __init__ for backward compatibility.
        """
        self.output_dir = Path(output_dir)
        self.pp3_path = pp3_path
        self.keep_dir_tree = keep_dir_tree
        self.opts = opts
        self.image_list = image_list

        if self.output_dir.exists():
            logging.warning(
                f"Destination folder {self.output_dir} already exists. Existing files may be overwritten."
            )
        else:
            self.output_dir.mkdir(parents=True)

    def convert(
        self,
        image_list: ImageList,
    ) -> bool:
        """
        Converts the raw image files to the specified format using RawTherapee.

        Args:
            image_list (ImageList): A list of paths to raw image files.

        Returns:
            bool: True if all files were converted successfully, False otherwise.
        """
        self.image_list = image_list

        if not self.keep_dir_tree:
            for file in tqdm(self.image_list):
                if not convert_raw(
                    file,
                    output_path=self.output_dir,
                    profile_path=self.pp3_path,
                    opts=self.opts,
                ):
                    raise RuntimeError(f"Unable to convert file {file.name}")
        else:
            dest_paths = rebuild_dir_tree(self.image_list, self.output_dir)
            for file, dest in tqdm(zip(self.image_list, dest_paths)):
                dest.mkdir(parents=True, exist_ok=True)
                if not convert_raw(
                    file, output_path=dest, profile_path=self.pp3_path, opts=self.opts
                ):
                    raise RuntimeError(f"Unable to convert file {file.name}")
        return True


def convert_raw(
    fname: Union[str, Path],
    output_path: Union[str, Path] = "converted",
    profile_path: Union[str, Path] = None,
    rawtherapee_path: Union[str, Path] = None,
    opts: List[str] = [],
) -> bool:
    """
    Converts a raw image file to a specified format using RawTherapee.

    Args:
        fname (Union[str, Path]): Path to the raw image file to convert.
        output_path (Union[str, Path], optional): Directory to save the converted file(s). Defaults to "converted" in the current working directory.
        profile_path (Union[str, Path], optional): Path to a processing profile (pp3) file to use for the conversion. Defaults to None.
        opts: Additional string arguments to pass to RawTherapee. A comprehensive list of possible arguments can be found in the RawTherapee documentation at https://rawpedia.rawtherapee.com/Command-Line_Options

    Returns:
        bool: True if the conversion was successful, False otherwise.

    Examples:
        To convert a raw image file named 'my_raw_image.CR2' to JPEG format with 90% compression, apply a processing profile saved in a file called 'my_profile.pp3' and save it to a directory called 'my_images', use the following command:

            >>> convert_raw('my_raw_image.CR2', output_path='my_images', profile_path='my_profile.pp3', '-j90' )

        To convert a raw image file named 'my_raw_image.CR2' to 16 bit TIF format and apply a processing profile saved in a file called 'my_profile.pp3', use the following command:

            >>> convert_raw('my_raw_image.CR2', output_path='my_images', profile_path='my_profile.pp3', '-t16')

        To convert a raw image file named 'my_raw_image.CR2' to 8bit TIF format, use:

            >>> convert_raw('my_raw_image.CR2', output_path='my_images', profile_path='my_profile.pp3', '-t', '-b8')

        To specify the JPEG chroma subsampling parameter, where 1=Best compression, 2=Balanced, 3= Best quality, use:

            >>> convert_raw('my_raw_image.CR2', output_path='my_images', profile_path='my_profile.pp3', '-j90', '-js3' )

        To force overwrite output if presen:

            >>> convert_raw('my_raw_image.CR2', output_path='my_images', profile_path='my_profile.pp3', '-j90', '-Y')

    """
    # Get path to RawTherapee executable (works automatically only on Linux!)
    if rawtherapee_path is None:
        rawtherapee_path = find_rawtherapee()
    else:
        assert Path(rawtherapee_path).exists(), "Invalid RawTherapee Path"

    Path(output_path).mkdir(exist_ok=True)

    # Define base command
    cmd = [
        rawtherapee_path,
        "-o",
        str(output_path),
    ]

    # Add option for processing a pp3 profile
    if profile_path is not None:
        assert Path(
            profile_path
        ).exists(), f"Input profile {profile_path} does not exist"
        cmd.append("-p")
        cmd.append(profile_path)

    # Add additional options specified as a tuple of additonal options as
    # Rawtherapee options are described at  https://rawpedia.rawtherapee.com/Command-Line_Options
    # e.g., ("-j100", "-js3")
    for arg in opts:
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


def rebuild_dir_tree(file_list: List[Path], dest_dir: Path) -> List[Path]:
    """Rebuilds the directory tree of a list of files in a new location.

    Given a list of file paths and a destination directory, this function extracts the relative path of each file in the list relatively to the common path to all files, and uses the relative path extracted to build a new path for copying the files maintaining the same directory tree but in the new location.
    If the path is not found automatically, a file dialog window will open to allow the user to select the executable manually.

    Args:
        file_list (List[Path]): A list of Path objects representing the paths to the files to be copied.
        dest_dir (Path): A Path object representing the destination directory.

    Returns:
        List[Path]: A list of Path objects representing the new paths of the copied files, with the same directory tree as
        in the original location."""
    system = platform.system()
    if system == "Linux" or system == "Darwin":
        paths = [f.resolve() for f in file_list]
    elif system == "Windows":
        paths = [Path(f).resolve() for f in file_list]
    root = os.path.commonpath(paths)
    dest_paths = [Path(dest_dir) / f.relative_to(root).parent for f in paths]
    return dest_paths


def find_rawtherapee() -> str:
    """
    Find the path of the RawTherapee executable on the current operating system.
    If the path is not found automatically, a file dialog window will open to allow the user to select the executable manually.

    Returns:
        str: Path to RawTherapee executable

    Raises:
        OSError: If the operating system is not supported
    """

    def select_path_gui():
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename()
        return path

    # Detect the operating system
    system = platform.system()
    if system == "Linux":
        # Get path to RawTherapee executable
        rawtherapee_path = subprocess.run(
            ["which", "rawtherapee-cli"], capture_output=True, text=True
        ).stdout.replace("\n", "")
        if rawtherapee_path == "":
            logging.warning(
                "Unable to automatically find RawTherapee executable. Please select it manually."
            )
            rawtherapee_path = select_path_gui()

    elif system == "Windows":
        try:
            rawtherapee_path = Path(
                "C://Program Files//RawTherapee//5.8//rawtherapee-cli.exe"
            )
            assert (
                rawtherapee_path.exists()
            ), "Rawtherapee not found in default windows path. Select the location of the rawtherapee-cli.exe exectutable manually."
        except AssertionError:
            logging.warning(
                "Unable to automatically find RawTherapee executable. Please select it manually."
            )
            rawtherapee_path = select_path_gui()

    elif system == "Darwin":
        logging.warning(
            "Unable to automatically find RawTherapee executable. Please select it manually."
        )
        rawtherapee_path = select_path_gui()

    else:
        raise OSError(f"Unsupported operating system: {system}")

    return rawtherapee_path


if __name__ == "__main__":
    path = find_rawtherapee()
    print(path)

    data_dir = "./data/conversion/"
    image_ext = "DNG"
    output_dir = "./data/converted"
    pp3_path = "./data/conversion/dji_p1_lightContrast_amaze0px.pp3"
    recursive = True
    keep_dir_tree = True
    rawtherapee_opts = ("-j100", "-js3", "-Y")

    files = ImageList(data_dir, image_ext=image_ext, recursive=recursive)
    print(files.head)

    # ret = convert_raw(files[0], output_dir, pp3_path)

    # Batch convert images with RawConverter class
    converter = RawConverter(
        output_dir=output_dir,
        pp3_path=pp3_path,
        keep_dir_tree=keep_dir_tree,
        opts=rawtherapee_opts,
    )
    converter.convert(files)
