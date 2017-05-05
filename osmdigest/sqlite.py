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
    
    def _node_from_obj(self, result):
        osm_id = result["osm_id"]
        data = { "id": osm_id,
            "lon": _to_float(result["longitude"]),
            "lat": _to_float(result["latitude"]) }
        node = _digest.Node(data)
        for key, value in self._get_tags("node_tags", osm_id).items():
            node.add_tag(key, value)
        return node

    def node(self, osm_id):
        """Return details of the node with this id.  Raises KeyError on failure
        to find.
        
        :param osm_id: The OSM id of the node.
        
        :return: An instance of :class:`Node`.
        """
        result = self._connection.execute("select * from nodes where nodes.osm_id=?", (osm_id,)).fetchone()
        if result is None:
            raise KeyError()
        return self._node_from_obj(result)

    def nodes(self):
        """A generator of all nodes."""
        result = self._connection.execute("select * from nodes")
        while True:
            node = result.fetchone()
            if node is None:
                return
            yield self._node_from_obj(node)

    def way(self, osm_id):
        """Return details of the way with this id.  Raises KeyError on failure
        to find.
        
        :param osm_id: The OSM id of the way.
        
        :return: An instance of :class:`Way`.
        """
        result = self._connection.execute("select noderef from ways where osm_id=? order by position", (osm_id,)).fetchall()
        if result is None or len(result) == 0:
            raise KeyError()
        way = _digest.Way({"id":osm_id})
        for r in result:
            way.add_node(r["noderef"])
        for key, value in self._get_tags("way_tags", osm_id).items():
            way.add_tag(key, value)
        return way

    def ways(self):
        """A generator of all ways."""
        result = self._connection.execute("select osm_id, noderef from ways order by osm_id, position")
        way = None
        while True:
            ref = result.fetchone()
            if ref is None or (way is not None and way.osm_id != ref["osm_id"]):
                for key, value in self._get_tags("way_tags", way.osm_id).items():
                    way.add_tag(key, value)
                yield way
                if ref is None:
                    return
            if way is None or way.osm_id != ref["osm_id"]:
                way = _digest.Way({"id": ref["osm_id"]})
            way.add_node(ref["noderef"])


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
    for key, value in node.tags.items():
        connection.execute("insert into node_tags(osm_id, key, value) values (?,?,?)",
            (node.osm_id, key, value))

def _write_way(connection, way):
    for pos, noderef in enumerate(way.nodes):
        connection.execute("insert into ways(osm_id, position, noderef) values (?,?,?)",
            (way.osm_id, pos, noderef))
    for key, value in way.tags.items():
        connection.execute("insert into way_tags(osm_id, key, value) values (?,?,?)",
            (way.osm_id, key, value))


class ConversionReport():
    def __init__(self):
        self.elements_processed = 0
        self.tags_generated = 0
        
    def _inc_elements_processed(self):
        self.elements_processed += 1
        
    def _inc_tags_processed(self, count):
        self.tags_generated += count
        
    def _report(self):
        return self.elements_processed % 100000 == 0
    
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
    connection.execute("create table ways(osm_id integer, position integer, noderef integer)")
    connection.execute("create index ways_idx on ways(osm_id, position)")
    connection.execute("create table way_tags(osm_id integer, key text, value text)")
    connection.execute("create index way_tags_osm_id_idx on way_tags(osm_id)")
    with connection:
        _write_osm(connection, next(gen))
        _write_bounds(connection, next(gen))
        
        report = ConversionReport()

        for element in gen:
            if element.name == "node":
                _write_node(connection, element)
            elif element.name == "way":
                _write_way(connection, element)
            report._inc_elements_processed()
            report._inc_tags_processed(len(element.tags))
            if report._report():
                yield report

def convert(xml_file, db_filename):
    """Convert the passed XML file to a sqlite3 database file.

    :param xml_file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.
    :param db_filename: Filename to pass to the `sqlite3` module.
    """
    for x in convert_gen(xml_file, db_filename):
        pass