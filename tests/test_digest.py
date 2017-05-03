import pytest

import osmdigest.digest as digest
import os

def test_BaseOSMElement():
    el = digest.BaseOSMElement({"id":"1234"})
    assert(el.osm_id == 1234)
    el.tags["bob"] = 55
    assert(el.tags["bob"] == 55)
    assert(len(el.tags) == 1)

def test_Node():
    el = digest.Node({"id":"1234", "lat":"12.4635251", "lon":"47.21753211"})
    assert(el.latitude == pytest.approx(12.4635251))
    assert(el.longitude == pytest.approx(47.21753211))
    el.tags["bob"] = "asa"
    assert(str(el) == "Node(1234 @ [12.4635251,47.21753211] {'bob': 'asa'})")
    
def test_Way():
    el = digest.Way({"id":"5432"})
    el.tags["bob"] = "asa"
    el.nodes.append(4321)
    assert(str(el) == "Way(5432 ->  [4321] {'bob': 'asa'})")
    
def test_Relation():
    el = digest.Relation({"id":"5432"})
    el.tags["bob"] = "asa"
    el.members.append(digest.Member(type="way", ref=9876, role="fish"))
    assert(str(el) == "Relation(5432 ->  [Member(type='way', ref=9876, role='fish')] {'bob': 'asa'})")

def check_example(out):
    assert(isinstance(out[0], digest.OSM))
    assert(isinstance(out[1], digest.Bounds))
    
    assert(out[2].osm_id == 298884269)
    assert(out[2].longitude == pytest.approx(12.2482632))
    assert(out[2].latitude == pytest.approx(54.0901746))
    assert(out[4].osm_id == 1831881213)
    assert(out[4].tags["name"] == "Neu Broderstorf")
    assert(out[4].tags["traffic_sign"] == "city_limit")
    
    assert(out[6].osm_id == 26659127)
    assert(out[6].tags == {"highway":"unclassified", "name":"Pastower Straße"})
    assert(out[6].nodes == [292403538, 298884289, 261728686])
    
    assert(out[7].osm_id == 56688)
    assert(out[7].tags["ref"] == "123")
    assert(out[7].members[0] == digest.Member("node",294942404,""))
    assert(out[7].members[1] == digest.Member("node",364933006,""))
    assert(out[7].members[2] == digest.Member("way",4579143,""))
    assert(out[7].members[3] == digest.Member("node",249673494,""))

    assert(len(out) == 8)

def test_parse():
    out = []
    for x in digest.parse(os.path.join("tests", "example.osm")):
        out.append(x)
    check_example(out)
    
def test_parse_gz():
    out = []
    for x in digest.parse(os.path.join("tests", "example.osm.gz")):
        out.append(x)
    check_example(out)
    
def test_parse_xz():
    out = []
    for x in digest.parse(os.path.join("tests", "example.osm.xz")):
        out.append(x)
    check_example(out)

def test_parse_bz2():
    out = []
    for x in digest.parse(os.path.join("tests", "example.osm.bz2")):
        out.append(x)
    check_example(out)
