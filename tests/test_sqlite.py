import pytest
import os
import io
import datetime

import osmdigest.sqlite as sqlite

@pytest.fixture
def xml_file():
    try:
        os.remove("test.db")
    except FileNotFoundError:
        pass
    try:
        yield os.path.join("tests", "example.osm")
    finally:
        try:
            os.remove("test.db")
        except Exception:
            pass

def test_osm(xml_file):
    sqlite.convert(xml_file, "test.db")

    db = sqlite.OSM_SQLite("test.db")

    assert(db.osm.version == "0.6")
    assert(db.osm.generator == "CGImap 0.0.2")
    assert(db.osm.timestamp is None)

    assert(db.bounds.min_latitude == 54.0889580)
    assert(db.bounds.min_longitude == 12.2487570)
    assert(db.bounds.max_latitude == 54.0913900)
    assert(db.bounds.max_longitude == 12.2524800)
    
test_xml = """<osm version="0.7" generator="inline" timestamp="2017-05-01T20:43:12Z">
        <bounds minlat="0" minlon="0" maxlat="10" maxlon="10" />
        <node id="1" lat="1.1" lon="1.2" />
        <node id="2" lat="1.3" lon="1.4" />
        <node id="3" lat="1.5" lon="1.6" />
        <node id="4" lat="1.7" lon="1.8" />
        <node id="5" lat="1.9" lon="2.0" />
        <way id="5">
            <nd ref="1" /><nd ref="2" />
            <tag k="type" v="v1" />
            <tag k="name" v="bob" />
        </way>
        <way id="6">
            <nd ref="1" /><nd ref="3" />
            <tag k="type" v="v2" />
            <tag k="name" v="bob" />
        </way>
        <way id="8">
            <nd ref="3" /><nd ref="4" /><nd ref="5" />
            <tag k="type" v="v2" />
            <tag k="name" v="dave" />
        </way>
        <relation id="2">
            <member type="node" ref="1" role="bob" />
            <tag k="highway" v="road" />
            <tag k="name" v="bob" />
        </relation>
        <relation id="4">
            <member type="way" ref="5" role="" />
            <tag k="highway" v="road" />
            <tag k="name" v="dave" />
        </relation>
    </osm>"""

@pytest.fixture
def test_xml_file():
    try:
        yield io.StringIO(test_xml)
    finally:
        try:
            os.remove("test.db")
        except Exception:
            pass

@pytest.fixture
def test_db(test_xml_file):
    sqlite.convert(test_xml_file, "test.db")
    db = sqlite.OSM_SQLite("test.db")
    try:
        yield db
    finally:
        db.close()

def test_osm_timestamp(test_db):
    assert(test_db.osm.version == "0.7")
    assert(test_db.osm.generator == "inline")
    assert(test_db.osm.timestamp == datetime.datetime(2017,5,1,20,43,12))

@pytest.fixture
def db(xml_file):
    sqlite.convert(xml_file, "test.db")
    db = sqlite.OSM_SQLite("test.db")
    try:
        yield db
    finally:
        db.close()

def test_nodes(db):
    node = db.node(298884269)
    assert(node.osm_id == 298884269)
    assert(node.longitude == 12.2482632)
    assert(node.latitude == 54.0901746)
    
    node = db.node(1831881213)
    assert(node.osm_id == 1831881213)
    assert(node.longitude == 12.2539381)
    assert(node.latitude == 54.0900666)
    assert(node.tags == {"name": "Neu Broderstorf", "traffic_sign": "city_limit"})
    
    with pytest.raises(KeyError):
        node = db.node(5)

def test_nodes_in_bb(db):
    nodes = list(db.nodes_in_bounding_box(12.248263, 12.248264, 54.090174, 54.090175))
    assert(set(node.osm_id for node in nodes) == {298884269})

def test_extract(db):
    try:
        sqlite.extract(db, 12.248263, 12.248264, 54.090174, 54.090175, "test_extract.db")
        with sqlite.OSM_SQLite("test_extract.db") as testdb:
            assert(set(node.osm_id for node in testdb.nodes()) == {298884269})
    finally:
        try:
            os.remove("test_extract.db")
        except:
            pass

def test_nodes_iterator(db):
    osm_ids = { node.osm_id for node in db.nodes() }
    assert(osm_ids == {298884269, 1831881213, 261728686, 298884272})

def test_ways(db):
    way = db.way(26659127)
    assert(way.nodes == [292403538, 298884289, 261728686])
    assert(way.tags == {"highway": "unclassified", "name": "Pastower Straße"})

def test_ways_iterator(test_db):
    db = test_db

    ways = list(db.ways())
    assert(ways[0].osm_id == 5)
    assert(ways[0].nodes == [1,2])
    assert(ways[1].osm_id == 6)
    assert(ways[1].nodes == [1,3])
    assert(ways[2].osm_id == 8)
    assert(ways[2].nodes == [3,4,5])
    assert(len(ways) == 3)
        
def test_way_complete(test_db):
    db = test_db

    way = db.complete_way(5)
    assert(way.complete_nodes[0].longitude == 1.2)
    assert(way.complete_nodes[0].latitude == 1.1)
    assert(way.complete_nodes[1].longitude == 1.4)
    assert(way.complete_nodes[1].latitude == 1.3)
    
    way = db.complete_way(db.way(5))
    assert(way.complete_nodes[0].longitude == 1.2)
    assert(way.complete_nodes[0].latitude == 1.1)
    assert(way.complete_nodes[1].longitude == 1.4)
    assert(way.complete_nodes[1].latitude == 1.3)
    
def test_relations(db):
    rel = db.relation(56688)
    
    for m in rel.members:
        assert(m.role=="")
    assert({ m.ref for m in rel.members if m.type == "way" } == {4579143})
    assert({ m.ref for m in rel.members if m.type == "relation" } == set())
    assert({ m.ref for m in rel.members if m.type == "node" } == {294942404, 249673494, 364933006})

    assert(rel.tags == {"name": "Küstenbus Linie 123",
        "network": "VVW",
        "operator": "Regionalverkehr Küste",
        "ref": "123",
        "route": "bus",
        "type": "route" })

def test_relations_iterator(test_db):
    db = test_db

    rels = list(db.relations())
    assert(rels[0].osm_id == 2)
    assert(rels[0].members[0].type == "node")
    assert(rels[0].members[0].ref == 1)
    assert(rels[0].members[0].role == "bob")
    assert(len(rels[0].members) == 1)
    assert(rels[1].osm_id == 4)
    assert(rels[1].members[0].type == "way")
    assert(rels[1].members[0].ref == 5)
    assert(rels[1].members[0].role == "")
    assert(len(rels[1].members) == 1)
    assert(len(rels) == 2)

def test_relation_complete(test_db):
    db = test_db

    rel = db.complete_relation(4)
    assert(rel.complete_members[0].osm_id == 5)
    assert(rel.complete_members[0].complete_nodes[0].longitude == 1.2)
    assert(rel.complete_members[0].complete_nodes[0].latitude == 1.1)

def search_relation_tags(test_db):
    rels = test_db.search_relation_tags({"highway": "road"})
    assert(set( rel.osm_id for rel in rels ) == {2, 4})

    rels = test_db.search_relation_tags({"highway": "road", "name": "bob"})
    assert(set( rel.osm_id for rel in rels ) == {2})

def search_way_tags(test_db):
    ways = test_db.search_way_tags({"name": "bob"})
    assert(set(way.osm_id for way in ways) == {5, 6})

    ways = test_db.search_way_tags({"type": "v2"})
    assert(set(way.osm_id for way in ways) == {6, 8})

    ways = test_db.search_way_tags({"name": "bob", "type": "v2"})
    assert(set(way.osm_id for way in ways) == {6})

def search_node_tags(db):
    nodes = db.search_way_tags({"traffic_sign": "city_limit"})
    assert(set(node.osm_id for node in nodes) == {1831881213})

    nodes = db.search_way_tags({"traffic_sign": "city"})
    assert(len(nodes) == 0)

    with pytest.raises(ValueError):
        db.search_way_tags({})

def test_search_way_tag_keys(test_db):
    out = test_db.search_way_tag_keys({"type"})
    assert(set(way.osm_id for way in out) == {5,6,8})
    out = test_db.search_way_tag_keys({"type", "other"})
    assert(set(way.osm_id for way in out) == set())