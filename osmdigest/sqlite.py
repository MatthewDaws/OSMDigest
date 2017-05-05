"""
sqlite
~~~~~~

Converts OSM data from XML format to a simple relational database format, using
the Python standard library `sqlite3` module.
"""

from . import digest as _digest
import sqlite3 as _sqlite3


# Read only
class OSM_SQLite():
    def __init__(self, db_filename):
        self._connection = _sqlite3.connect(db_filename)
        self._connection.row_factory = _sqlite3.Row
        self._osm = self._read_osm()
        self._bounds = self._read_bounds()

    def _read_osm(self):
        osm = dict(self._connection.execute("select * from osm").fetchone())
        timestamp = osm["gentime"]
        del osm["gentime"]
        if timestamp is not None and timestamp != "None":
            d, t = timestamp.split()
            osm["timestamp"] = "{}T{}Z".format(d, t)
        return _digest.OSM("osm", osm)

    def _read_bounds(self):
        bounds = self._connection.execute("select * from bounds").fetchone()
        xml = { "minlat": _to_float(bounds["minlat"]),
               "maxlat": _to_float(bounds["maxlat"]),
               "minlon": _to_float(bounds["minlon"]),
               "maxlon": _to_float(bounds["maxlon"]) }
        return _digest.Bounds("bounds", xml)

    def close(self):
        """Close the connection to the database.  After this, most methods will
        fail to work."""
        self._connection.close()

    def __enter__(self):
        return self
    
    def __exit__(self, a,b,c):
        self.close()

    @property
    def osm(self):
        """Returns an :class:`OSM` object detailing how the XML file was
        generated.
        """
        return self._osm

    @property
    def bounds(self):
        """Return a :class:`Bounds` object detailing the bounds of data."""
        return self._bounds
    
    def _get_tags(self, dbname, osm_id):
        #tags = self._connection.execute("select key, value from ? where osm_id=?", (dbname, osm_id)).fetchall()
        tags = self._connection.execute("select key, value from "+dbname+" where osm_id=?", (osm_id,)).fetchall()
        return { key:value for (key, value) in tags }
    
    def node(self, osm_id):
        """Return details of the node with this id.  Raises KeyError on failure
        to find.
        
        :param osm_id: The OSM id of the node.
        
        :return: An instance of :class:`Node`.
        """
        result = self._connection.execute("select * from nodes where nodes.osm_id=?", (osm_id,)).fetchone()
        if result is None:
            raise KeyError()
        data = { "id": result["osm_id"],
            "lon": _to_float(result["longitude"]),
            "lat": _to_float(result["latitude"]) }
        node = _digest.Node(data)
        for key, value in self._get_tags("node_tags", osm_id).items():
            node.add_tag(key, value)
        return node


def _to_float(num):
    return num / 1e7

def _to_num(fl):
    if fl >= 0:
        return int(fl * 1e7 + 0.5)
    return int(fl * 1e7 - 0.5)


def _write_osm(connection, osm):
    connection.execute("create table osm(version text, generator text, gentime text)")
    connection.execute("insert into osm(version, generator, gentime) values (?,?,?)",
        (osm.version, osm.generator, str(osm.timestamp)))

def _write_bounds(connection, bounds):
    connection.execute("create table bounds(minlat integer, maxlat integer, minlon integer, maxlon integer)")
    data = (bounds.min_latitude, bounds.max_latitude, bounds.min_longitude, bounds.max_longitude)
    connection.execute("insert into bounds(minlat, maxlat, minlon, maxlon) values (?,?,?,?)",
        tuple( _to_num(x) for x in data ))

def _write_node(connection, node):
    connection.execute("insert into nodes(osm_id, longitude, latitude) values (?,?,?)",
        (node.osm_id, _to_num(node.longitude), _to_num(node.latitude)))
    tags = [ (node.osm_id, key, value) for key, value in node.tags.items() ]
    if len(tags) > 0:
        connection.executemany("insert into node_tags(osm_id, key, value) values (?,?,?)", tags)


class ConversionReport():
    def __init__(self):
        self.elements_processed = 0
        self.tags_generated = 0
        
    def _inc_elements_processed(self):
        self.elements_processed += 1
        
    def _inc_tags_processed(self, count):
        self.tags_generated += count
        
    def _report(self):
        return self.elements_processed % 1000 == 0
    
    def __repr__(self):
        return "ConversionReport(elements_processed={}, tags_generated={})".format(self.elements_processed, self.tags_generated)
        

def convert_gen(xml_file, db_filename):
    """Convert the passed XML file to a sqlite3 database file.  As this is
    rather slow, this function is a generator which will `yield` information
    on its progress.

    :param xml_file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.
    :param db_filename: Filename to pass to the `sqlite3` module.
    """
    gen = _digest.parse(xml_file)
    connection = _sqlite3.connect(db_filename)
    connection.execute("create table nodes(osm_id integer primary key, longitude integer, latitude integer)")
    connection.execute("create table node_tags(osm_id integer, key text, value text)")
    connection.execute("create index node_tags_osm_id_idx on node_tags(osm_id)")
    try:
        with connection:
            _write_osm(connection, next(gen))
            _write_bounds(connection, next(gen))
        
        report = ConversionReport()
        
        for element in gen:
            if element.name == "node":
                _write_node(connection, element)
            report._inc_elements_processed()
            report._inc_tags_processed(len(element.tags))
            if report._report():
                yield report
                connection.commit()
    finally:
        connection.commit()
        connection.close()    

def convert(xml_file, db_filename):
    """Convert the passed XML file to a sqlite3 database file.

    :param xml_file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.
    :param db_filename: Filename to pass to the `sqlite3` module.
    """
    for x in convert_gen(xml_file, db_filename):
        pass