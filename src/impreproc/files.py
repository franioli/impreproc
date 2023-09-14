import os
import shutil

from pathlib import Path
from typing import Union


RULES = {
    "raw": ["dng", "cr2", "nef", "arw"],
    "jpg": ["jpg", "jpeg"],
    "png": ["png"],
    "tif": ["tif", "tiff"],
    # "dji_gnss": ["obs", "nav", "bin", "mrk"],
    # "videos": ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm"],
    # "documents": ["pdf", "docx", "pptx", "xls", "doc", "ppt"],
    # "audios": ["mp3", "wav", "ogg", "flac", "aac", "wma", "m4a"],
    # "archives": ["zip", "rar", "7z", "tar", "gz", "pkg", "deb", "rpm"],
    # "executables": ["exe", "msi", "apk", "app", "bat", "sh"],
    # "code": ["py", "js", "html", "css", "cpp", "c", "java", "go", "php", "rb", "json", "xml", "sql"],
}


def get_extension(file: Union[str, Path]) -> str:
    """Returns the extension of a given file."""
    return Path(file).suffix.lower()[1:]


def organize_files(
    dir: Union[str, Path],
    rules: dict = RULES,
    inplace: bool = True,
) -> None:
    """Organizes files in a given directory into corresponding subdirectories based on file extension."""

    files = os.listdir(dir)
    current_extensions = set([get_extension(file) for file in files])

    for rule, extensions in rules.items():
        if not isinstance(extensions, list):
            raise TypeError("Rules must be a dictionary of lists.")
        # Check if at least one of the extensions is in the current directory
        if any([v in current_extensions for v in extensions]):
            out_path = Path(dir) / rule.lower()
            out_path.mkdir(exist_ok=True, parents=True)

    for file in files:
        ext = get_extension(file)
        if not ext:
            continue  # Skip directories and files without extensions

        for rule, extensions in rules.items():
            if ext in extensions:
                if inplace:
                    new_path = Path(dir) / rule / file
                    os.rename(os.path.join(dir, file), new_path)
                else:
                    new_path = Path(dir) / rule / Path(file).name
                    shutil.copy(os.path.join(dir, file), new_path)
                break


class Organizer:
    def __init__(
        self, rules: dict = RULES, recursive: bool = False, keep_dir_tree: bool = False
    ) -> None:
        assert isinstance(rules, dict), "Rules must be a dictionary."
        assert isinstance(recursive, bool), "Recursive must be a boolean."
        assert isinstance(keep_dir_tree, bool), "Keep_dir_tree must be a boolean."

        self.rules = rules
        self.recursive = recursive
        self.keep_dir_tree = keep_dir_tree

    def organize(
        self,
    ) -> bool:
        pass


if __name__ == "__main__":
    # path = input(r"PATH: ")
    # organize_files(path)

    # imdir = "data/conversion/DJI_202303031031_001"

    # organize_files(imdir, inplace=False)

    # Batch on multiple directories
    # root_dir = "/mnt/labmgf/Belvedere/2023/00_img"
    root_dir = "data/conversion"
    subfolders = sorted([Path(f.path) for f in os.scandir(root_dir) if f.is_dir()])

    for dir in subfolders:
        organize_files(dir)
