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
from . import richobjs

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
        tags = self._connection.execute("select key, value from "+dbname+" where osm_id=?", (osm_id,)).fetchall()
        return { key:value for (key, value) in tags }

    @staticmethod
    def _yield_ids(dbresult):
        while True:
            osm_id = dbresult.fetchone()
            if osm_id is None:
                return
            yield osm_id[0]

    def _search_tags(self, dbname, key, value):
        """Generator returning ids of matches"""
        tags = self._connection.execute("select osm_id from "+dbname+" where key=? and value=?", (key,value))
        yield from self._yield_ids(tags)

    def _search_tag_keys(self, dbname, key):
        """Generator returning ids of matches"""
        tags = self._connection.execute("select osm_id from "+dbname+" where key=?", (key,))
        yield from self._yield_ids(tags)

    def _search_all_tags(self, dbname, wanted_tags):
        """Generator of ids which match all wanted_tags"""
        wanted_tags = list(wanted_tags.items())
        if len(wanted_tags) == 0:
            raise ValueError("Must specify at least one tag")
        for osm_id in self._search_tags(dbname, wanted_tags[0][0], wanted_tags[0][1]):
            tags = self._get_tags(dbname, osm_id)
            if all( key in tags and tags[key] == value for (key, value) in wanted_tags ):
                yield osm_id

    def _search_all_tag_keys(self, dbname, wanted_keys):
        """Generator of ids which match all wanted_tags"""
        wanted_tags = list(wanted_keys)
        if len(wanted_tags) == 0:
            raise ValueError("Must specify at least one tag key")
        for osm_id in self._search_tag_keys(dbname, wanted_tags[0]):
            tags = self._get_tags(dbname, osm_id)
            if all( key in tags for key in wanted_tags ):
                yield osm_id

    def search_relation_tags(self, tags):
        """Search all relations for any with matching tags.

        :param tags: A dictionary of key/value pairs.  Only relations with all
          these tags are returned.
        
        :return: A list of matching relations.
        """
        return [self.relation(osm_id) for osm_id in self._search_all_tags("relation_tags", tags)]

    def search_way_tags(self, tags):
        """Search all ways for any with matching tags.

        :param tags: A dictionary of key/value pairs.  Only ways with all
          these tags are returned.
        
        :return: A list of matching ways.
        """
        return [self.way(osm_id) for osm_id in self._search_all_tags("way_tags", tags)]

    def search_node_tags(self, tags):
        """Search all nodes for any with matching tags.

        :param tags: A dictionary of key/value pairs.  Only nodes with all
          these tags are returned.
        
        :return: A list of matching nodes.
        """
        return [self.node(osm_id) for osm_id in self._search_all_tags("node_tags", tags)]

    def search_relation_tag_keys(self, keys):
        """Search all relations for any with matching tag keys.

        :param keys: A set of keys to search for.  Any relations which have
          tags for all these keys (and any values) will be returned.
        
        :return: A generator (for efficiency) of matching relations.
        """
        for osm_id in self._search_all_tag_keys("relation_tags", keys):
            yield self.relation(osm_id)

    def search_way_tag_keys(self, keys, just_ids = False):
        """Search all ways for any with matching tag keys.

        :param keys: A set of keys to search for.  Any ways which have tags
          for all these keys (and any values) will be returned.
        :param just_ids: If True, then only return the osm_id's of the ways.
          Default is False.
        
        :return: A generator (for efficiency) of matching ways.
        """
        gen = self._search_all_tag_keys("way_tags", keys)
        if just_ids:
            yield from gen
        else:
            for osm_id in gen:
                yield self.way(osm_id)

    def search_node_tag_keys(self, keys):
        """Search all nodes for any with matching tag keys.

        :param keys: A set of keys to search for.  Any nodes which have tags
          for all these keys (and any values) will be returned.
        
        :return: A generator (for efficiency) of matching nodes.
        """
        for osm_id in self._search_all_tag_keys("node_tags", keys):
            yield self.node(osm_id)

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

    def nodes_in_bounding_box(self, minlon, maxlon, minlat, maxlat):
        """Find all nodes which fall in the bounding box, giving a generator
        of :class:`Node` instances.
        """
        result = self._connection.execute("select * from nodes where longitude >= ? and longitude <= ? and latitude >= ? and latitude <= ?",
            (_to_num(minlon), _to_num(maxlon), _to_num(minlat), _to_num(maxlat)))
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
            way = osm_id
        else:
            way = self.way(osm_id)
        def provider():
            for node_id in way.nodes:
                yield self.node(node_id)
        return richobjs.RichWay(way, provider())
        
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
        relation = self.relation(osm_id)
        def provide_full_members():
            for member in relation.members:
                if member.type == "node":
                    yield self.node(member.ref)
                elif member.type == "way":
                    yield self.complete_way(member.ref)
                elif member.type == "relation":
                    yield self.complete_relation(member.ref)
        return richobjs.RichRelation(relation, provide_full_members())

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


def _node_ids_in_bb(db, minlon, maxlon, minlat, maxlat):
    result = db.connection.execute("select osm_id from nodes where longitude >= ? and longitude <= ? and latitude >= ? and latitude <= ?",
        (_to_num(minlon), _to_num(maxlon), _to_num(minlat), _to_num(maxlat))).fetchall()
    return set(row[0] for row in result)

def _chunk_in_request(db, search_set, query):
    chunk = 10240
    search = list(search_set)
    out = set()
    while len(search) > 0:
        if len(search) <= chunk:
            this_search, search = search, []
        else:
            this_search, search = search[:chunk], search[chunk:]
        this_search_string = ",".join(str(x) for x in this_search)
        out.update(row[0] for row in
            db.connection.execute(query.format(this_search_string)).fetchall() )
    return out

def _ways_from_nodes(db, node_set):
    return _chunk_in_request(db, node_set, "select osm_id from ways where noderef in ({})")

def _all_nodes_from_ways(db, way_set):
    return _chunk_in_request(db, way_set, "select noderef from ways where osm_id in ({})")

def extract(db, minlon, maxlon, minlat, maxlat, out_filename):
    """Create a new database based on the parsed bounding box.  We extract all
    ways which feature at least one node in the bounding box.  Then all nodes
    in the bounding box, and all nodes required for these ways, are returned.
    Any relation which features a node or way in the dataset is also returned
    (but such a relation is allowed to also have a way/node which is not in the
    dataset).

    As might be expected, this can be rather memory intensive.

    :param db: A :class:`OSM_SQLite` object to extract from.
    :param out_filename: The new database to construct.
    """
    def gen():
        yield _digest.OSM("osm", {"version":db.osm.version, "generator":db.osm.generator+" / extract by OSMDigest"})
        yield _digest.Bounds("bounds", {"minlon":minlon, "maxlon":maxlon, "minlat":minlat, "maxlat":maxlat})

        valid_node_ids = _node_ids_in_bb(db, minlon, maxlon, minlat, maxlat)
        valid_way_ids = _ways_from_nodes(db, valid_node_ids)
        valid_node_ids = valid_node_ids | _all_nodes_from_ways(db, valid_way_ids)

        for nodeid in valid_node_ids:
            yield db.node(nodeid)
        for wayid in valid_way_ids:
            yield db.way(wayid)
        for relation in db.relations():
            if any( ( m.type=="node" and m.ref in valid_node_ids ) or
                ( m.type=="way" and m.ref in valid_way_ids ) for m in relation.members ):
                yield relation
        
    for _ in _convert_gen_from_any_source(gen(), out_filename):
        pass

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


def _schema_db(connection):
    """Build all the tables and indexes"""
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

def _convert_gen_from_any_source(gen, db_filename):
    connection = _sqlite3.connect(db_filename)
    try:
        _schema_db(connection)
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

def convert_gen(xml_file, db_filename):
    """Convert the passed XML file to a sqlite3 database file.  As this is
    rather slow, this function is a generator which will `yield` information
    on its progress.

    :param xml_file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.
    :param db_filename: Filename to pass to the `sqlite3` module.
    """
    gen = _digest.parse(xml_file)
    yield from _convert_gen_from_any_source(gen, db_filename)

def convert(xml_file, db_filename):
    """Convert the passed XML file to a sqlite3 database file.

    :param xml_file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.
    :param db_filename: Filename to pass to the `sqlite3` module.
    """
    for x in convert_gen(xml_file, db_filename):
        pass
