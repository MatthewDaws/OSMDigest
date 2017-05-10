"""
richobjs
~~~~~~~~

Provides data containers which offer richer structures than a direct
translation of the XML structure.  For example, a representation of a "way"
which contains all the coordinates of the nodes, instead of just references.
"""

from . import digest as _digest

def _centroid(gen):
    """Find the centroid of the coordinates given by the generator.  The
    generator should yield pairs (longitude, latitude).

    :return: Pair (longitude, latitude) of the centroid.
    """
    n, lon, lat = 0, 0, 0
    for pair in gen:
        lon += pair[0]
        lat += pair[1]
        n += 1
    return lon / n, lat / n

class RichWay(_digest.Way):
    """Subclass of :class:`Way` which stores complete node information.
    
    :param way: The :class:`Way` object to add details to.
    :param provide_full_nodes: A generator which will yield a list of
      :class:`Node` objects.
    """
    def __init__(self, way, provide_full_nodes):
        super().__init__({"id":way.osm_id})
        self._nodes = way._nodes
        self._tags = way._tags
        self._full_nodes = list(provide_full_nodes)
        self._validate_ids()

    def _validate_ids(self):
        if len(self.nodes) != len(self.complete_nodes):
            raise ValueError("Length of node references and complete nodes disagree")
        for i, (node, full_node) in enumerate(zip(self.nodes, self.complete_nodes)):
            if node != full_node.osm_id:
                raise ValueError("Nodes at index {} disagree on ids, {} vs {}".format(i, node, full_node.osm_id))

    @property
    def complete_nodes(self):
        """Returns an ordered list of :class:`Node` instances which form the
        way.
        """
        return self._full_nodes
    
    def __len__(self):
        return len(self._full_nodes)

    def centroid(self):
        """Compute the centroid of this way.
        
        :return: Pair (longitude, latitude) of the centroid.
        """
        return _centroid( ((node.longitude, node.latitude) for node in self.complete_nodes) )

    def __repr__(self):
        return "RichWay({} ->  {} {})".format(self.osm_id, self.complete_nodes, self.tags)


class RichRelation(_digest.Relation):
    """Subclass of :class:`Relation` which stores full details of any node,
    way or relation which forms a member.

    :param relation: An instance of :class:`Relation` to add details to.
    :param provide_full_members: A generator of :class:`Node`, :class:`Way` and
      :class:`Relation` objects which form the members of this relation.
    """
    def __init__(self, relation, provide_full_members):
        super().__init__({"id":relation.osm_id})
        self._tags = relation._tags
        self._members = relation._members
        self._full_members = list(provide_full_members)
        self._validate_ids()

    def _validate_ids(self):
        if len(self.members) != len(self.complete_members):
            raise ValueError("Length of member references and complete members disagree")
        for i, (member, full_member) in enumerate(zip(self.members, self.complete_members)):
            if member.ref != full_member.osm_id:
                raise ValueError("Index {} has a mismatch in id: {} vs {}".format(i, member.ref, full_member.osm_id))
            if member.type != full_member.name:
                raise ValueError("Index {} has a mismatch in type: {} vs {}".format(i, member.type, full_member.name))
    
    @property
    def complete_members(self):
        """Returns a list of members, each entry of which is a fully populated
        node, way or relation object.
        """
        return self._full_members
    
    def centroid(self):
        """Compute the centroid of this relation.  We recursively find the
        centroid of each member, and then find the centroid of these centroids.
        
        :return: Pair (longitude, latitude) of the centroid.
        """
        def gen():
            for member in self.complete_members:
                if member.name == "node":
                    yield (member.longitude, member.latitude)
                else:
                    yield member.centroid()
        return _centroid(gen())

    def __repr__(self):
        # Deliberately aneamic so as to not spam...
        return "RichRelation({} ->  {} {})".format(self.osm_id, self.members, self.tags)
