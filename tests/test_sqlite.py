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
    yield os.path.join("tests","example.osm")
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
    
def test_osm_timestamp(xml_file):
    file = io.StringIO("""<osm version="0.7" generator="inline" timestamp="2017-05-01T20:43:12Z">
        <bounds minlat="0" minlon="0" maxlat="10" maxlon="10" />
    </osm>""")
    sqlite.convert(file, "test.db")

    db = sqlite.OSM_SQLite("test.db")

    assert(db.osm.version == "0.7")
    assert(db.osm.generator == "inline")
    assert(db.osm.timestamp == datetime.datetime(2017,5,1,20,43,12))

def test_nodes(xml_file):
    sqlite.convert(xml_file, "test.db")
    db = sqlite.OSM_SQLite("test.db")

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
