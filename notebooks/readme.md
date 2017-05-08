# Notebooks

Some examples of how to look at OpenStreetMap XML data, and how to use the package.

- [Explore an example](Explore%20an%20example.ipynb) Load some XML data and explore it, using a number of different XML parsing techniques.
- [Pythonify](Pythonify.ipynb) Explores converting the XML data is raw python data structures, and saving these using `pickle`.  This might be viable for medium sized data, but uses too much memory for large data sets.
- [Convert to SQLite](Convert%20to%20SQLite%20DB.ipynb) Uses the Python standard library support for SQLite databases.  This is quite a viable approach-- the resulting database files are (rather) large but it is very quick and memory efficient to access e.g. ways and then populate with node information.
- [Convert script](convert_to_db.py) Very simply python script to convert a XML file to a SQLite database file.  (A long running task is easier to run from the command prompt than in a notebook.)


### Making practical use of the data

- [Explore buildings and addresses](Explore%20buildings%20and%20addresses.ipynb) Looks at how buildings and addresses are tagged in some UK data, and some USA data.
- [Find places](Find%20places.ipynb) Work in progress
- [Geopandas](Geopandas.ipynb) Work in progress