"""
*********
Shapefile
*********

Generates a networkx.DiGraph from point and line shapefiles.

"The Esri Shapefile or simply a shapefile is a popular geospatial vector
data format for geographic information systems software. It is developed
and regulated by Esri as a (mostly) open specification for data
interoperability among Esri and other software products."
See https://en.wikipedia.org/wiki/Shapefile for additional information.
"""
import networkx as nx
import os


__all__ = ['read_shp', 'write_shp']


def read_shp(path, unique_attribute, simplify=True, geom_attrs=True, strict=True):
    """Generates a networkx.DiGraph from shapefiles. Point geometries are
    translated into nodes, lines into edges. Coordinate tuples are used as
    keys. Attributes are preserved, line geometries are simplified into start
    and end coordinates. Accepts a single shapefile or directory of many
    shapefiles.

    "The Esri Shapefile or simply a shapefile is a popular geospatial vector
    data format for geographic information systems software [1]_."

    Parameters
    ----------
    path : file or string
       File, directory, or filename to read.

    unique_attribute: string
        Attribute in shapefile which allows to distinguish parallel edges

    simplify:  bool
        If True, simplify line geometries to start and end coordinates.
        If False, and line feature geometry has multiple segments, the
        non-geometric attributes for that feature will be repeated for each
        edge comprising that feature.

    geom_attrs: bool
        If True, include the Wkb, Wkt and Json geometry attributes with
        each edge.

        NOTE:  if these attributes are available, write_shp will use them
        to write the geometry.  If nodes store the underlying coordinates for
        the edge geometry as well (as they do when they are read via
        this method) and they change, your geomety will be out of sync.

    strict: bool
        If True, raise NetworkXError when feature geometry is missing or
        GeometryType is not supported.
        If False, silently ignore missing or unsupported geometry in features.

    Returns
    -------
    G : NetworkX graph

    Raises
    ------
    ImportError
       If ogr module is not available.

    RuntimeError
       If file cannot be open or read.

    NetworkXError
       If strict=True and feature is missing geometry or GeometryType is
       not supported.

    Examples
    --------
    >>> G = nx.read_shp('test.shp', 'Name') # doctest: +SKIP

    References
    ----------
    .. [1] https://en.wikipedia.org/wiki/Shapefile
    """
    try:
        from osgeo import ogr
    except ImportError:
        raise ImportError("read_shp requires OGR: http://www.gdal.org/")

    if not isinstance(path, str):
        return

    net = nx.MultiGraph()
    shp = ogr.Open(path)
    if shp is not None:
        layer = shp.GetLayer()
        spatial_ref = str(layer.GetSpatialRef())
    else:
        spatial_ref = None
    net.graph['crs'] = spatial_ref
    if shp is None:
        raise RuntimeError("Unable to open {}".format(path))
    for field_name in shp:
        fields = [x.GetName() for x in field_name.schema]
        for feature in field_name:
            geometry = feature.geometry()
            if geometry is None:
                if strict:
                    raise nx.NetworkXError("Bad data: feature missing geometry")
                else:
                    continue
            field_data = [feature.GetField(feature.GetFieldIndex(x)) for x in fields]
            attributes = dict(zip(fields, field_data))
            attributes["ShpName"] = field_name.GetName()
            # Note:  Using layer level geometry type
            if geometry.GetGeometryType() == ogr.wkbPoint:
                net.add_node((geometry.GetPoint_2D(0)), **attributes)
            elif geometry.GetGeometryType() in (ogr.wkbLineString,
                                         ogr.wkbMultiLineString):
                for edge in edges_from_line(geometry, attributes, simplify,
                                            geom_attrs):
                    e1, e2, attr = edge
                    net.add_edge(e1, e2, attr[unique_attribute])
                    net[e1][e2][attr[unique_attribute]].update(attr)
            else:
                if strict:
                    raise nx.NetworkXError("GeometryType {} not supported".
                                           format(geometry.GetGeometryType()))
    return net


def edges_from_line(geom, attrs, simplify=True, geom_attrs=True):
    """
    Generate edges for each line in geom
    Written as a helper for read_shp

    Parameters
    ----------

    geom:  ogr line geometry
        To be converted into an edge or edges

    attrs:  dict
        Attributes to be associated with all geoms

    simplify:  bool
        If True, simplify the line as in read_shp

    geom_attrs:  bool
        If True, add geom attributes to edge as in read_shp


    Returns
    -------
     edges:  generator of edges
        each edge is a tuple of form
        (node1_coord, node2_coord, attribute_dict)
        suitable for expanding into a networkx Graph add_edge call
    """
    try:
        from osgeo import ogr
    except ImportError:
        raise ImportError("edges_from_line requires OGR: http://www.gdal.org/")

    if geom.GetGeometryType() == ogr.wkbLineString:
        if simplify:
            edge_attrs = attrs.copy()
            last = geom.GetPointCount() - 1
            if geom_attrs:
                edge_attrs["Wkb"] = geom.ExportToWkb()
                edge_attrs["Wkt"] = geom.ExportToWkt()
                edge_attrs["Json"] = geom.ExportToJson()
            yield (geom.GetPoint_2D(0), geom.GetPoint_2D(last), edge_attrs)
        else:
            for i in range(0, geom.GetPointCount() - 1):
                pt1 = geom.GetPoint_2D(i)
                pt2 = geom.GetPoint_2D(i + 1)
                edge_attrs = attrs.copy()
                if geom_attrs:
                    segment = ogr.Geometry(ogr.wkbLineString)
                    segment.AddPoint_2D(pt1[0], pt1[1])
                    segment.AddPoint_2D(pt2[0], pt2[1])
                    edge_attrs["Wkb"] = segment.ExportToWkb()
                    edge_attrs["Wkt"] = segment.ExportToWkt()
                    edge_attrs["Json"] = segment.ExportToJson()
                    del segment
                yield (pt1, pt2, edge_attrs)

    elif geom.GetGeometryType() == ogr.wkbMultiLineString:
        for i in range(geom.GetGeometryCount()):
            geom_i = geom.GetGeometryRef(i)
            for edge in edges_from_line(geom_i, attrs, simplify, geom_attrs):
                yield edge


def write_shp(G, unique_attribute, outdir):
    """Writes a networkx.DiGraph to two shapefiles, edges and nodes.
    Nodes and edges are expected to have a Well Known Binary (Wkb) or
    Well Known Text (Wkt) key in order to generate geometries. Also
    acceptable are nodes with a numeric tuple key (x,y).

    "The Esri Shapefile or simply a shapefile is a popular geospatial vector
    data format for geographic information systems software [1]_."

    Parameters
    ----------
    unique_attribute: string
        Attribute in shapefile which allows to distinguish parallel edges

    outdir : directory path
       Output directory for the two shapefiles.

    Returns
    -------
    None

    Examples
    --------
    nx.write_shp(digraph, 'Name', '/shapefiles') # doctest +SKIP

    References
    ----------
    .. [1] https://en.wikipedia.org/wiki/Shapefile
    """
    os.environ['SHAPE_ENCODING'] = "cp1251"
    try:
        from osgeo import ogr, osr
    except ImportError:
        raise ImportError("write_shp requires OGR: http://www.gdal.org/")
    # easier to debug in python if ogr throws exceptions
    ogr.UseExceptions()
    try:
        srs = osr.SpatialReference(G.graph['crs'])
    except AttributeError:
        srs = None
    def netgeometry(key, data):
        if 'Wkb' in data:
            geom = ogr.CreateGeometryFromWkb(data['Wkb'])
        elif 'Wkt' in data:
            geom = ogr.CreateGeometryFromWkt(data['Wkt'])
        elif type(key[0]).__name__ == 'tuple':  # edge keys are packed tuples
            geom = ogr.Geometry(ogr.wkbLineString)
            _from, _to = key[0], key[1]
            try:
                geom.SetPoint(0, *_from)
                geom.SetPoint(1, *_to)
            except TypeError:
                # assume user used tuple of int and choked ogr
                _ffrom = [float(x) for x in _from]
                _fto = [float(x) for x in _to]
                geom.SetPoint(0, *_ffrom)
                geom.SetPoint(1, *_fto)
        else:
            geom = ogr.Geometry(ogr.wkbPoint)
            try:
                geom.SetPoint(0, *key)
            except TypeError:
                # assume user used tuple of int and choked ogr
                fkey = [float(x) for x in key]
                geom.SetPoint(0, *fkey)

        return geom

    # Create_feature with new optional attributes arg (should be dict type)
    def create_feature(geometry, lyr, attributes):
        feature = ogr.Feature(lyr.GetLayerDefn())
        feature.SetGeometry(g)
        if attributes is not None:
            # Loop through attributes, assigning data to each field
            for field, data in attributes.items():
                feature.SetField(field, data)
        lyr.CreateFeature(feature)
        feature.Destroy()

    # Conversion dict between python and ogr types #encode('cp1251')
    OGRTypes = {int: ogr.OFTInteger, str: ogr.OFTString, float: ogr.OFTReal}

    # Check/add fields from attribute data to Shapefile layers
    def add_fields_to_layer(key, value, fields, layer):
        # Field not in previous edges so add to dict
        if type(value) in OGRTypes:
            fields[key] = OGRTypes[type(value)]
        else:
            # Data type not supported, default to string (char 80)
            fields[key] = ogr.OFTString
        # Create the new field
        newfield = ogr.FieldDefn(key, fields[key])
        layer.CreateField(newfield)

    drv = ogr.GetDriverByName("ESRI Shapefile")
    shpdir = drv.CreateDataSource(outdir)
    # delete pre-existing output first otherwise ogr chokes
    try:
        shpdir.DeleteLayer("nodes")
    except:
        pass
    nodes = shpdir.CreateLayer("nodes", srs, ogr.wkbPoint)

    # Storage for node field names and their data types
    node_fields = {}

    def create_attributes(data, fields, layer):
        attributes = {}  # storage for attribute data (indexed by field names)
        for key, value in data.items():
            # Reject spatial data not required for attribute table
            if (key != 'Json' and key != 'Wkt' and key != 'Wkb'
                    and key != 'ShpName'):
                # Check/add field and data type to fields dict
                if key not in fields:
                    add_fields_to_layer(key, value, fields, layer)
                # Store the data from new field to dict for CreateLayer()
                try:
                    attributes[key] = value.decoding('cp1251')
                except:
                    attributes[key] = value
        return attributes, layer

    for n in G:
        data = G.nodes[n]
        g = netgeometry(n, data)
        attributes, nodes = create_attributes(data, node_fields, nodes)
        create_feature(g, nodes, attributes)

    try:
        shpdir.DeleteLayer("edges")
    except:
        pass
    edges = shpdir.CreateLayer("edges", srs, ogr.wkbLineString)

    # New edge attribute write support merged into edge loop
    edge_fields = {}      # storage for field names and their data types

    for edge in G.edges(data=True):
        key = edge[2][unique_attribute]
        data = G.get_edge_data(edge[0], edge[1], key)
        g = netgeometry(edge, data)
        attributes, edges = create_attributes(edge[2], edge_fields, edges)
        create_feature(g, edges, attributes)

    nodes, edges, attributes = None, None, None
