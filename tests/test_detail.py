import pytest
import os
import datetime

import osmdigest.detail as detail

def test_OSMElement():
    el = detail.OSMElement("tag", {"id":"298884269", "lat":"54.0901746", "lon":"12.2482632", "user":"SvenHRO",
                        "uid":"46882", "visible":"true", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z"})
    assert( el.osm_id == 298884269 )
    assert( el.name == "tag" )
    assert( el.subobjs == [] )
    assert( el.keys == {"lon", "lat"} )
    assert( el.metadata == {"user":"SvenHRO", "uid":46882, "version":1, "changeset":676636,
                            "timestamp": datetime.datetime(2008,9,21,21,37,45)} )

def test_OSMElement_user_optional():
    el = detail.OSMElement("tag", {"id":"298884269", "lat":"54.0901746", "lon":"12.2482632",
                        "visible":"true", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z"})
    assert( el.metadata == {"user":"", "uid":0, "version":1, "changeset":676636,
                            "timestamp": datetime.datetime(2008,9,21,21,37,45)} )
    
def test_OSMElement_must_be_visible():
    with pytest.raises(ValueError):
        detail.OSMElement("tag", {"id":"298884269", "lat":"54.0901746", "lon":"12.2482632",
                        "visible":"false", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z"})
    
def test_OSMElement_other_parse_error():
    with pytest.raises(ValueError):
        detail.OSMElement("tag", {"id":"2988sgjaf84269", "lat":"54.0901746", "lon":"12.2482632",
                        "visible":"false", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z"})

def test_Node():
    el = detail.Node("node", {"id":"298884269", "lat":"54.0901746", "lon":"12.2482632", "user":"SvenHRO",
                        "uid":"46882", "visible":"true", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z"})
    assert(el.latitude == pytest.approx(54.0901746))
    assert(el.longitude == pytest.approx(12.2482632))
    assert( str(el) == "Node(298884269 @ [54.0901746,12.2482632])" )
    
def test_Node_must_be_correct_name():
    with pytest.raises(ValueError):
        detail.Node("tag", {"id":"298884269", "lat":"54.0901746", "lon":"12.2482632", "user":"SvenHRO",
                        "uid":"46882", "visible":"true", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z"})

def test_Node_mustnt_have_extra_attributes():
    with pytest.raises(ValueError):
        detail.Node("tag", {"id":"298884269", "lat":"54.0901746", "lon":"12.2482632", "user":"SvenHRO",
                        "uid":"46882", "visible":"true", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z", "extra":"dave"})

def test_Way():
    el = detail.Way("way", {"id":"298884269", "user":"SvenHRO",
                        "uid":"46882", "visible":"true", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z"})
    assert( str(el) == "Way(298884269,[])" )

def test_Way_wrong_name():
    with pytest.raises(ValueError):
        detail.Way("way2", {"id":"298884269", "user":"SvenHRO",
                        "uid":"46882", "visible":"true", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z"})

def test_Way_extra_attribute():
    with pytest.raises(ValueError):
        detail.Way("way", {"id":"298884269", "user":"SvenHRO",
                        "uid":"46882", "visible":"true", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z", "extra":"5"})

def test_Relation():
    el = detail.Relation("relation", {"id":"298884269", "user":"SvenHRO",
                        "uid":"46882", "visible":"true", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z"})
    assert( str(el) == "Relation(298884269,[])" )

def test_Relation_wrong_name():
    with pytest.raises(ValueError):
        detail.Relation("relation2", {"id":"298884269", "user":"SvenHRO",
                        "uid":"46882", "visible":"true", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z"})
    
def test_Relation_extra_attribute():
    with pytest.raises(ValueError):
        detail.Relation("relation", {"id":"298884269", "user":"SvenHRO",
                        "uid":"46882", "visible":"true", "version":"1", "changeset":"676636",
                        "timestamp":"2008-09-21T21:37:45Z", "extra":"5"})

def test_Bounds():
    el = detail.Bounds("bounds", {"minlat":"54.0889580", "minlon":"12.2487570", "maxlat":"54.0913900", "maxlon":"12.2524800"})
    assert(el.min_latitude == pytest.approx(54.0889580))
    assert(el.min_longitude == pytest.approx(12.2487570))
    assert(el.max_latitude == pytest.approx(54.0913900))
    assert(el.max_longitude == pytest.approx(12.2524800))
    
def test_Bounds_parse_failures():
    try:
        detail.Bounds("bounds2", {"minlat":"54.0889580", "minlon":"12.2487570", "maxlat":"54.0913900", "maxlon":"12.2524800"})
    except ValueError as ex:
        assert(str(ex) == "Should be of type 'bounds'")
    try:
        detail.Bounds("bounds", {"extra":"5", "minlat":"54.0889580", "minlon":"12.2487570", "maxlat":"54.0913900", "maxlon":"12.2524800"})
    except ValueError as ex:
        assert(str(ex) == "Unexpected extra attributes for 'bounds' element: {'extra'}")

def test_Tag():
    el = detail.Tag("tag", {"k": "traffic_sign", "v": "city_limit"})
    assert(el.key == "traffic_sign")
    assert(el.value == "city_limit")
    assert(str(el) == "Tag(traffic_sign->city_limit)")
    
def test_Tag_parse_failures():
    try:
        detail.Tag("tag2", {"k": "traffic_sign", "v": "city_limit"})
    except ValueError as ex:
        assert(str(ex) == "Should be of type 'tag'")
    try:
        detail.Tag("tag", {"extra":"bob", "k": "traffic_sign", "v": "city_limit"})
    except ValueError as ex:
        assert(str(ex) == "Unexpected extra attributes for 'tag' element: {'extra'}")
    
def test_NodeRef():
    el = detail.NodeRef("nd", {"ref": "292403538"})
    assert(el.ref == 292403538)
    assert(str(el) == "NodeRef(292403538)")

def test_NodeRef_parse_failures():
    try:
        detail.NodeRef("nd2", {"ref": "292403538"})
    except ValueError as ex:
        assert(str(ex) == "Should be of type 'nd'")
    try:
        detail.NodeRef("nd", {"extra": "292403538"})
    except ValueError as ex:
        assert(str(ex) == "Unexpected extra attributes for 'nd' element: {'extra'}")

def test_Member():
    el = detail.Member("member", {"type":"node", "ref":"294942404", "role":""})
    assert(el.type == "node")
    assert(el.ref == 294942404)
    assert(el.role == "")

    with pytest.raises(ValueError):
        detail.Member("member2", {"type":"node", "ref":"294942404", "role":""})
    with pytest.raises(ValueError):
        detail.Member("member", {"extra":"jegw", "type":"node", "ref":"294942404", "role":""})

def test_OSM():
    el = detail.OSM("osm", {"version":"0.6", "generator":"CGImap 0.0.2"})
    assert(el.version == "0.6")
    assert(el.generator == "CGImap 0.0.2")
    assert(el.timestamp is None)

    el = detail.OSM("osm", {"version":"0.6", "generator":"osmconvert 0.8.5", "timestamp":"2017-04-25T20:43:28Z"})
    assert(el.version == "0.6")
    assert(el.generator == "osmconvert 0.8.5")
    assert(el.timestamp == datetime.datetime(2017,4,25,20,43,28))

def check_example_output(out):
    assert(isinstance(out[0], detail.OSM))
    assert(isinstance(out[1], detail.Bounds))
    
    assert(out[2].osm_id == 298884269)
    assert(out[2].longitude == pytest.approx(12.2482632))
    assert(out[2].latitude == pytest.approx(54.0901746))
    assert(isinstance(out[3], detail.Node))
    assert(out[4].osm_id == 1831881213)
    assert(out[4].subobjs[0].key == "name")
    assert(out[4].subobjs[0].value == "Neu Broderstorf")
    assert(str(out[4].subobjs[1]) == "Tag(traffic_sign->city_limit)")
    assert(isinstance(out[5], detail.Node))
    
    assert(out[6].osm_id == 26659127)
    assert(out[6].subobjs[0].ref == 292403538)
    assert(str(out[6].subobjs[3]) == "Tag(highway->unclassified)")
    assert(str(out[6].subobjs[4]) == "Tag(name->Pastower Straße)")

    assert(out[7].osm_id == 56688)
    assert(out[7].subobjs[0].ref == 294942404)
    assert(out[7].subobjs[2].type == "way")
    assert(str(out[7].subobjs[4]) == "Tag(name->Küstenbus Linie 123)")
    assert(len(out[7].subobjs) == 10)
    
    assert(len(out) == 8)

def test_example():
    with detail.Parser(os.path.join("tests", "example.osm")) as parser:
        out = list(parser)
    check_example_output(out)
    
def test_example_xz():
    with detail.Parser(os.path.join("tests", "example.osm.xz")) as parser:
        out = list(parser)
    check_example_output(out)
    
def test_example_gz():
    with detail.Parser(os.path.join("tests", "example.osm.gz")) as parser:
        out = list(parser)
    check_example_output(out)
    
def test_example_bz2():
    with detail.Parser(os.path.join("tests", "example.osm.bz2")) as parser:
        out = list(parser)
    check_example_output(out)