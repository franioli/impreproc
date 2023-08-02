import argparse
from pathlib import Path

from easydict import EasyDict as edict


def parse_command_line() -> edict:
    """
    parse_command_line Parse command line input

    """
    parser = argparse.ArgumentParser(
        description="""Rename batch of images recursively. Check -h or --help for options.
        Usage: ./main.py /path/to/images -e jpg,png -r -p *_image*"""
    )
    parser.add_argument(
        "data_dir",
        type=str,
        help="Path to root directory containing images",
    )
    parser.add_argument(
        "-e",
        "--image_ext",
        type=str,
        help="Image file extensions, separated by commas (e.g., jpg,png)",
    )
    parser.add_argument(
        "-o",
        "--output_folder",
        type=str,
        default="renamed",
        help="Destination folder for renamed images (default: 'renamed')",
    )
    parser.add_argument(
        "-p",
        "--name_pattern",
        type=str,
        default=None,
        help="File name pattern to match (e.g., *_image*)",
    )
    parser.add_argument(
        "-b",
        "--base_name",
        type=str,
        default="IMG",
        help="Base name for renamed images (default: 'IMG')",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        default=False,
        help="Search for images recursively in subdirectories (default: False)",
    )
    parser.add_argument(
        "-D",
        "--delete_original",
        action="store_true",
        help="Remove original image after renaming (default: False)",
    )
    parser.add_argument(
        "-cs",
        "--case_sensitive",
        action="store_true",
        default=True,
        help="Make glob search case-sensitive (default: True)",
    )
    parser.add_argument(
        "-par",
        "--parallel",
        action="store_true",
        default=False,
        help="Flag to process images in parallel using multiprocessing (default: False)",
    )

    args = parser.parse_args()

    opt = edict(
        {
            "data_dir": Path(args.data_dir),
            "image_ext": None if args.image_ext is None else args.image_ext.split(","),
            "dest_folder": Path(args.output_folder),
            "recursive": args.recursive,
            "name_pattern": args.name_pattern,
            "base_name": args.base_name,
            "delete_original": args.delete_original,
            "case_sensitive": args.case_sensitive,
            "parallel": args.parallel,
        }
    )

    return opt
