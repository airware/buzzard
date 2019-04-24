The code is currently annotated for review, it will be cleaned before merging.

Previous code is annotated with a :heavy_multiplication_x: symbol.
New code is annotated with a :grey_question: symbol.

```
# repository's description
X Geofiles management can be great. No joke!
? Data-science with images and geometries
? Advanced raster and geometry manipulations

which one?
```


```
# repository's keywords
X python gis raster vector gdal feedback-welcome footprint
? python gis geospatial raster image vector geometry gdal ogr osr data-science footprint rasters-pipelines

more? less?
```

---

Begining of `README.md`.

---

# `buzzard`
:heavy_multiplication_x: In a nutshell, `buzzard` reads and writes geospatial raster and vector data.
:grey_question: In a nutshell, `buzzard` provides powerful abstractions to work with images and geometries that comes from many kind of sources.

<div align="center">
  <img src="https://github.com/airware/buzzard/raw/master/img/buzzard.png"><br><br>
</div>

[![license](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/airware/buzzard/blob/master/LICENSE)[![CircleCI](https://circleci.com/gh/airware/buzzard/tree/master.svg?style=shield&circle-token=9d41310f0eb3f8ff120a7103ba2d7ee5d5d628b7)](https://circleci.com/gh/airware/buzzard/tree/master)[![codecov](https://codecov.io/gh/airware/buzzard/branch/master/graph/badge.svg?token=FbWmLGplCq)](https://codecov.io/gh/airware/buzzard)

## `buzzard` is
:heavy_multiplication_x: :heavy_multiplication_x: :heavy_multiplication_x:
- a python library
- a `gdal`/`ogr`/`osr` wrapper
- designed to hide all cumbersome operations while working with GIS files
- designed for data science workflows
- under active development (see [`todo`](https://www.notion.so/buzzard/2c94ef6ee8da4d6280834129cc00f4d2?v=334ead18796342feb32ba85ccdfcf69f))
- tested with `pytest` with python 3.4 and python 3.7

:heavy_multiplication_x: :heavy_multiplication_x: :heavy_multiplication_x:

:grey_question: :grey_question: :grey_question:
- A _python_ library.
- Primarily designed to hide all cumbersome operations when doing data-science with [GIS](https://en.wikipedia.org/wiki/Geographic_information_system) files.
- Multipurpose, it can be used in all kind of situations were images or geometries are involved.
- A pythonic wrapper for _osgeo_'s _gdal_/_ogr_/_osr_.
- A solution to work with arbitrary large images by simplifying and automating the manipulation of image slices.
- Developed at [Delair](https://delair.aero) where it is used in several deep learning and algorithmic projects.

:grey_question: :grey_question: :grey_question:

## How to open and read files
This example demonstrates how to visualize a large raster based on polygons.

```py
import buzzard as buzz
import numpy as np
import matplotlib.pyplot as plt

# Open the files. Only files' metadata are read so far
r = buzz.open_raster('path/to/rgba-image.file')
v = buzz.open_vector('path/to/polygons.file')

# Load the polygons from disk one by one as shapely objects
for poly in v.iter_data():

    # Compute the Footprint bounding `poly`
    fp = r.fp.intersection(poly)
    print(fp)

    # Load the image from disk at `fp` to a numpy array
    rgb = r.get_data(fp=fp, channels=(0, 1, 2))
    alpha = r.get_data(fp=fp, channels=3)

    # Create a boolean mask as a numpy array from the shapely polygon
    mask = np.invert(fp.burn_polygons(poly))

    # Darken pixels outside of polygon, set transparent pixels to orange
    rgb[mask] = (rgb[mask] * 0.5).astype(np.uint8)
    rgb[alpha == 0] = [236, 120, 57]

    # Show the result with matplotlib 
    plt.imshow(rgb)
    plt.show()

```
`Footprint(tl=(712834.451695, 281577.139643), br=(713136.221695, 281294.539643), size=(301.770000, 282.600000), rsize=(6706, 6280))`

<div align="center">
  <img src="https://user-images.githubusercontent.com/9285880/56652243-34924800-668b-11e9-9692-a77e44a05f00.png" width="100%"><br><br>
</div>

`Footprint(tl=(712441.061695, 281118.139643), br=(712730.051695, 281007.304643), size=(288.990000, 110.835000), rsize=(6422, 2463))`
<div align="center">
  <img src="https://user-images.githubusercontent.com/9285880/56652245-34924800-668b-11e9-8a9d-7f1876c144a5.png" width="65%"><br><br>
</div>

## How to create files and manipulate _Footprints_
```py
import buzzard as buzz
import numpy as np
import matplotlib.pyplot as plt
import keras

r = buzz.open_raster('path/to/rgba-image.file')
km = keras.models.load_model('path/to/deep-learning-model.hdf5')

# Chunk the raster's Footprint to Footprints of size
# 1920 x 1080 pixel stored in a 2d numpy array
tiles = r.fp.tile(1920, 1080)

all_roads = []

for i, fp in enumerate(tiles.flat):
    rgb = r.get_data(fp=fp, channels=(0, 1, 2))

    # Perform pixelwise semantic segmentation with a keras model
    predictions_heatmap = km.predict(rgb[np.newaxis, ...])[0]
    predictions_top1 = np.argmax(heatmap, axis=-1)

    # Save the prediction to a `geotiff`
    with buzz.create_raster(path='predictions_{}.tif'.format(i), fp=fp,
                            dtype='uint8', channel_count=1).close as out:
        out.set_data(predictions_top1)

    # Extract the road polygons by transforming a numpy boolean mask to shapely polygons
    road_polygons = fp.find_polygons(predictions_top1 == 3)
    all_roads += road_polygons

    # Show the result with matplotlib for one tile
    if i == 2:
        plt.imshow(rgb)
        plt.imshow(predictions_top1)
        plt.show()

# Save all roads found to a single `shapefile`
with buzz.create_vector(path='roads.shp', type='polygon').close as out:
    for poly in all_roads:
        out.inser_data(poly)

```

<div align="center">
  <img src="https://user-images.githubusercontent.com/9285880/56656251-4b3d9c80-6695-11e9-9a0e-1d9a309ddf03.png" width="100%"><br><br>
</div>

<div align="center">
  <img src="https://user-images.githubusercontent.com/9285880/56656252-4b3d9c80-6695-11e9-80cd-84365dd68f91.png" width="100%"><br><br>
</div>

## Advanced examples
Additional examples can be found here:
- [Files and _Footprints_ in depth](https://github.com/airware/buzzard/blob/master/doc/examples.ipynb)
- [_async rasters_ in depth](https://github.com/airware/buzzard/blob/master/doc/notebook2/async_rasters.ipynb)

## `buzzard` allows
:heavy_multiplication_x: :heavy_multiplication_x: :heavy_multiplication_x:
- Raster and vector files reading to `numpy.ndarray`, `shapely` objects, `geojson` and raw coordinates
- Raster and vector files writing from `numpy.ndarray`, `shapely` objects, `geojson` and raw coordinates
- Raster and vector files creation
- Powerful manipulations of raster windows
- Spatial reference homogenization between opened files like a `GIS software`

:heavy_multiplication_x: :heavy_multiplication_x: :heavy_multiplication_x:

:grey_question: :grey_question: :grey_question:
- Raster and vector files opening and creation. Supports all [GDAL drivers (GTiff, PNG, ...)](https://www.gdal.org/formats_list.html) and all [OGR drivers (GeoJSON, DXF, Shapefile, ...)](https://www.gdal.org/ogr_formats.html).
- Raster files reading to _numpy.ndarray_.
  - _Options:_ `sub-rectangle reading`, `rotated and scaled sub-rectangle reading (thanks to on-the-fly remapping with OpenCV)`, `automatic parallelization of read and remapping (soon)`, `async (soon)`, `be the source of an image processing pipeline (soon)`.
  - _Properties:_ `thread-safe`
- Raster files writing from _numpy.ndarray_.
  - _Options:_ `sub-rectangle writing`, `rotated and scaled sub-rectangle writing (thanks to on-the-fly remapping with OpenCV)`, `masked writing`.
- Vector files reading to _shapely objects_, _geojson dict_ and _raw coordinates_.
  - _Options:_ `masking`.
  - _Properties:_ `thread-safe`
- Vector files writing from _shapely objects_, _geojson dict_ and _raw coordinates_.
- Powerful manipulations of raster windows
- Instantiation of image processing pipelines where each node is a raster, and each edge is a user defined python function working on _numpy.ndarray_ (beta, partially implemented).
  - _Options:_ `automatic parallelization using user defined thread or process pools`, `disk caching`.
  - _Properties:_ `lazy evaluation`, `deterministic`, `automatic tasks chunking into tiles`, `fine grain task prioritization`, `backpressure prevention`.
- Spatial reference homogenization between opened files like a GIS software does (beta)

:grey_question: :grey_question: :grey_question:

## `buzzard` contains
:heavy_multiplication_x: :heavy_multiplication_x: :heavy_multiplication_x:
- a class to open/read/write/create GIS files: [`Dataset`](./buzzard/_dataset.py)
- a toolbox class designed to locate a rectangle in both image space and geometry space: [`Footprint`](./buzzard/_footprint.py)

:heavy_multiplication_x: :heavy_multiplication_x: :heavy_multiplication_x:

:grey_question: :grey_question: :grey_question:
- A [`Dataset`](https://github.com/airware/buzzard/blob/master/buzzard/_dataset.py) class that oversees all opened files in order to share ressources.
- An immutable toolbox class, the [`Footprint`](https://github.com/airware/buzzard/blob/master/buzzard/_footprint.py), designed to locate a rectangle in both image space and geometry space.

:grey_question: :grey_question: :grey_question:

## Dependencies
The following table lists dependencies along with the minimum version, their status for the project and the related license.

| Library          | Version  | Mandatory | License                                                                              | Comment                                                       |
|------------------|----------|-----------|--------------------------------------------------------------------------------------|---------------------------------------------------------------|
| gdal             | >=2.3.3  | Yes       | [MIT/X](https://github.com/OSGeo/gdal/blob/trunk/gdal/LICENSE.TXT)                   | Hard to install. Will be included in `buzzard` wheels         |
| opencv-python    | >=3.1.0  | Yes       | [3-clause BSD](http://opencv.org/license.html)                                       | Easy to install with `opencv-python` wheels. Will be optional |
| shapely          | >=1.6.1  | Yes       | [3-clause BSD](https://github.com/Toblerity/Shapely/blob/master/LICENSE.txt)         |                                                               |
| affine           | >=2.0.0  | Yes       | [3-clause BSD](https://github.com/sgillies/affine/blob/master/LICENSE.txt)           |                                                               |
| numpy            | >=1.15.0 | Yes       | [numpy](https://docs.scipy.org/doc/numpy-1.10.0/license.html)                        |                                                               |
| scipy            | >=0.19.1 | Yes       | [scipy](https://www.scipy.org/scipylib/license.html)                                 |                                                               |
| pint             | >=0.8.1  | Yes       | [3-clause BSD](https://github.com/hgrecco/pint/blob/master/LICENSE)                  |                                                               |
| six              | >=1.11.0 | Yes       | [MIT](https://github.com/benjaminp/six/blob/master/LICENSE)                          |                                                               |
| sortedcontainers | >=1.5.9  | Yes       | [apache](https://github.com/grantjenks/python-sortedcontainers/blob/master/LICENSE)  |                                                               |
| Rtree            | >=0.8.3  | Yes       | [MIT](https://github.com/Toblerity/rtree/blob/master/LICENSE.txt)                    |                                                               |
| scikit-image     | >=0.14.0 | Yes       | [scikit-image](https://github.com/scikit-image/scikit-image/blob/master/LICENSE.txt) |                                                               |
| chainmap         | >=1.0.2  | Yes       | [Python 2.7 license](https://bitbucket.org/jeunice/chainmap)                         | Only for python <3.2                                          |
| pytest           | >=3.2.2  | No        | [MIT](https://docs.pytest.org/en/latest/license.html)                                | Only for tests                                                |
| attrdict         | >=2.0.0  | No        | [MIT](https://github.com/bcj/AttrDict/blob/master/LICENSE.txt)                       | Only for tests                                                |

## How to install from terminal
### Anaconda and pip
```sh
# Step 1 - Install Anaconda
# https://www.anaconda.com/download/

# Step 2 - Create env
conda create -n buzz python gdal>=2.3.3 shapely rtree -c 'conda-forge'

# Step 3 - Activate env
conda activate buzz

# Step 4 - Install buzzard
pip install buzzard
```

### Docker
```sh
docker build -t buzz --build-arg PYTHON_VERSION=3.7 https://raw.githubusercontent.com/airware/buzzard/master/.circleci/images/base-python/Dockerfile
docker run -it --rm buzz bash
pip install buzzard

```

### Package manager and pip
```sh
# Step 1 - Install GDAL and rtree
# Windows:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#rtree

# MacOS:
brew install gdal
brew tap osgeo/osgeo4mac
brew tap --repair
brew install gdal2
brew install spatialindex
export PATH="/usr/local/opt/gdal2/bin:$PATH"
python -m pip install 'gdal==2.3.3'

# Ubuntu:
sudo add-apt-repository ppa:ubuntugis/ppa
sudo apt-get update
sudo apt-get install gdal-bin
sudo apt-get install libgdal-dev
sudo apt-get install python3-rtree
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export C_INCLUDE_PATH=/usr/include/gdal
pip install GDAL

# Step 2 - Install buzzard
python -m pip install buzzard
```

## Supported Python versions
To enjoy the latest buzzard features, update your python!

#### Full python support
- Latest supported version: `3.7` (June 2018)
- Oldest supported version: `3.4` (March 2014)

#### Partial python support
- `2.7`: use buzzard version `0.4.4`

## How to test
```sh
git clone https://github.com/airware/buzzard
pip install -r buzzard/requirements-dev.txt
pytest buzzard/buzzard/test
```

## Documentation
Hosted soon, in the meantime
- look at the docstrings in code
- play with the examples above

## Contributions and feedback
Welcome to the `buzzard` project! We appreciate any contribution and feedback, your proposals and pull requests will be considered and responded to. For more information, see the [`CONTRIBUTING.md`](./CONTRIBUTING.md) file.

## Authors
See [AUTHORS](./AUTHORS.md)

## License and Notice
See [LICENSE](./LICENSE) and [NOTICE](./NOTICE).

## Other pages
- [examples](./doc/examples.ipynb)
- [classes](https://github.com/airware/buzzard/wiki/Classes)
- [wiki](https://github.com/airware/buzzard/wiki)
- [todo](https://www.notion.so/buzzard/2c94ef6ee8da4d6280834129cc00f4d2?v=334ead18796342feb32ba85ccdfcf69f)

------------------------------------------------------------------------------------------------------------------------

