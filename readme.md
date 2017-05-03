# OSMDigest

Some simple utilties for reading and processing raw Open Street Map download data, using pure python.  Mostly for my own interest (I try to stick to the Python standard library), but also with the hope this is of use to other people.

At the time of writing, OSM data cannot easily be read into, say, [geopandas](http://geopandas.org/).  There is good support for dealing with OSM data in C++ or Java, for example, and for serious processing, the size of the datasets suggests that this is the way to go.  Sticking with Python, other options are:

- [osmread](https://github.com/dezhin/osmread) which is also a Python project (using lxml); can also read PBF files (slowly).
- [osmnx](https://github.com/gboeing/osmnx) which looks to be a very nice library for downloading *small* subsets of data directly from the Overpass API.  Currently mainly aimed at network analysis of road networks.

## Usage

Currently under active development.  See [notebooks](notebooks) for some Jupyter notebooks demoing features.