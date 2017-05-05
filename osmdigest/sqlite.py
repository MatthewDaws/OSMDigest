"""
sqlite
~~~~~~

Converts OSM data from XML format to a simple relational database format, using
the Python standard library `sqlite3` module.
"""

from . import digest as _digest
import sqlite3 as _sqlite3


# Read only
class OSM_SQLITE():
    def __init__(self, db_filename):
        self._connection = _sqlite3.connect(db_filename)
        self._connection.row_factory = _sqlite3.Row
        self._osm = self._read_osm()

    def _read_osm(self):
        osm = dict(self._connection.execute("select * from osm").fetchone())
        timestamp = osm["gentime"]
        del osm["gentime"]
        if timestamp is not None and timestamp != "None":
            d, t = timestamp.split()
            osm["timestamp"] = "{}T{}Z".format(d, t)
        return _digest.OSM("osm", osm)

    @property
    def osm(self):
        """Returns an :class:`OSM` object detailing how the XML file was
        generated.
        """
        return self._osm


def _write_osm(connection, osm):
    connection.execute("create table osm(version text, generator text, gentime text)")
    connection.execute("insert into osm(version, generator, gentime) values (?,?,?)",
        (osm.version, osm.generator, str(osm.timestamp)))

def convert(xml_file, db_filename):
    """Convert the passed XML file to a sqlite3 database file.

    :param xml_file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.
    :param db_filename: Filename to pass to the `sqlite3` module.
    """

    gen = _digest.parse(xml_file)
    connection = _sqlite3.connect(db_filename)
    with connection:
        _write_osm(connection, next(gen))
