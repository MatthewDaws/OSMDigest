"""
geometry
~~~~~~~~

Use, optionally, `geopandas` and `shapely` to perform more advanced geometric
manipulatons.
"""

import sys
try:
    import geopandas as gpd
    import shapely.geometry as _geometry
    import shapely.ops as _ops
except Exception as ex:
    print("Failed to load geopandas, caused by: {}/{}".format(type(ex), ex), file=sys.stderr)
    gpd = None
    _geometry = None

from . import richobjs as _richobjs

def _tags_with_id(element):
    tags = dict(element.tags)
    tags["osm_id"] = element.osm_id
    return tags

def geojson_from_node(node):
    """Construct a simple GeoJSON object (as a python dictionary) from a
    node.
    """
    coords = [node.longitude, node.latitude]
    return {"geometry":{"type": "Point", "coordinates": coords}, "properties": _tags_with_id(node)}

def geojson_from_way(way, polygonise=False):
    """Construct a simple GeoJSON object (as a python dictionary) from a
    way.  If the `way` is an instance of :class:`RichWay` then the geometry
    is converted to a line-string.  Otherwise there is empty geometry, but an
    extra property of "nodes".

    :param way: The way to convert.
    :param polygonise: Optionally, set to True to return the geometry as a
      polygon.
    """
    json = {"geometry":{}, "properties":_tags_with_id(way)}
    try:
        coords = []
        for node in way.complete_nodes:
            coords.append([node.longitude, node.latitude])
        if polygonise:
            json["geometry"] = {"type": "Polygon", "coordinates": [coords]}
        else:
            json["geometry"] = {"type": "LineString", "coordinates": coords}
    except:
        json["properties"]["nodes"] = way.nodes
    return json

def geoseries_from_way(way):
    """Convert a :class:`RichWay` instance to a :class:`GeoSeries`.  Each way
    will be returned as a "line string" which is a zero area, not closed
    object.  Some Open Street Map ways are better represented as closed regions
    with area (a "polygon") but it is hard to tell this, automatically, from
    context, without knowing a lot about how to interpret tags.

    :param way: An instance of :class:`RichWay`.
    
    :return: An instance of :class:`GeoSeries` with the geometry and tags of
      the way.
    """
    points = [((node.longitude, node.latitude)) for node in way.complete_nodes]
    data = {"geometry": _geometry.LineString(points)}
    for key, value in way.tags.items():
        data[key] = value
    data["osm_id"] = way.osm_id
    return gpd.GeoSeries(data)

def _features_from_relation(relation):
    features = []
    features.append({"geometry":{}, "properties":_tags_with_id(relation)})
    features[0]["properties"]["members"] = relation.members
    for mem, member in zip(relation.members, relation.complete_members):
        if member.name == "node":
            json = geojson_from_node(member)
            json["properties"]["role"] = mem.role
            features.append(json)
        elif member.name == "way":
            json = geojson_from_way(member)
            json["properties"]["role"] = mem.role
            features.append(json)
        else:
            for json in _features_from_relation(member):
                json["properties"]["role"] = mem.role
                features.append(json)
    return features

def geodataframe_from_relation(relation):
    """Convert a relation into a :class:`GeoDataFrame` by (recursively)
    converting each member into a point (for a node) or a line-string (for a
    way), and collecting all tags (which may lead to many columns in the data
    frame).  The first row will be the tags of the relation itself, and
    further rows detail the members.  If a member is a relation, then that
    relation will be expanded out in the same way.
    
    :return: An instance of :class:`GeoDataFrame` with the geometry and tags
      of all members of the relation.
    """
    return gpd.GeoDataFrame.from_features(_features_from_relation(relation))

def _complete_way_to_linestring(way):
    coords = ( (node.longitude, node.latitude) for node in way.complete_nodes )
    return _geometry.LineString(coords)

def _ways_to_multipolygon(rich_relation, type):
    ways = []
    for member, full_member in zip(rich_relation.members, rich_relation.complete_members):
        if member.type == "way" and member.role == type:
            ways.append(full_member)
    if len(ways) == 0:
        return None
    out = _ops.linemerge([_complete_way_to_linestring(way) for way in ways])
    out = list(_ops.polygonize(out))
    if len(out) == 1:
        return out[0]
    return _geometry.MultiPolygon(out)

def _geo_from_relation(relation):
    outer = _ways_to_multipolygon(relation, "outer")
    if outer is None:
        return None
    inner = _ways_to_multipolygon(relation, "inner")
    if inner is not None:
        outer = outer.difference(inner)
    return outer

def geoseries_from_relation(relation):
    """Attempt to convert an instance of :class:`RichRelation` to a
    :class:`GeoSeries`, with some intelligence.  For exploring relations of
    unknown type, the :func:`geodataframe_from_relation` might be more useful.

    Currently, we ignore the "type" tag of the relation, and instead look for
    any ways with "role" of "inner" or "outer".  These are then ordered to try
    to form a Multi-Polygon, see
    http://wiki.openstreetmap.org/wiki/Relation:multipolygon
    Certain valid OSM constructs, like
    http://wiki.openstreetmap.org/wiki/Relation:multipolygon#Island_within_a_hole
    may not be supported.

    Otherwise, the conversion fails.

    :param relation: An instance of :class:`RichRelation`.
    
    :return: An instance of :class:`GeoSeries` with the geometry and tags of
      the relation.  If conversion fails, then `None`.
    """
    geo = _geo_from_relation(relation)
    if geo is None:
        return None
    data = {"geometry": geo, "osm_id": relation.osm_id}
    for key, value in relation.tags.items():
        data[key] = value
    return gpd.GeoSeries(data)

def polygonise(series):
    """A helper method.  Changes the geometry of the passed series object
    to a polygon, using `shapely`.

    :return: The (in place) altered series.
    """
    polys = list(_ops.polygonize(series["geometry"]))
    if len(polys) == 1:
        series["geometry"] = polys[0]
    elif len(polys) > 1:
        series["geometry"] = _geometry.MultiPolygon(polys)
    return series

def _line_to_geojson(line):
    return {"type":"LineString", "coordinates":list(line.coords)}

def _polygon_to_coords(poly):
    out = [list(poly.exterior.coords)]
    out.extend( list(line.coords) for x in poly.interiors )
    return out

def _polygon_to_geojson(poly):
    return {"type":"Polygon", "coordinates":_polygon_to_coords(poly)}

def _multipoly_to_geojson(mp):
    return {"type":"MultiPolygon", "coordinates":[_polygon_to_coords(p) for p in mp]}

def _point_to_geojson(p):
    return {"type":"Point", "coordinates":next(iter(p.coords))}

_shapely_converters = { "Polygon" : _polygon_to_geojson,
                        "LinearRing" : _line_to_geojson,
                        "LineString" : _line_to_geojson,
                        "MultiPolygon" : _multipoly_to_geojson,
                        "Point" : _point_to_geojson }

def shapely_to_geojson(geo):
    """Convert `shapely` geometry objects to GeoJSON.  Supported are:
    - Point
    - LineString and LinearRing (the same code)
    - Polygon
    - MultiPolygon
    """
    t = geo.geometryType()
    if t in _shapely_converters:
        return {"geometry":_shapely_converters[t](geo)}
    raise NotImplementedError("Cannot convert " + t)

def dataframe_from_elements(elements, polygonise=False):
    """For the iterable of elements, which should be :class:`Node`,
    :class:`RichWay` or :class:`RichRelation` instances, generate suitable
    geometry, and merge into a dataframe with all tags.

    For relations, the same algorithm as :func:`geoseries_from_relation`
    is applied.

    This method is typically a lot quicker than constructing GeoSeries
    and merging.

    :param elements: An iterable.
    :param polygonise: If True, convert applicable geometry to polygons.

    :return: A :class:`GeoDataFrame` instance.
    """
    features = []
    for el in elements:
        if el.name == "node":
            features.append(geojson_from_node(el))
        elif el.name == "way":
            features.append(geojson_from_way(el, polygonise))
        elif el.name == "relation":
            geo = _geo_from_relation(el)
            feature = shapely_to_geojson(geo)
            feature["properties"] = _tags_with_id(el)
            features.append(feature)
        else:
            raise NotImplementedError()
    return gpd.GeoDataFrame.from_features(features)