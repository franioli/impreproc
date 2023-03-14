import numpy as np
import time
import sys
import argparse
import PIL
import exifread

from easydict import EasyDict as EasyDict
from pathlib import Path
from datetime import datetime


def parse_command_line():
    """
    parse_command_line Parse command line input

    """
    parser = argparse.ArgumentParser(
        description="""icepy
            Low-cost stereo photogrammetry for 4D glacier monitoring \
            Check -h or --help for options.
        Usage: ./main.py -c config_base.yaml"""
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path of to the configuration file",
    )
    args = parser.parse_args()

    if not len(sys.argv) > 1:
        raise ValueError(
            "Not enough input arguments. Specify at least the configuration file. Use --help (or -h) for help."
        )

    return args


if __name__ == "__main__":
    pass
