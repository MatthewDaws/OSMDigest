import pytest

import osmdigest.richobjs as richobjs
import osmdigest.digest as digest

@pytest.fixture
def way():
    way = digest.Way({"id": "1234"})
    way.add_node(1)
    way.add_node(2)
    way.add_node(5)
    def provider():
        yield digest.Node({"id": "1", "lon": "1.1", "lat": "1.2"})
        yield digest.Node({"id": "2", "lon": "1.3", "lat": "1.4"})
        yield digest.Node({"id": "5", "lon": "1.5", "lat": "1.6"})
    return richobjs.RichWay(way, provider())

def test_RichWay(way):
    assert(way.osm_id == 1234)
    assert(len(way.complete_nodes) == 3)
    assert(way.complete_nodes[0].osm_id == 1)
    assert(way.complete_nodes[0].longitude == 1.1)
    assert(way.complete_nodes[0].latitude == 1.2)
    assert(way.complete_nodes[1].osm_id == 2)
    assert(way.complete_nodes[1].longitude == 1.3)
    assert(way.complete_nodes[1].latitude == 1.4)
    assert(way.complete_nodes[2].osm_id == 5)
    assert(way.complete_nodes[2].longitude == 1.5)
    assert(way.complete_nodes[2].latitude == 1.6)

def test_RichWay_mismatch():
    way = digest.Way({"id": "1234"})
    way.add_node(1)
    way.add_node(2)
    def provider():
        yield digest.Node({"id": "1", "lon": "1.1", "lat": "1.2"})
        yield digest.Node({"id": "3", "lon": "1.3", "lat": "1.4"})
    with pytest.raises(ValueError):
        richobjs.RichWay(way, provider())

    way = digest.Way({"id": "1234"})
    way.add_node(1)
    with pytest.raises(ValueError):
        richobjs.RichWay(way, provider())

def test_RichWay_centroid(way):
    assert(way.centroid()[0] == pytest.approx(1.3))
    assert(way.centroid()[1] == pytest.approx(1.4))

@pytest.fixture
def relation(way):
    relation = digest.Relation({"id": "432"})
    relation.add_member(digest.Member("node", 3, ""))
    relation.add_member(digest.Member("way", 1234, ""))
    def rels():
        yield digest.Node({"id": "3", "lon": "1.1", "lat": "1.2"})
        yield way
    return richobjs.RichRelation(relation, rels())

def test_RichRelation(relation):
    assert(relation.osm_id == 432)
    assert(relation.complete_members[0].osm_id == 3)
    assert(relation.complete_members[0].name == "node")
    assert(relation.complete_members[0].longitude == 1.1)
    assert(relation.complete_members[0].latitude == 1.2)
    assert(relation.complete_members[1].osm_id == 1234)
    assert(relation.complete_members[1].name == "way")

def test_RichRelation_centroid(relation):
    assert(relation.centroid()[0] == pytest.approx(1.2))
    assert(relation.centroid()[1] == pytest.approx(1.3))
    