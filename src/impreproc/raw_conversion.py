from pathlib import Path
from typing import List, Union
import subprocess


def convert_raw(
    fname: Union[str, Path],
    output_path: Union[str, Path] = None,
    profile_path: Union[str, Path] = None,
    *args,
) -> bool:
    # Get path to RawTherapee executable (works only on Linux!)
    rawtherapee_path = subprocess.run(
        ["which", "rawtherapee-cli"], capture_output=True, text=True
    ).stdout.replace("\n", "")

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
