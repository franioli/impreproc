import logging
import platform
import subprocess
from pathlib import Path
from typing import List, Union

from tqdm import tqdm

from impreproc.images import ImageList


class RawConverter:
    def __init__(
        self,
        image_list: ImageList,
        output_dir: Union[str, Path] = "converted",
        pp3_path: Union[str, Path] = None,
    ):
        self.image_list = image_list
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.pp3_path = pp3_path

    def convert(self, *args) -> bool:
        for file in tqdm(self.image_list):
            if not convert_raw(file, self.output_dir, self.pp3_path, *args):
                raise RuntimeError(f"Unable to convert file {file.name}")
        return True


def find_rawtherapee() -> str:
    # Detect the operating system
    system = platform.system()
    if system == "Linux":
        # Get path to RawTherapee executable
        rawtherapee_path = subprocess.run(
            ["which", "rawtherapee-cli"], capture_output=True, text=True
        ).stdout.replace("\n", "")
        if rawtherapee_path == "":
            import tkinter as tk
            from tkinter import filedialog

            logging.warning(
                "Unable to automatically find RawTherapee executable. Please select it manually."
            )
            root = tk.Tk()
            root.withdraw()
            rawtherapee_path = filedialog.askopenfilename()

    elif system == "Windows":
        import tkinter as tk
        from tkinter import filedialog

        logging.warning(
            "Unable to automatically find RawTherapee executable. Please select it manually."
        )
        root = tk.Tk()
        root.withdraw()
        rawtherapee_path = filedialog.askopenfilename()
    elif system == "Darwin":
        import tkinter as tk
        from tkinter import filedialog

        logging.warning(
            "Unable to automatically find RawTherapee executable. Please select it manually."
        )
        root = tk.Tk()
        root.withdraw()
        rawtherapee_path = filedialog.askopenfilename()
    else:
        raise OSError(f"Unsupported operating system: {system}")

    return rawtherapee_path


def convert_raw(
    fname: Union[str, Path],
    output_path: Union[str, Path] = "converted",
    profile_path: Union[str, Path] = None,
    *args,
) -> bool:
    # Get path to RawTherapee executable (works automatically only on Linux!)
    rawtherapee_path = find_rawtherapee()

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

    # Add additional options specified as **kwargs.
    # **kwargs is a tuple of additonal options as
    # # Rawtherapee options are described at  https://rawpedia.rawtherapee.com/Command-Line_Options
    # e.g., ("-j100", "-js3")
    for arg in args:
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


if __name__ == "__main__":
    pass
