import pytest
import os, io

import osmdigest.pythonify as pythonify

# Don't really need this, but it's fun to show how a test fixture works
@pytest.fixture()
def pickle_file():
    yield None
    os.remove("test.pic.xz")

def test_pickle(pickle_file):
    obj = {"a":1, "b":7}
    pythonify.pickle(obj, "test.pic.xz")
    obj_back = pythonify.unpickle("test.pic.xz")
    assert( obj == obj_back )
    
test_xml = """<osm version="0.6" generator="CGImap 0.0.2">
<bounds minlat="54.0889580" minlon="12.2487570" maxlat="54.0913900" maxlon="12.2524800"/>
<node id="1" lat="54.0901746" lon="12.2482632" version="1" changeset="676636" timestamp="2008-09-21T21:37:45Z">
  <tag k="name" v="bob" />
  <tag k="traffic_sign" v="city_limit" />
</node>
<node id="2" lat="54.0901746" lon="12.2482" version="1" changeset="676636" timestamp="2008-09-21T21:37:45Z">
  <tag k="name" v="dave" />
  <tag k="traffic_sign" v="speed_limit" />
</node>
<node id="10" lat="54.0901746" lon="12.2482" version="1" changeset="676636" timestamp="2008-09-21T21:37:45Z" />
<way id="1" version="5" changeset="4142606" timestamp="2010-03-16T11:47:08Z">
  <nd ref="1" />
  <nd ref="2" />
  <tag k="highway" v="unclassified" />
</way>
<way id="2" version="5" changeset="4142606" timestamp="2010-03-16T11:47:08Z">
  <nd ref="1" />
  <nd ref="4" />
  <nd ref="7" />
  <nd ref="1" />
  <tag k="highway" v="road" />
</way>
<relation id="1" version="28" changeset="6947637" timestamp="2011-01-12T14:23:49Z">
  <tag k="route" v="bus" />
  <tag k="name" v="64" />
</relation>
<relation id="2" version="28" changeset="6947637" timestamp="2011-01-12T14:23:49Z">
  <member type="node" ref="1" role=""/>
  <member type="way" ref="4" role="fish"/>
  <tag k="route" v="bus" />
  <tag k="name" v="68" />
</relation>
</osm>
"""

@pytest.fixture
def xml_file():
    yield io.StringIO(test_xml)

def lists_agree_up_to_ordering(l1, l2):
    """Use of dictionaries mean that returned lists might be in any order,
    so we need to allow order to vary..."""
    if len(l1) != len(l2):
        return False
    li1, li2 = list(l1), list(l2)
    try:
        for x in li1:
            index = li2.index(x)
            del li2[index]
        return True
    except ValueError:
        return False
        
def test_lists_agree_up_to_ordering():
    assert(lists_agree_up_to_ordering([1,2], [1,2]))
    assert(lists_agree_up_to_ordering([1,2], [2,1]))
    assert(not lists_agree_up_to_ordering([1,2], [1,2,3]))
    assert(not lists_agree_up_to_ordering([1,2], [2,3]))
    
def test_by_key_pair(xml_file):
    tags = pythonify.Tags(xml_file)
    assert( tags.nodes(("a", "b")) == [] )
    assert( tags.nodes(("traffic_sign", "city_limit")) == [1] )
    assert( tags.nodes(("route", "bus")) == [] )
    
    assert( tags.ways(("a", "b")) == [] )
    assert( tags.ways(("highway", "unclassified")) == [1] )
    assert( tags.ways(("route", "bus")) == [] )
    
    assert( tags.relations(("a", "b")) == [] )
    assert( tags.relations(("highway", "unclassified")) == [] )
    assert( lists_agree_up_to_ordering(tags.relations(("route", "bus")), [1, 2]) )

def test_by_key(xml_file):
    tags = pythonify.Tags(xml_file)
    assert( lists_agree_up_to_ordering(tags.nodes_from_key("name"), [("bob", 1), ("dave", 2)]) )
    assert( tags.nodes_from_key("highway") == [] )
    assert( lists_agree_up_to_ordering(tags.ways_from_key("highway"), [("unclassified", 1), ("road", 2)]) )
    assert( lists_agree_up_to_ordering(tags.relations_from_key("route"), [("bus", 1), ("bus", 2)]) )
    assert( lists_agree_up_to_ordering(tags.relations_from_key("name"), [("64", 1), ("68", 2)]) )
    
def test_from_key_value(xml_file):
    tags = pythonify.Tags(xml_file)
    assert( tags.from_key_value("name", "bob") == [("node", 1)] )
    assert( lists_agree_up_to_ordering(tags.from_key_value("route", "bus"), [("relation", 1), ("relation", 2)]) )
    
def test_from_key(xml_file):
    tags = pythonify.Tags(xml_file)
    assert( lists_agree_up_to_ordering(tags.from_key("name"), [("node", "bob", 1), ("node", "dave", 2),
           ("relation", "64", 1), ("relation", "68", 2)]) )
    assert( lists_agree_up_to_ordering(tags.from_key("highway"),
        [("way", "unclassified", 1), ("way", "road", 2)]) )
    
@pytest.fixture
def tags(xml_file):
    yield pythonify.Tags(xml_file)
    
def test_TagsById(tags):
    tags = pythonify.TagsById(tags)
    assert(tags.node(1) == {"name":"bob", "traffic_sign":"city_limit"})
    assert(tags.node(3) == {})
    assert(tags.way(2) == {"highway":"road"})
    assert(tags.way(3) == {})
    assert(tags.relation(1) == {"name":"64", "route":"bus"})
    assert(tags.relation(3) == {})

def test_all_node_tags(tags):
    s = tags.all_node_tags
    assert(s == {("name","bob"), ("traffic_sign", "city_limit"),
                 ("name","dave"), ("traffic_sign", "speed_limit")})
    
def test_all_node_tag_keys(tags):
    s = tags.all_node_tag_keys
    assert(s == {"name", "traffic_sign"})

def test_all_way_tags(tags):
    s = tags.all_way_tags
    assert(s == {("highway","unclassified"), ("highway", "road")})
    
def test_all_way_tag_keys(tags):
    s = tags.all_way_tag_keys
    assert(s == {"highway"})
    
def test_all_relation_tags(tags):
    s = tags.all_relation_tags
    assert(s == {("route","bus"), ("name", "64"), ("name", "68")})
    
def test_all_relation_tag_keys(tags):
    s = tags.all_relation_tag_keys
    assert(s == {"route", "name"})

def check_nodes_object(nodes):
    assert( nodes[1] == (12.2482632, 54.0901746) )
    assert( nodes[2] == (12.2482, 54.0901746) )
    with pytest.raises(KeyError):
        nodes[3]
    assert( nodes[10] == (12.2482, 54.0901746) )

def test_Nodes(xml_file):
    nodes = pythonify.Nodes(xml_file)
    check_nodes_object(nodes)

def check_Nodes_iter(li):
    assert(li[0] == (1, (12.2482632, 54.0901746)))
    assert(li[1] == (2, (12.2482, 54.0901746)))
    assert(li[2] == (10, (12.2482, 54.0901746)))
    assert(len(li) == 3)    

def test_Nodes_iter(xml_file):
    nodes = pythonify.Nodes(xml_file)
    check_Nodes_iter(list(nodes))
        
def test_NodesPacked(xml_file):
    nodes = pythonify.NodesPacked(xml_file)
    check_nodes_object(nodes)

def test_NodesPacked_from_Nodes(xml_file):
    nodes1 = pythonify.Nodes(xml_file)
    nodes = pythonify.NodesPacked.from_Nodes(nodes1)
    check_nodes_object(nodes)

def test_NodesPacked_iter(xml_file):
    nodes = pythonify.NodesPacked(xml_file)
    check_Nodes_iter(list(nodes))

def test_Ways(xml_file):
    ways = pythonify.Ways(xml_file)
    assert( ways[1] == [1,2] )
    assert( ways[2] == [1,4,7,1] )
    with pytest.raises(KeyError):
        ways[3]
        
def test_Ways_iter(xml_file):
    ways = pythonify.Ways(xml_file)
    li = list(ways)    
    assert(li[0] == (1,[1,2]))
    assert(li[1] == (2,[1,4,7,1]))
    assert(len(li) == 2)

def test_Relations(xml_file):
    relations = pythonify.Relations(xml_file)
    assert( relations[1] == [] )
    assert( len(relations[2]) == 2 )
    assert( relations[2][0].type == "node" )
    assert( relations[2][1].role == "fish" )
    with pytest.raises(KeyError):
        relations[3]

def test_Relations_iter(xml_file):
    relations = pythonify.Relations(xml_file)
    li = list(relations)    
    assert(li[0] == (1,[]))
    assert(li[1][0] == 2)
    assert(len(li) == 2)

def test_pythonify_and_pickle():
    filename = os.path.join("tests", "example.osm")
    names = pythonify.pythonify_and_pickle(filename, "test_processed")
    for name, typpe in zip(names, [pythonify.NodesPacked, pythonify.Ways,
                                   pythonify.Relations, pythonify.Tags]):
        obj = pythonify.unpickle(name)
        assert(isinstance(obj, typpe))
        os.remove(name)