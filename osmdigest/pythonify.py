"""
pythonify
~~~~~~~~

Converts an OSM XML file into a number of Python dictionaries.  This process
is slow, and (very) memory intensive, so can be split into a number of parts.
We also support saving and loading the results from compressed pickle'd files
(these should be viewed a temporary files, which are unlikely to be compatible
across different Python runtime systems.)
"""

from . import digest as _digest
import pickle as _pickle
import lzma as _lzma
import array as _array
import bisect as _bisect
from collections import defaultdict as _defaultdict

def unpickle(filename):
    """Load an object from a .xz compressed pickle file."""
    with _lzma.open(filename, "rb") as file:
        return _pickle.load(file)

def pickle(object, filename):
    """Save an object to a .xz compressed pickle file."""
    with _lzma.open(filename, "wb") as file:
        return _pickle.dump(object, file)

def _all_elements(file):
    gen = _digest.parse(file)
    osm, bounds = next(gen), next(gen)
    if not isinstance(osm, _digest.OSM) or not isinstance(bounds, _digest.Bounds):
        raise Exception("Unexpected initial two elements.  Has the XML file format changed?")
    yield from gen
    
def _all_elements_of_type(file, typename, fast=True):
    if not fast:
        yield from (element for element in _all_elements(file)
            if element.name == typename )
    else:
        for element in _all_elements(file):
            if element.name == typename:
                yield element
            else:
                if typename == "node":
                    return
                elif typename == "way" and element.name == "relation":
                    return


class Nodes():
    """Extracts the coordinate data (only) for the nodes.  Stores data in a
    dictionary.
    
    :param file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.
    :param fast: If True (default) then assume the input XML file is organised
      so that all nodes occur first, then all ways, and then all relations.
    """
    def __init__(self, file, fast=True):
        self._nodes = dict()
        for node in _all_elements_of_type(file, "node", fast):
            self._nodes[node.osm_id] = (node.longitude, node.latitude)
            
    def __getitem__(self, index):
        if index in self._nodes:
            return self._nodes[index]
        raise KeyError()
        
    def __iter__(self):
        yield from self._nodes.items()


class NodesPacked():
    """A more efficient storage method than the :class:`Nodes` implements, but
    at the cost of slower querying.
    
    :param file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.untitled0.py
    :param fast: If True (default) then assume the input XML file is organised
      so that all nodes occur first, then all ways, and then all relations.
    """
    def __init__(self, file, fast=True):
        if file is not None:
            interim_list = []
            for node in _all_elements_of_type(file, "node", fast):
                interim_list.append( (node.osm_id, node.longitude, node.latitude) )
            self._osm_ids, self._longitude, self._latitude = self._arrays_from_unordered_list(interim_list)
        else:
            self._osm_ids, self._longitude, self._latitude = None, None, None

    def __getitem__(self, index):
        i = _bisect.bisect_left(self._osm_ids, index)
        if i == len(self._osm_ids) or self._osm_ids[i] != index:
            raise KeyError()
        lon, lat = self._longitude[i], self._latitude[i]
        return lon / 1e7, lat / 1e7
    
    def __iter__(self):
        for osm_id, lon, lat in zip(self._osm_ids, self._longitude, self._latitude):
            yield (osm_id, (lon / 1e7, lat / 1e7))

    @staticmethod
    def _from_float(fl):
        if fl >= 0:
            return int(fl * 1e7 + 0.5)
        return int(fl * 1e7 - 0.5)
            
    @staticmethod
    def _arrays_from_unordered_list(input):
        input.sort(key = lambda tri : tri[0])
        osm_ids = _array.array("Q")
        lons, lats = _array.array("l"), _array.array("l")
        for (osm_id, lon, lat) in input:
            osm_ids.append(osm_id)
            lons.append(NodesPacked._from_float(lon))
            lats.append(NodesPacked._from_float(lat))
        return osm_ids, lons, lats

    @staticmethod
    def from_Nodes(nodes):
        """Construct a new instance from an instance of :class:`Nodes`."""
        new = NodesPacked(None)
        interim_list = [ (osm_id, lon, lat) for osm_id, (lon, lat) in nodes._nodes.items() ]
        new._osm_ids, new._longitude, new._latitude = NodesPacked._arrays_from_unordered_list(interim_list)
        return new


class Ways():
    """Extracts (only) the list of nodes for each way.
    
    :param file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.untitled0.py
    :param fast: If True (default) then assume the input XML file is organised
      so that all nodes occur first, then all ways, and then all relations.
    """
    def __init__(self, file, fast=True):
        self._ways = dict()
        for way in _all_elements_of_type(file, "way", fast):
            self._ways[way.osm_id] = way.nodes
            
    def __getitem__(self, index):
        if index in self._ways:
            return self._ways[index]
        raise KeyError()
        
    def __iter__(self):
        yield from self._ways.items()


class Relations():
    """Extracts (only) the list of members of each relation.
    
    :param file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.untitled0.py
    :param fast: If True (default) then assume the input XML file is organised
      so that all nodes occur first, then all ways, and then all relations.
    """
    def __init__(self, file, fast=True):
        self._rels = dict()
        for rel in _all_elements_of_type(file, "relation", fast):
            self._rels[rel.osm_id] = rel.members
            
    def __getitem__(self, index):
        if index in self._rels:
            return self._rels[index]
        raise KeyError()

    def __iter__(self):
        yield from self._rels.items()


class Tags():
    """Stores all the tags in a lookup optimised for finding the objects
    (nodes, ways and relations) which have a given tag.
    
    :param file: Construct from the filename or file-like object; can be
      anything which :module:`digest` can parse.
    """
    def __init__(self, file):
        self.from_nodes = _defaultdict(list)
        self.from_ways = _defaultdict(list)
        self.from_relations = _defaultdict(list)
        lookup = {"node" : self.from_nodes, "way": self.from_ways,
                  "relation": self.from_relations }
        for element in _all_elements(file):
            d = lookup[element.name]
            for key_pair in element.tags.items():
                d[key_pair].append(element.osm_id)
                
    @staticmethod
    def _by_key_pair(dictionary, key_pair):
        if key_pair in dictionary:
            return dictionary[key_pair]
        return []
                
    @staticmethod
    def _by_key(dictionary, key):
        out = []
        for key_pair in dictionary:
            if key_pair[0] == key:
                for osm_id in dictionary[key_pair]:
                    out.append( (key_pair[1], osm_id) )
        return out

    @property
    def all_node_tags(self):
        """Set of all `(key, value)` pairs of tags of nodes."""
        return set(self.from_nodes)
    
    @property
    def all_node_tag_keys(self):
        """Set of all keys which occur on tags of nodes."""
        return set(k for (k,v) in self.from_nodes)
    
    @property
    def all_way_tags(self):
        """Set of all `(key, value)` pairs of tags of ways."""
        return set(self.from_ways)
    
    @property
    def all_way_tag_keys(self):
        """Set of all keys which occur on tags of ways."""
        return set(k for (k,v) in self.from_ways)
    
    @property
    def all_relation_tags(self):
        """Set of all `(key, value)` pairs of tags of relations."""
        return set(self.from_relations)
    
    @property
    def all_relation_tag_keys(self):
        """Set of all keys which occur on tags of relations."""
        return set(k for (k,v) in self.from_relations)

    def from_key_value(self, key, value):
        """Return a list of all element which have the tag `{key: value}`.
        
        :param key: The key to search for tags with.
        :param value: The value to search for tags with.
        
        :return: A list of pairs `(typename, osm_id)` where `typename` is one
          of "node", "way" or "relation" and `osm_id` is the id of the element.
        """
        out = []
        for osm_id in self.nodes((key, value)):
            out.append(("node", osm_id))
        for osm_id in self.ways((key, value)):
            out.append(("way", osm_id))
        for osm_id in self.relations((key, value)):
            out.append(("relation", osm_id))
        return out
    
    def from_key(self, key):
        """Return a list of all element which have the tag `key`.
        
        :param key: The key to search for tags with.
        
        :return: A list of triple `(typename, value, osm_id)` where `typename`
          is one of "node", "way" or "relation", `value` is the value of the
          tag, and `osm_id` is the id of the element.
        """
        out = []
        for value, osm_id in self.nodes_from_key(key):
            out.append(("node", value, osm_id))
        for value, osm_id in self.ways_from_key(key):
            out.append(("way", value, osm_id))
        for value, osm_id in self.relations_from_key(key):
            out.append(("relation", value, osm_id))
        return out

    def nodes(self, key_pair):
        """Returns a list of all the nodes which have the tag `{key: value}`.
        
        :param key_pair: `(key, value)` of tag to search for.
        :return: list, maybe empty, of ids of nodes with this tag.
        """
        return self._by_key_pair(self.from_nodes, key_pair)

    def nodes_from_key(self, key):
        """Returns a list of all the nodes which have the tag key.
        
        :param key: The key of tags to search for.
        :return: list, maybe empty, of pairs `(value, id)` where `value` is the
          value from the tag, and `id` is osm id of the node.
        """
        return self._by_key(self.from_nodes, key)
    
    def ways(self, key_pair):
        """Returns a list of all the ways which have the tag `{key: value}`.
        
        :param key_pair: `(key, value)` of tag to search for.
        :return: list, maybe empty, of ids of ways with this tag.
        """
        return self._by_key_pair(self.from_ways, key_pair)

    def ways_from_key(self, key):
        """Returns a list of all the ways which have the tag key.
        
        :param key: The key of tags to search for.
        :return: list, maybe empty, of pairs `(value, id)` where `value` is the
          value from the tag, and `id` is osm id of the way.
        """
        return self._by_key(self.from_ways, key)

    def relations(self, key_pair):
        """Returns a list of all the relations which have the tag
        `{key: value}`.
        
        :param key_pair: `(key, value)` of tag to search for.
        :return: list, maybe empty, of ids of relations with this tag.
        """
        return self._by_key_pair(self.from_relations, key_pair)

    def relations_from_key(self, key):
        """Returns a list of all the relations which have the tag key.
        
        :param key: The key of tags to search for.
        :return: list, maybe empty, of pairs `(value, id)` where `value` is the
          value from the tag, and `id` is osm id of the relation.
        """
        return self._by_key(self.from_relations, key)


class TagsById():
    """A lookup from osm id number to tags.
    
    :param tags: An instance of :class:`Tags`.
    """
    def __init__(self, tags):
        if not isinstance(tags, Tags):
            raise ValueError("Need an instance of Tags for construction.")
        self._nodes = _defaultdict(dict)
        self._ways = _defaultdict(dict)
        self._relations = _defaultdict(dict)
        self._populate(tags.from_nodes, self._nodes)
        self._populate(tags.from_ways, self._ways)
        self._populate(tags.from_relations, self._relations)
        
    @staticmethod
    def _populate(input, output):
        for (key, value), ids in input.items():
            for osm_id in ids:
                output[osm_id][key] = value
                      
    def node(self, osm_id):
        """Return a (possibly empty) dictionary of tags for the node with
        this id.
        """
        if osm_id in self._nodes:
            return self._nodes[osm_id]
        return dict()
        
    def way(self, osm_id):
        """Return a (possibly empty) dictionary of tags for the node with
        this id.
        """
        if osm_id in self._ways:
            return self._ways[osm_id]
        return dict()

    def relation(self, osm_id):
        """Return a (possibly empty) dictionary of tags for the node with
        this id.
        """
        if osm_id in self._relations:
            return self._relations[osm_id]
        return dict()
    
        
def pythonify_and_pickle(file, out_filename):
    """Convert all the data in the XML file and save as pickled files for
    nodes, ways, relations and tags separately.
    
    :param file: Filename (the file will be opened 4 times, so passing a file
      object will not work).  Can be anything which :module:`digest` can parse.
    :param out_filename: If is `test` then writes files `test_nodes.pic.xz`
      through `test_tags.pic.xz`
     
    :return: A tuple of the 4 output filenames for nodes, ways, relations
      and tags.
    """
    obj = NodesPacked(file)
    out = [out_filename + "_nodes.pic.xz"]
    pickle(obj, out[0])
    for typpe, name in [(Ways, "ways"), (Relations, "relations"),
                        (Tags, "tags")]:
        obj = None
        obj = typpe(file)
        name = "{}_{}.pic.xz".format(out_filename, name)
        pickle(obj, name)
        out.append(name)
    return out
