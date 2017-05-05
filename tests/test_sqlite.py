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
    yield os.path.join("tests", "example.osm")
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
        <way id="5">
            <nd ref="1" /><nd ref="2" />
        </way>
        <way id="6">
            <nd ref="1" /><nd ref="3" />
        </way>
        <way id="8">
            <nd ref="3" /><nd ref="4" /><nd ref="5" />
        </way>
        <relation id="2">
            <member type="node" ref="1" role="bob" />
        </relation>
        <relation id="4">
            <member type="way" ref="2" role="" />
        </relation>
    </osm>"""

@pytest.fixture
def test_xml_file():
    yield io.StringIO(test_xml)
    try:
        os.remove("test.db")
    except Exception:
        pass

def test_osm_timestamp(test_xml_file):
    sqlite.convert(test_xml_file, "test.db")
    db = sqlite.OSM_SQLite("test.db")

    assert(db.osm.version == "0.7")
    assert(db.osm.generator == "inline")
    assert(db.osm.timestamp == datetime.datetime(2017,5,1,20,43,12))

@pytest.fixture
def db(xml_file):
    sqlite.convert(xml_file, "test.db")
    db = sqlite.OSM_SQLite("test.db")
    yield db
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

def test_nodes_iterator(db):
    osm_ids = { node.osm_id for node in db.nodes() }
    assert(osm_ids == {298884269, 1831881213, 261728686, 298884272})

def test_ways(db):
    way = db.way(26659127)
    assert(way.nodes == [292403538, 298884289, 261728686])
    assert(way.tags == {"highway": "unclassified", "name": "Pastower Straße"})

def test_ways_iterator(test_xml_file):
    sqlite.convert(test_xml_file, "test.db")
    db = sqlite.OSM_SQLite("test.db")

    ways = list(db.ways())
    assert(ways[0].osm_id == 5)
    assert(ways[0].nodes == [1,2])
    assert(ways[1].osm_id == 6)
    assert(ways[1].nodes == [1,3])
    assert(ways[2].osm_id == 8)
    assert(ways[2].nodes == [3,4,5])
    assert(len(ways) == 3)
        
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

def test_relations_iterator(test_xml_file):
    sqlite.convert(test_xml_file, "test.db")
    db = sqlite.OSM_SQLite("test.db")

    rels = list(db.relations())
    assert(rels[0].osm_id == 2)
    assert(rels[0].members[0].type == "node")
    assert(rels[0].members[0].ref == 1)
    assert(rels[0].members[0].role == "bob")
    assert(len(rels[0].members) == 1)
    assert(rels[1].osm_id == 4)
    assert(rels[1].members[0].type == "way")
    assert(rels[1].members[0].ref == 2)
    assert(rels[1].members[0].role == "")
    assert(len(rels[1].members) == 1)
    assert(len(rels) == 2)
