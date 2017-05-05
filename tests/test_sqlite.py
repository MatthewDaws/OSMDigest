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

    db = sqlite.OSM_SQLITE("test.db")
    
    assert(db.osm.version == "0.6")
    assert(db.osm.generator == "CGImap 0.0.2")
    assert(db.osm.timestamp is None)

def test_osm_timestamp(xml_file):
    file = io.StringIO("""<osm version="0.7" generator="inline" timestamp="2017-05-01T20:43:12Z">
        <bounds minlat="0" minlon="0" maxlat="10" maxlon="10" />
    </osm>""")
    sqlite.convert(file, "test.db")
    
    db = sqlite.OSM_SQLITE("test.db")
    
    assert(db.osm.version == "0.7")
    assert(db.osm.generator == "inline")
    assert(db.osm.timestamp == datetime.datetime(2017,5,1,20,43,12))