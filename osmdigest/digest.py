"""
digest
~~~~~~

A reduced-complexity parser which extracts a sub-set of data from the OSM XML
file.
"""

import collections as _collections
from .utils import saxgen as _saxgen
import gzip as _gzip
import bz2 as _bz2
import lzma as _lzma
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


def _parse_file(fileobj):
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
                

def parse(file):
    """Parse the file-like object to a stream of OSM objects, as defined in
    this module.  This is a generator; failure to consume to the end can lead
    to a resource leak.  Typical usage:
        
        for obj in parse("filename.osm"):
            # Handle obj which is of type OSM, Bounds, Node, Way or
            # Relation
            pass
    
    :param file: A filename (intelligently handles ".gz", ".xz", ".bz2" file
      extensions) or a file-like object.
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
            yield from _parse_file(file)
    else:
        yield from _parse_file(file)        
