import re
import numpy as np
from pathlib import Path
from typing import Union


def mrkread(fname: Union[Path, str]) -> dict:
    """
    mrkread Function to read DJI MRK files

    Args:
        fname (Union[Path, str]): _description_

    Returns:
        dict: _description_
    """

    # check if the file exists and is a .mrk file
    fname = Path(fname)
    assert fname.exists(), f"File {fname} does not exist"
    assert fname.suffix.lower() == ".mrk", f"File {fname} is not a .mrk file"

    # open the file and parse each row using , as separator
    with open(fname, "r") as fid:
        indata = [re.split(",|\t|[|]|\n", i) for i in fid.readlines()]

    n = len(indata)
    outdata = {
        "Time": [None] * n,
        "Name": [None] * n,
        "Lat": [None] * n,
        "Lon": [None] * n,
        "Ellh": [None] * n,
        "stdE": [None] * n,
        "stdN": [None] * n,
        "stdV": [None] * n,
        "dE": [None] * n,
        "dN": [None] * n,
        "dV": [None] * n,
        "Qual": [None] * n,
        "Flag": [None] * n,
    }

    for i, line in enumerate(indata):
        outdata["Name"][i] = "%03d" % np.float_(line[0])
        outdata["Time"][i] = np.float_(line[1])
        outdata["Lat"][i] = np.float_(line[9])
        outdata["Lon"][i] = np.float_(line[11])
        outdata["Ellh"][i] = np.float_(line[13])
        outdata["stdN"][i] = np.float_(line[15])
        outdata["stdE"][i] = np.float_(line[16])
        outdata["stdV"][i] = np.float_(line[17])
        outdata["dN"][i] = np.float_(line[3])
        outdata["dE"][i] = np.float_(line[5])
        outdata["dV"][i] = np.float_(line[7])
        outdata["Qual"][i] = np.float_(line[18])
        outdata["Flag"][i] = line[19]

    return outdata
