# impreproc

`impreproc` allows for performing several pre-processing operations on large datasets of images, e.g., acquired by several UAVs photogrammetric flights, in batch mode. 
## Installation

Clone the repository

```bash
git clone https://github.com/franioli/impreproc.git
cd impreproc
```

Create an anaconda environment and upgrade pip

```bash
conda create -n impreproc python=3.9
conda activate impreproc
python3.8 -m pip install --upgrade pip
```

Install `impreproc` package and its dependancies by using pip

```bash
pip install -e .
```

## Features

The following operations are currently supported:

- [x] read DJI .mrk file, extract the GPS coordinates of the images and their accuracy in batch mode, and save them in a .csv file together with the exif data.
- [x] GUI for the .mrk file reader 
- [x] rename images in batch mode based on a custom defined pattern (e.g., `%BASE_NAME%_%DATE%_%TIME%.%EXT%`)
- [x] perform raw conversion in batch mode and recursively in subfolders by using `rawtherapee` software
- [x] organize files recursively in a directory tree, subdividing them in subfolders based on their extensions
- [x] make CRS conversion with pyproj
- [ ] make previews images for Potree
- [ ] implement geodetic height correction
- [ ] make time-laspe videos from image sequence

## Getting Started

To get started with `impreproc`, you can refer to the documentation at [https://franioli.github.io/impreproc/](https://franioli.github.io/impreproc/) or use the Jupyter notebooks available in the notebook folder.