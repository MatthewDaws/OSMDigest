import pytest

import osmdigest.geometry as geometry
import osmdigest.digest as digest
import osmdigest.richobjs as richobjs

@pytest.fixture
def node():
    node = digest.Node({"id":"1234", "lon":"1.1", "lat":"1.2"})
    node.add_tag("name", "bob")
    node.add_tag("key0", "value0")
    return node

def test_node_to_geojson(node):
    json = geometry.geojson_from_node(node)
    assert(json == {"geometry": {
               "type": "Point",
               "coordinates": [1.1, 1.2]
           },
           "properties": {
               "name":"bob" , "key0":"value0", "osm_id":1234
           }})

@pytest.fixture
def way():
    way = digest.Way({"id":"432"})
    way.add_node(1)
    way.add_node(2)
    way.add_node(6)
    way.add_tag("name", "dave")
    way.add_tag("key1", "value1")
    return way

@pytest.fixture
def richway(way):
    def provider():
        yield digest.Node({"id":"1", "lon":"1.1", "lat":"1.2"})
        yield digest.Node({"id":"2", "lon":"1.3", "lat":"1.4"})
        node = digest.Node({"id":"6", "lon":"1.5", "lat":"1.6"})
        node.add_tag("name", "bob")
        node.add_tag("key0", "value0")
        yield node
    return richobjs.RichWay(way, provider())

def test_way_to_geojson(way):
    json = geometry.geojson_from_way(way)
    assert(json == {"geometry":{}, "properties":{"name":"dave", "osm_id": 432, "key1":"value1", "nodes":[1,2,6]}})

def test_richway_to_geojson(richway):
    json = geometry.geojson_from_way(richway)
    assert(json == {"geometry":{"type":"LineString", "coordinates":[[1.1,1.2], [1.3,1.4], [1.5,1.6]]},
        "properties":{"name":"dave", "key1":"value1", "osm_id":432}})
    json = geometry.geojson_from_way(richway, polygonise=True)
    assert(json == {"geometry":{"type":"Polygon", "coordinates":[[[1.1,1.2], [1.3,1.4], [1.5,1.6]]]},
        "properties":{"name":"dave", "key1":"value1", "osm_id":432}})
    
def test_geoseries_from_way(richway):
    gs = geometry.geoseries_from_way(richway)
    assert(set(gs.keys()) == {"name", "key1", "geometry", "osm_id"})
    assert(gs["name"] == "dave")
    assert(gs["key1"] == "value1")
    assert(gs["osm_id"] == 432)
    assert(list(gs["geometry"].coords) == [(1.1,1.2), (1.3,1.4), (1.5,1.6)] )