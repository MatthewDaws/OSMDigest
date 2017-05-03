"""
digest
~~~~~~

A reduced-complexity parser which extracts a sub-set of data from the OSM XML
file.

The :function:`parse` uses the element-tree iterator parsing scheme, and is
fairly performant.  For academic interest, you can use :function:`parse_sax`
which uses the :mod:`saxgen` module; this is incredibly slow.  If you really
want to use the SAX parser, then :function:`parse_callback` uses a callback
mechanism (instead of implementing as a generator) as is only a bit slower
than than :function:`parse`.
"""

import collections as _collections
from .utils import saxgen as _saxgen
import gzip as _gzip
import bz2 as _bz2
import lzma as _lzma
import xml.etree.ElementTree as _etree
import xml.sax as _sax
from .detail import Bounds, OSM

class BaseOSMElement():
    def __init__(self, attrs):
        self._osm_id = int(attrs["id"])
        self._tags = dict()
        
    @property
    def osm_id(self):
        """The OSM id."""
        return self._osm_id
        
    @property
    def tags(self):
        """A dictionary of tags."""
        return self._tags
    
    @property
    def name(self):
        """Returns "way", "node" or "relation" as appropriate."""
        return "BaseOSMElement"
        

class Node(BaseOSMElement):
    """A node, stores longitude, latitide an id, together with zero or more
    tags.
    """
    def __init__(self, attrs):
        super().__init__(attrs)
        self._latitude = float(attrs["lat"])
        self._longitude = float(attrs["lon"])
    
    @property
    def latitude(self):
        """The latitude of the point."""
        return self._latitude
    
    @property
    def longitude(self):
        """The longitude of the point."""
        return self._longitude
        
    def __repr__(self):
        return "Node({} @ [{},{}] {})".format(self.osm_id, self.latitude, self.longitude, self.tags)

    @property
    def name(self):
        return "node"


class Way(BaseOSMElement):
    """A way, an ordered list of nodes, an id, and zero or more tags."""
    def __init__(self, attrs):
        super().__init__(attrs)
        self._nodes = []

    @property
    def nodes(self):
        """An ordered list of id numbers of nodes."""
        return self._nodes
    
    def __repr__(self):
        return "Way({} ->  {} {})".format(self.osm_id, self.nodes, self.tags)
    
    @property
    def name(self):
        return "way"
    

Member = _collections.namedtuple("Member", ["type", "ref", "role"])


class Relation(BaseOSMElement):
    """A relation between other nodes or ways, together with an id, and zero or
    more tags.
    """
    def __init__(self, attrs):
        super().__init__(attrs)
        self._members = []

    @property
    def members(self):
        """A list of members."""
        return self._members

    def __repr__(self):
        return "Relation({} ->  {} {})".format(self.osm_id, self.members, self.tags)

    @property
    def name(self):
        return "relation"


class OSMDataHandler():
    """Defines the interface for a callback handler to deal with OSM data."""
    
    def start(self, osm):
        """Notify of the start of the data.
        
        :param osm: An instance of :class:`OSM` giving details of the file.
        """
        pass
    
    def end(self):
        """Called at the end of the file."""
        pass
    
    def bounds(self, bounds):
        """Notify of the bounding box of the data.
        
        :param bounds: An instance of :class:`Bounds`.
        """
        pass
    
    def node(self, node):
        """Notify of a fully-formed node.
        
        :param node: An instance of :class:`Node`.
        """
        pass
    
    def way(self, way):
        """Notify of a fully-formed way.
        
        :param way: An instance of :class:`Way`.
        """
        pass

    def relation(self, node):
        """Notify of a fully-formed relation.
        
        :param relation: An instance of :class:`Relation`.
        """
        pass
    
    
class _SAXHandler(_sax.handler.ContentHandler):
    """
    :param handler: Should follow interface of :class:`OSMDataHandler`
    """
    def __init__(self, handler):
        self.handler = handler
        self.current_object = None
    
    def endDocument(self):
        self.handler.end()
        
    def startElement(self, name, attrs):
        if name == "osm":
            self.handler.start(OSM(name, attrs))
        elif name == "bounds":
            self.handler.bounds(Bounds(name, attrs))
        elif name == "node":
            self.current_object = Node(attrs)
        elif name == "way":
            self.current_object = Way(attrs)
        elif name == "relation":
            self.current_object = Relation(attrs)
        elif name == "tag":
            self.current_object.tags[attrs["k"]] = attrs["v"]
        elif name == "nd":
            self.current_object.nodes.append(int(attrs["ref"]))
        elif name == "member":
            member = Member(type=attrs["type"],
                   ref=int(attrs["ref"]),
                   role=attrs["role"])
            self.current_object.members.append(member)
        
    def endElement(self, name):
        if name == "node":
            self.handler.node(self.current_object)
        elif name == "way":
            self.handler.way(self.current_object)
        elif name == "relation":
            self.handler.relation(self.current_object)
    

def _parse_callback(fileobj, handler):
    """Actally parse, using the callback mechanism."""
    _sax.parse(fileobj, _SAXHandler(handler))

def parse_callback(file, handler):
    """Parse the file-like object to a stream of OSM objects, as defined in
    this module.  We report objects via a callback mechanism, and use the SAX
    parser to process the XML file.
    
    :param file: A filename (intelligently handles ".gz", ".xz", ".bz2" file
      extensions) or a file-like object.
    :param handler: Should follow interface of :class:`OSMDataHandler`.
    """
    if isinstance(file, str):
        if file[-3:] == ".gz":
            file = _gzip.open(file, mode="rt", encoding="utf-8")
        elif file[-3:] == ".xz":
            file = _lzma.open(file, mode="rt", encoding="utf-8")
        elif file[-4:] == ".bz2":
            file = _bz2.open(file, mode="rt", encoding="utf-8")
        else:
            file = open(file, encoding="utf-8")
        with file:
            _parse_callback(file, handler)
    else:
        _parse_callback(file, handler)

def _parse_file(fileobj):
    """Actually do the parsing, using saxgen."""
    with _saxgen.parse(fileobj) as gen:
        current_object = None
        for xml_event in gen:
            if isinstance(xml_event, _saxgen.StartDocument):
                pass
            elif isinstance(xml_event, _saxgen.EndDocument):
                pass
            elif isinstance(xml_event, _saxgen.Characters):
                content = xml_event.content.strip()
                if len(content) > 0:
                    raise ValueError("Unexpected string data '{}'".format(content))
            elif isinstance(xml_event, _saxgen.EndElement):
                if xml_event.name in {"node", "way", "relation"}:
                    yield current_object
            elif isinstance(xml_event, _saxgen.StartElement):
                if xml_event.name == "osm":
                    yield OSM(xml_event.name, xml_event.attrs)
                elif xml_event.name == "bounds":
                    yield Bounds(xml_event.name, xml_event.attrs)
                elif xml_event.name == "node":
                    current_object = Node(xml_event.attrs)
                elif xml_event.name == "way":
                    current_object = Way(xml_event.attrs)
                elif xml_event.name == "relation":
                    current_object = Relation(xml_event.attrs)
                elif xml_event.name == "tag":
                    key = xml_event.attrs["k"]
                    value = xml_event.attrs["v"]
                    current_object.tags[key] = value
                elif xml_event.name == "nd":
                    noderef = int(xml_event.attrs["ref"])
                    current_object.nodes.append(noderef)
                elif xml_event.name == "member":
                    member = Member(type=xml_event.attrs["type"],
                           ref=int(xml_event.attrs["ref"]),
                           role=xml_event.attrs["role"])
                    current_object.members.append(member)
                else:
                    raise ValueError("Unexpected XML tag {}".format(xml_event))
            else:
                raise ValueError("Unexpected XML event {}".format(xml_event))
                
def _parse(file, parse_func):
    if isinstance(file, str):
        if file[-3:] == ".gz":
            file = _gzip.open(file, mode="rt", encoding="utf-8")
        elif file[-3:] == ".xz":
            file = _lzma.open(file, mode="rt", encoding="utf-8")
        elif file[-4:] == ".bz2":
            file = _bz2.open(file, mode="rt", encoding="utf-8")
        else:
            file = open(file, encoding="utf-8")
        with file:
            yield from parse_func(file)
    else:
        yield from parse_func(file)        

def parse_sax(file):
    """Parse the file-like object to a stream of OSM objects, as defined in
    this module.  This is a generator; failure to consume to the end can lead
    to a resource leak.  Typical usage:
        
        for obj in parse("filename.osm"):
            # Handle obj which is of type OSM, Bounds, Node, Way or
            # Relation
            pass
    
    Uses the SAX parser and the complicated thread-based model; is incredible
    slow.  See :function:`parse` for a real-world alternative.
    
    :param file: A filename (intelligently handles ".gz", ".xz", ".bz2" file
      extensions) or a file-like object.
    """
    yield from _parse(file, _parse_file)

def _add_children(parent_element, obj):
    for el in parent_element:
        if el.tag == "tag":
            obj.tags[el.attrib["k"]] = el.attrib["v"]
        elif el.tag == "nd":
            noderef = int(el.attrib["ref"])
            obj.nodes.append(noderef)
        elif el.tag == "member":
            member = Member(type=el.attrib["type"],
                   ref=int(el.attrib["ref"]),
                   role=el.attrib["role"])
            obj.members.append(member)
        else:
            raise ValueError("Unexpected XML tag for child: {}".format(parent_element))

def _parse_file_etree(file):
    generator = _etree.iterparse(file, events=["start", "end"])
    generator = iter(generator)
    # Grab the root node, so we can stop it getting over-populated
    root = next(generator)[1]
    if root.tag == "osm":
        yield OSM("osm", root.attrib)
    else:
        raise Exception("Unexpected initial tag: {}".format(root))

    for event, element in generator:
        if event == "start":
            continue
        if element.tag == "bounds":
            yield Bounds("bounds", element.attrib)
        elif element.tag == "node":
            current_object = Node(element.attrib)
            _add_children(element, current_object)
            yield current_object
        elif element.tag == "way":
            current_object = Way(element.attrib)
            _add_children(element, current_object)
            yield current_object
        elif element.tag == "relation":
            current_object = Relation(element.attrib)
            _add_children(element, current_object)
            yield current_object
        root.clear() # Stop memory buildup
        
def parse(file):
    """Parse the file-like object to a stream of OSM objects, as defined in
    this module.  Is a generator, so typical usage is:
        
        for obj in parse("filename.osm"):
            # Handle obj which is of type OSM, Bounds, Node, Way or
            # Relation
            pass
    
    :param file: A filename (intelligently handles ".gz", ".xz", ".bz2" file
      extensions) or a file-like object.
    """
    yield from _parse(file, _parse_file_etree)
