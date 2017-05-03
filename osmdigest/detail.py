"""
detail
~~~~~~

Parse an OSM XML file, validating the data, and producing a stream of rich
data objects.  Designed for debugging and understanding the data.  Practical
applications should use one of the faster, more streamlined processing modules.
"""

from .utils import saxgen as _saxgen
import datetime as _datetime
import gzip as _gzip
import bz2 as _bz2
import lzma as _lzma

_DT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

class OSMElement():
    """Base class for standard top-level OSM elements.  Expects the attributes
    "id", "version", "changeset" and "timestamp".  Optional attributes "user"
    and "uid".  If the attribute "visible" is present, is should have value
    "true".
    """
    def __init__(self, name, attrs):
        try:
            self._name = name
            self.keys = set(attrs.keys())
            self._osm_id = int(attrs["id"])
            self._metadata = {"user" : self._opt_element(attrs, "user"),
                            "uid" : int(self._opt_element(attrs, "uid", 0)),
                            "version" : int(attrs["version"]),
                            "changeset" : int(attrs["changeset"]),
                            "timestamp" : _datetime.datetime.strptime(attrs["timestamp"], _DT_FORMAT) }
            if "visible" in self.keys:
                if not attrs["visible"] == "true":
                    raise Exception("Element not visible!")
                self.keys.remove("visible")

            self.keys.difference_update(["id", "user", "uid", "version", "changeset", "timestamp"])
        except Exception as e:
            raise ValueError("Failed to parse {}/{}, cause: {}/{}".format(name,
                {k:attrs[k] for k in attrs.keys()}, type(e), e))
    
    @property
    def keys(self):
        """The currently unprocesses extra attributes."""
        return self._keys

    @keys.setter
    def keys(self, value):
        self._keys = set(value)
    
    @property
    def osm_id(self):
        """The OpenStreetMap id code"""
        return self._osm_id
    
    @property
    def name(self):
        """The tag name"""
        return self._name

    @property
    def subobjs(self):
        """A list of sub-objects"""
        if not hasattr(self, "_subobjs"):
            self._subobjs = []
        return self._subobjs

    @property
    def metadata(self):
        """A dictionary of extra data."""
        return self._metadata
        
    @staticmethod
    def _opt_element(mapping, key, default=""):
        if key in mapping:
            return mapping[key]
        return default


class Node(OSMElement):
    """Represents an OSM "node" which is a point on the planet surface with
    possible extra data.  See http://wiki.openstreetmap.org/wiki/Node
    """
    def __init__(self, name, attrs):
        super().__init__(name, attrs)
        if self.name != "node":
            raise ValueError("Should be of type 'node'")
        self._latitude = float(attrs["lat"])
        self._longitude = float(attrs["lon"])
        extra_keys = self.keys.difference(["lat", "lon"])
        if extra_keys:
            raise ValueError("Unexpected keys for node element: {}".format(extra_keys))
        
    @property
    def latitude(self):
        """The latitude of the point."""
        return self._latitude
    
    @property
    def longitude(self):
        """The longitude of the point."""
        return self._longitude
        
    def __repr__(self):
        return "Node({} @ [{},{}])".format(self.osm_id, self.latitude, self.longitude)

        
class Way(OSMElement):
    """Represents an ordered list of nodes, with possible extra data.
    See http://wiki.openstreetmap.org/wiki/Way
    """
    def __init__(self, name, attrs):
        super().__init__(name, attrs)
        if self.name != "way":
            raise ValueError("Should be of type 'way'")
        if self.keys:
            raise ValueError("Unexpected keys for way element: {}".format(self.keys))
        
    def __repr__(self):
        return "Way({},{})".format(self.osm_id, self.subobjs)


class Relation(OSMElement):
    """Represents a logical relationship between other elements.
    See http://wiki.openstreetmap.org/wiki/Relation
    """
    def __init__(self, name, attrs):
        super().__init__(name, attrs)
        if self.name != "relation":
            raise ValueError("Should be of type 'relation'")
        if self.keys:
            raise ValueError("Unexpected keys for relation element: {}".format(self.keys))
            
    def __repr__(self):
        return "Relation({},{})".format(self.osm_id, self.subobjs)
    

class OSMSingleElement():
    """Base class for OSM XML elements which do not contain sub-elements."""
    _extra_keys_msg = "Unexpected extra attributes for '{}' element: {}"

    def __init__(self, name, attrs, expected_name, expected_keys):
        if name != expected_name:
            raise ValueError("Should be of type '{}'".format(expected_name))
        extra_keys = set(attrs.keys()).difference(expected_keys)
        if extra_keys:
            raise ValueError(self._extra_keys_msg.format(expected_name, extra_keys))
        

class Bounds(OSMSingleElement):
    """Stores the bounding box for the data the XML file contains."""
    def __init__(self, name, attrs):
        super().__init__(name, attrs, "bounds", ["minlat", "minlon", "maxlat", "maxlon"])
        self._min_latitude = float(attrs["minlat"])
        self._min_longitude = float(attrs["minlon"])
        self._max_latitude = float(attrs["maxlat"])
        self._max_longitude = float(attrs["maxlon"])
        
    @property
    def min_latitude(self):
        """The minimimum value of latitude in the data."""
        return self._min_latitude

    @property
    def max_latitude(self):
        """The maximum value of latitude in the data."""
        return self._max_latitude

    @property
    def min_longitude(self):
        """The minimimum value of longitude in the data."""
        return self._min_longitude

    @property
    def max_longitude(self):
        """The maximum value of longitude in the data."""
        return self._max_longitude

    @property
    def name(self):
        return "bounds"
        
    def __repr__(self):
        return "Bounds(latitude:[{},{}], longitude:[{},{}]".format(self.min_latitude,
            self.max_latitude, self.min_longitude, self.max_longitude)


class Tag(OSMSingleElement):
    """Stores a key/value pair to add data to another element.
    See http://wiki.openstreetmap.org/wiki/Tags
    """
    def __init__(self, name, attrs):
        super().__init__(name, attrs, "tag", ["k", "v"])
        self._k = attrs["k"]
        self._v = attrs["v"]
    
    @property
    def key(self):
        return self._k
    
    @property
    def value(self):
        return self._v
    
    def __repr__(self):
        return "Tag({}->{})".format(self.key, self.value)

    
class NodeRef(OSMSingleElement):
    """A reference to a node."""
    def __init__(self, name, attrs):
        super().__init__(name, attrs, "nd", ["ref"])
        self._ref = int(attrs["ref"])

    @property
    def ref(self):
        """The integer value of the id of the node."""
        return self._ref
    
    def __repr__(self):
        return "NodeRef({})".format(self.ref)
    

class Member(OSMSingleElement):
    """Specifies a reference to a node or way in a relation, with an optional
    "role".
    """
    def __init__(self, name, attrs):
        super().__init__(name, attrs, "member", ["ref", "type", "role"])
        self._ref = int(attrs["ref"])
        self._type = attrs["type"]
        self._role = attrs["role"]

    @property
    def ref(self):
        """An int giving the osm id of the way or node this is a reference to."""
        return self._ref

    @property
    def type(self):
        """Should be 'way', 'node' or 'relation'."""
        return self._type
    
    @property
    def role(self):
        """The, possibly empty, string specifying the "role" the member has."""
        return self._role
    
    def __repr__(self):
        return "Member(ref={}, type={}, role={})".format(self.ref, self.type, self.role)
    

class OSM(OSMSingleElement):
    """Represents top-level data about the XML file."""
    def __init__(self, name, attrs):
        super().__init__(name, attrs, "osm", ["version", "generator", "timestamp"])
        self._version = attrs["version"]
        self._generator = attrs["generator"]
        if "timestamp" in attrs.keys():
            self._timestamp = _datetime.datetime.strptime(attrs["timestamp"], _DT_FORMAT)
        else:
            self._timestamp = None
    
    @property
    def version(self):
        """String representing the format version."""
        return self._version
    
    @property
    def generator(self):
        """String giving the way the file was generated; typically the name of
        the generating software package.
        """
        return self._generator
    
    @property
    def timestamp(self):
        """The timestamp of the file, or `None`"""
        return self._timestamp
    
    @property
    def name(self):
        return "osm"

    def __repr__(self):
        return "OSM(version={}, generator={}, timestamp={})".format(self.version,
            self.generator, self.timestamp)
        

class BaseParser():
    """A validating parser of OSM XML data."""
    _relations = {"osm" : {"bounds", "node", "way", "relation"},
                  "node" : {"tag"},
                  "way" : {"tag", "nd"},
                  "relation" : {"tag", "member"}}
    
    def __init__(self):
        super().__init__()
        self.currently_open_tags = []
        self.current_object = None
        
    def _processNewElement(self, name, attrs):
        if len(self.currently_open_tags) == 0:
            if name == "osm":
                return OSM(name, attrs)
            else:
                raise Exception("Expect all data to be inside 'osm' tag.")
            return
        
        allowed = self._relations[self.currently_open_tags[-1]]
        if name not in allowed:
            raise Exception("Inside tag '{}' so expected '{}' but got '{}'".format(
                self.currently_open_tags[-1], allowed, name))
        
        if name == "bounds":
            self.current_object = Bounds(name, attrs)
        elif name == "node":
            self.current_object = Node(name, attrs)
        elif name == "way":
            self.current_object = Way(name, attrs)
        elif name == "relation":
            self.current_object = Relation(name, attrs)
        elif name == "tag":
            self.current_object.subobjs.append(Tag(name, attrs))
        elif name == "nd":
            self.current_object.subobjs.append(NodeRef(name, attrs))
        elif name == "member":
            self.current_object.subobjs.append(Member(name, attrs))
        else:
            raise ValueError("Unexpected tag: '{}'".format(name))
        
    def receive(self, element):
        el = None
        if isinstance(element, _saxgen.StartElement):
            el = self.startElement(element.name, element.attrs)
        elif isinstance(element, _saxgen.EndElement):
            el = self.endElement(element.name)
        elif isinstance(element, _saxgen.Characters):
            el = self.characters(element.content)
        elif isinstance(element, _saxgen.StartDocument):
            pass
        elif isinstance(element, _saxgen.EndDocument):
            pass
        else:
            raise ValueError("Unexpected XML entity: {}".format(element))
        return el
            
    def startElement(self, name, attrs):
        el = self._processNewElement(name, attrs)
        self.currently_open_tags.append(name)
        return el
    
    def endElement(self, name):
        if name == self.currently_open_tags[-1]:
            self.currently_open_tags.pop()
        else:
            raise ValueError("Expected next close tag to be '{}' but got '{}'".format(
                self.currently_open_tags[-1], name))
        if name in {"bounds", "node", "way", "relation"}:
            return self.current_object
    
    def characters(self, content):
        content = content.strip()
        if len(content) > 0:
            raise ValueError("Unexpected characters: '{}'".format(content))
            

class Parser():
    """Implements the context manager protocol, so should be used with the
    "with" statement.  Gives a generator of OSMSingleElement objects
    describing top-level data, or OSMElement objects describing nodes, ways
    and relationships.
    
    :param file: A file-like object, or a filename.  Intelligently handles
    ".gz", ".xz" and ".bz2" file types.
    """
    def __init__(self, file):
        self._file = file
        self._our_file = None

    def __enter__(self):
        if isinstance(self._file, str):
            if self._file[-3:] == ".gz":
                self._our_file = _gzip.open(self._file, mode="rt", encoding="utf-8")
            elif self._file[-3:] == ".xz":
                self._our_file = _lzma.open(self._file, mode="rt", encoding="utf-8")
            elif self._file[-4:] == ".bz2":
                self._our_file = _bz2.open(self._file, mode="rt", encoding="utf-8")
            else:
                self._our_file = open(self._file, encoding="utf-8")
            self._file = self._our_file                
        self.xml_generator = _saxgen.parse(self._file)
        self.xml_generator.__enter__()
        return self
    
    def __exit__(self, type, value, traceback):
        self.xml_generator.__exit__(type, value, traceback)
        if self._our_file is not None:
            self._our_file.close()
            
    def __iter__(self):
        parser = BaseParser()
        for xml_element in self.xml_generator:
            out = parser.receive(xml_element)
            if out is not None:
                yield out