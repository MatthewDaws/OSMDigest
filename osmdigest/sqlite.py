"""
sqlite
~~~~~~

Converts OSM data from XML format to a simple relational database format, using
the Python standard library `sqlite3` module.

Typical usage is then:
    
    # Generate a DB file from some compressed XML input data
    convert("input.osm.bz2", "output.db")
    
    # Now connect to and use the database
    db = OSM_SQLite("output.db")
    # Find a particular node
    node = db.node(1234)
    # Iterate over all ways, finding those with a certain tag
    for way in db.ways():
        if "building" in way.tags():
            # Do something...
            pass
"""

from . import digest as _digest
import sqlite3 as _sqlite3


class RichWay(_digest.Way):
    """Subclass of :class:`Way` which stores complete node information."""
    def __init__(self, way, db):
        super().__init__({"id":way.osm_id})
        self._nodes = way._nodes
        self._tags = way._tags
        self._full_nodes = []
        for node_id in way.nodes:
            self._full_nodes.append(db.node(node_id))

    @property
    def complete_nodes(self):
        """Returns an ordered list of :class:`Node` instances which
        form the way.
        """
        return self._full_nodes
    
    def __repr__(self):
        return "RichWay({} ->  {} {})".format(self.osm_id, self.complete_nodes, self.tags)


class RichRelation(_digest.Relation):
    """Subclass of :class:`Relation` which stores full details of any node,
    way or relation which forms a member.
    """
    def __init__(self, relation, db):
        super().__init__({"id":relation.osm_id})
        self._tags = relation._tags
        self._members = relation._members
        self._full_members = []
        for member in self._members:
            if member.type == "node":
                detail = db.node(member.ref)
            elif member.type == "way":
                detail = db.complete_way(member.ref)
            elif member.type == "relation":
                detail = db.complete_relation(member.ref)
            self._full_members.append(detail)
    
    @property
    def complete_members(self):
        """Returns a list of members, each entry of which is a fully populated
        node, way or relation object.
        """
        return self._full_members
    
    def __repr__(self):
        # Deliberately aneamic so as to not spam...
        return "RichRelation({} ->  {} {})".format(self.osm_id, self.members, self.tags)


class OSM_SQLite():
    """Connects to the generated SQLite database, and provides methods for
    reading rich data from the database.
    
    :param db_filename: The generated SQLite database file.  No data is
      written.
    """
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
    def connection(self):
        """The underlying database connection: for debugging etc."""
        return self._connection

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
            raise KeyError("Node {} not found".format(osm_id))
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
            raise KeyError("Way {} not found".format(osm_id))
        way = _digest.Way({"id":osm_id})
        for r in result:
            way.add_node(r["noderef"])
        for key, value in self._get_tags("way_tags", osm_id).items():
            way.add_tag(key, value)
        return way
    
    def complete_way(self, osm_id):
        """Return full details of the way with this id: gives a complete list
        of nodes, not just their ids.  Raises KeyError on failure to find.
        
        :param osm_id: The OSM id of the way.  Alternatively, a :class:`Way`
          instance to augment with full node details.
        
        :return: An instance of :class:`RichWay`.
        """
        if isinstance(osm_id, _digest.Way):
            osm_id = osm_id.osm_id
        return RichWay(self.way(osm_id), self)
        
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

    def relation(self, osm_id):
        """Return details of the relation with this id.  Raises KeyError on
        failure to find.
        
        :param osm_id: The OSM id of the relation.
        
        :return: An instance of :class:`Relation`.
        """
        result = self._connection.execute("select * from relations where osm_id=?", (osm_id,)).fetchall()
        if result is None or len(result) == 0:
            raise KeyError("Relation {} not found".format(osm_id))
        rel = _digest.Relation({"id":osm_id})
        for r in result:
            rel.add_member(_digest.Member(type=r["member"],
                ref=r["memberref"], role=r["role"]))
        for key, value in self._get_tags("relation_tags", osm_id).items():
            rel.add_tag(key, value)
        return rel

    def complete_relation(self, osm_id):
        """Return full details of the relation with this id: gives a complete
        list of objects, not just their ids.  Raises KeyError on failure to
        find.
        
        :param osm_id: The OSM id of the relation.  Alternatively, a
          :class:`Relation` instance to augment with full details.
        
        :return: An instance of :class:`RichRelation`.
        """
        if isinstance(osm_id, _digest.Relation):
            osm_id = osm_id.osm_id
        return RichRelation(self.relation(osm_id), self)

    def relations(self):
        """A generator of all the relations."""
        result = self._connection.execute("select * from relations order by osm_id")
        rel = None
        while True:
            ref = result.fetchone()
            if ref is None or (rel is not None and rel.osm_id != ref["osm_id"]):
                for key, value in self._get_tags("relation_tags", rel.osm_id).items():
                    rel.add_tag(key, value)
                yield rel
                if ref is None:
                    return
            if rel is None or rel.osm_id != ref["osm_id"]:
                rel = _digest.Relation({"id": ref["osm_id"]})
            rel.add_member(_digest.Member(type=ref["member"],
                ref=ref["memberref"], role=ref["role"]))


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

def _write_relation(connection, relation):
    for member in relation.members:
        connection.execute("insert into relations(osm_id, member, memberref, role) values (?,?,?,?)",
            (relation.osm_id, member.type, member.ref, member.role))
    for key, value in relation.tags.items():
        connection.execute("insert into relation_tags(osm_id, key, value) values (?,?,?)",
            (relation.osm_id, key, value))


class ConversionReport():
    def __init__(self, message=None):
        self.elements_processed = 0
        self.tags_generated = 0
        self.message = message
        
    def _inc_elements_processed(self):
        self.elements_processed += 1
        
    def _inc_tags_processed(self, count):
        self.tags_generated += count
        
    def _report(self):
        return self.elements_processed % 100000 == 0
    
    def __repr__(self):
        if self.message is None:
            return "ConversionReport(elements_processed={}, tags_generated={})".format(self.elements_processed, self.tags_generated)
        return "ConversionReport(" + self.message + ")"


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
    try:
        connection.execute("create table nodes(osm_id integer primary key, longitude integer, latitude integer)")
        connection.execute("create table node_tags(osm_id integer, key text, value text)")
        connection.execute("create index node_tags_osm_id_idx on node_tags(osm_id)")
        connection.execute("create table ways(osm_id integer, position integer, noderef integer)")
        connection.execute("create index ways_idx on ways(osm_id, position)")
        connection.execute("create table way_tags(osm_id integer, key text, value text)")
        connection.execute("create index way_tags_osm_id_idx on way_tags(osm_id)")
        connection.execute("create table relations(osm_id integer, member text, memberref integer, role text)")
        connection.execute("create index relations_idx on relations(osm_id)")
        connection.execute("create table relation_tags(osm_id integer, key text, value text)")
        connection.execute("create index relation_tags_osm_id_idx on relation_tags(osm_id)")
        with connection:
            _write_osm(connection, next(gen))
            _write_bounds(connection, next(gen))
            
            report = ConversionReport()

            for element in gen:
                if element.name == "node":
                    _write_node(connection, element)
                elif element.name == "way":
                    _write_way(connection, element)
                elif element.name == "relation":
                    _write_relation(connection, element)
                report._inc_elements_processed()
                report._inc_tags_processed(len(element.tags))
                if report._report():
                    yield report
    finally:
        connection.close()

def convert(xml_file, db_filename):
    """Convert the passed XML file to a sqlite3 database file.

    :param xml_file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.
    :param db_filename: Filename to pass to the `sqlite3` module.
    """
    for x in convert_gen(xml_file, db_filename):
        pass
