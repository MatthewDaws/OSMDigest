import pytest
import os
import io

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

    db = sqlite.OSM_SQLITE("test.db")
    
    assert(db.osm.version == "0.6")
    assert(db.osm.generator == "CGIMap 0.0.2")
    assert(db.osm.timestamp is None)

def test_osm_timestamp(xml_file):
    io.StringIO("""<osm version="0.7", generator="inline", timestamp=")