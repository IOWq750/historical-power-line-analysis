# -*- coding: utf-8 -*-
import os
import networkx as nx
from osgeo import ogr, osr
import import_export_shp as aux_ie


def el_centrality(power_lines, power_points, name, weight, voltage, output_workspace):
    """ Calculation of electrical network centrality as a number of shortest paths between each substation and
    topologically closest generation points.

            Parameters
            ----------
            power_lines: str
                 path to the polyline shapefile with all power lines

            power_points: str
                path to the point shapefile with all power points (substations, generation) with attribute 'Point_Type',
                all generation points have value 'ЭС', all substations have values 'ПС'

            name: str
                name field for power lines as a third key for multigraph

            weight: str
                weight field name for power lines (inverted capacity)

            voltage: str
                voltage field name for power lines

            output_workspace: str
                path to the output directory

            Returns
            -------
            number of nodes (original power points without orphan links), number of generation points,
            number of substation points"""

    G_network = aux_ie.convert_shp_to_graph(power_lines, "false", "true", name)
    G_points = nx.read_shp(power_points)
    number_nodes = int(G_points.number_of_nodes())
    dict_point_type = {}
    t1 = nx.get_node_attributes(G_points, 'Type')
    nodes_from_points = G_points.nodes
    for node_p in nodes_from_points:
        try:
            dict_point_type[node_p] = t1[node_p]
        except:
            print('No such a node with ccordinates {}'.format(node_p))
    nx.set_node_attributes(G_network, dict_point_type, 'Type')
    nodes_from_network = G_network.nodes
    generation = set()
    node_dict = nx.get_node_attributes(G_network, 'Type')
    for node in nodes_from_network:
        if node in node_dict:
            if node_dict[node] in ['Р­РЎ', 'РџРЎ', 'ЭС', 'РУ']:
                generation.add(node)
    generation_count = len(generation)
    substation_count = number_nodes - generation_count
    G_network, trace_dict = trace_lines(G_network, voltage)
    shortest_path = nx.multi_source_dijkstra_path(G_network, generation, weight=weight)
    aux_ie.export_path_to_shp(G_network, "true", output_workspace, trace_dict + [shortest_path])
    return number_nodes, generation_count, substation_count


def trace_lines(G_network, voltage):
    """Tracing all existing lines in graph and appending them to the dictionary, calculation of the number of
    parallel edges with the same voltage class, appending this data as attribute of edge

            Parameters
            ----------
            G_network : networkx graph
               name of graph, voltage of the line should be in appropriate attribute field

            voltage: str
                voltage field name for power lines

            Returns
            -------
            networkx graph and list of tracing dictionaries kind of {start: (start, end)}"""
    line_dict = {}
    trace_dict_list = [{}]
    for line in G_network.edges(data=True):
        checked_lines = []
        start_end = line[:2]
        item = (start_end, line[2][voltage])
        item_inverted = (start_end[1], start_end[0], line[2][voltage])
        if item not in line_dict and item_inverted not in line_dict:
            line_dict[item] = 1
        else:
            line_dict[item] += 1
        for i in range(len(trace_dict_list)):
            if line not in checked_lines:
                if start_end[0] not in trace_dict_list[i]:
                    trace_dict_list[i][start_end[0]] = [start_end[0], start_end[1]]
                    checked_lines.append(line)
                elif i + 1 == len(trace_dict_list):
                    trace_dict_list.append({})
                    trace_dict_list[i + 1][start_end[0]] = [start_end[0], start_end[1]]
                    checked_lines.append(line)
    circuit_dict = {}
    for line in G_network.edges(keys=True, data=True):
        try:
            circuit_dict[line[:3]] = line_dict[(line[:2], line[3][voltage])]
        except:
            circuit_dict[line[:3]] = line_dict[line[1], line[0], line[3][voltage]]
    nx.set_edge_attributes(G_network, circuit_dict, 'Circ_Count')
    return G_network, trace_dict_list


def create_cpg(shapefile):
    """Encoding description file creation"""
    with open('{}.cpg'.format(shapefile), 'w') as cpg:
        cpg.write('cp1251')


def geometry_extraction(layer):
    centroid = ogr.FieldDefn('centroid', ogr.OFTString)
    layer.CreateField(centroid)
    for feature in layer:
        geom = feature.GetGeometryRef()
        centroid = geom.Centroid().ExportToWkt()
        feature.SetField('centroid', centroid)
        layer.SetFeature(feature)
    layer.ResetReading()


def dissolve_layer(layer, output_shp, input_fields=None, delete_fields=None, add_fields=None, stats_dict=None):
    """Grouping features by attribute values in input fields and optionally calculation of statistics. If input fields
    set as None, all existing fields will be accounted in dissolving except the list of delete fields

        Parameters
        ----------
        layer: ogr layer object
           name of layer to read.

        output_shp: str
            Output shapefile path with dissolved features

        input_fields: list
            Attributes in shapefile for dissolving by their unique values

        delete_fields: list
            Attributes in shapefile which should be deleted in output shapefile

        add_fields: dict
            dictionary kind of {fieldname: fieldtype} to add in output shapefile

        stats_dict: dict
            keys – name of attribute fields for statistics calculation, values – type of statistics
            valid types of statistics:
            COUNT – number of dissolved features
            SUM – sum of dissolved features values
            MIN – min of dissolved features values
            MAX – max of dissolved features values
            AVE – average of dissolved features values

        Returns
        -------
        None"""

    for stats in stats_dict:
        add_fields[(stats + stats_dict[stats])[:10]] = ogr.OFTInteger
    field_list = import_field_schema(layer, output_shp, input_fields, delete_fields, add_fields)
    grouped_features = {}
    for feature in layer:
        groupby = []
        for field in field_list:
            group_field = feature.GetField(field)
            groupby.append(group_field)
        groupby = tuple(groupby)
        if groupby not in grouped_features:
            grouped_features[groupby] = [feature]
        else:
            grouped_features[groupby] += [feature]
    layer.ResetReading()
    dissolved_features = []
    for groupby in grouped_features:
        dissolved_feature = {}
        for i in range(len(field_list)):
            dissolved_feature[field_list[i]] = groupby[i]
        merged_line = ogr.Geometry(ogr.wkbMultiLineString)
        for feature in grouped_features[groupby]:
            merged_line.AddGeometry(feature.GetGeometryRef())
        dissolved_feature['group'] = merged_line
        if stats_dict is not None:
            for stats in stats_dict:
                if stats == 'COUNT':
                    dissolved_feature[(stats + stats_dict[stats])[:10]] = len(grouped_features[groupby])
                if stats == 'SUM':
                    dissolved_feature[(stats + stats_dict[stats])[:10]] = sum([feature.GetField(stats_dict[stats]) for
                                                                               feature in grouped_features[groupby]])
                if stats == 'MIN':
                    dissolved_feature[(stats + stats_dict[stats])[:10]] = min([feature.GetField(stats_dict[stats]) for
                                                                               feature in grouped_features[groupby]])
                if stats == 'MAX':
                    dissolved_feature[(stats + stats_dict[stats])[:10]] = max([feature.GetField(stats_dict[stats]) for
                                                                               feature in grouped_features[groupby]])
                if stats == 'AVE':
                    dissolved_feature[(stats + stats_dict[stats])[:10]] = sum([feature.GetField(stats_dict[stats]) for
                                            feature in grouped_features[groupby]])/float(len(grouped_features[groupby]))
        dissolved_features.append(dissolved_feature)
    out_ds = ogr.GetDriverByName('ESRI Shapefile').Open(output_shp, 1)
    out_layer = out_ds.GetLayer()
    for item in dissolved_features:
        feature = ogr.Feature(out_layer.GetLayerDefn())
        for key in item.keys():
            if key == 'group':
                feature.SetGeometry(item[key])
            else:
                feature.SetField(key, item[key])
        out_layer.CreateFeature(feature)


def import_field_schema(layer, output_shp, input_fields=None, delete_fields=None, add_field=None):
    """Import field list from input layer to the shapefile in path_output directory excluding the list of delete_fields

        Parameters
        ----------
        layer: datasource.GetLayer() object

        output_shp: string
        directory of output shapefile

        delete_fields: list (optional)
        list of fields that should be excluded from final shp

        add_field: dictionary
        dictionary kind of {fieldname: fieldtype} to add in output datasource

        Returns
        -------
        datasource.GetLayer() object of final shapefile, dictionary of field schema {fieldName: fieldType}
    """

    out_ds = ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(output_shp)
    dst_layer = out_ds.CreateLayer(os.path.basename(output_shp), osr.SpatialReference(str(layer.GetSpatialRef())),
                                   ogr.wkbMultiLineString, options=["ENCODING=CP1251"])
    dst_layer.CreateFields(layer.schema)
    layer_definition_in = layer.GetLayerDefn()
    layer_definition_out = dst_layer.GetLayerDefn()
    if input_fields is None:
        in_fields = []
    for i in range(layer_definition_in.GetFieldCount()):
        field_name = layer_definition_in.GetFieldDefn(i).GetName()
        if input_fields is None:
            in_fields.append(field_name)
        elif field_name in input_fields:
            in_fields.append(field_name)
        else:
            delete_fields.append(field_name)
    for field_name in in_fields:
        if field_name in delete_fields:
            dst_layer.DeleteField(layer_definition_out.GetFieldIndex(field_name))
            in_fields.remove(field_name)
    if add_field is not None:
        for field in add_field:
            dst_layer.CreateField(ogr.FieldDefn(field, add_field[field]))
    return in_fields


def centrality_normalization(shp, node_number, generation_count):
    """Normalization of centrality values by the number of possible links between substations and generation;
    distribution of normalized values equally between parallel edges of the same voltage class

        Parameters
        ----------
        shp: shapefile
           path to the shapefile with calculated centrality.

        node_number: int
            number of power points in network

        generation_count: int
            number of generation points in network

        Returns
        -------
        None"""
    out_ds = ogr.GetDriverByName('ESRI Shapefile').Open(shp, 1)
    layer = out_ds.GetLayer()
    for feature in layer:
        count_field = feature.GetField('COUNTFID') - 1
        count_circuit = feature.GetField('Circ_Count')
        el_cen = float(count_field) / ((node_number * (node_number - 1)) - generation_count * (generation_count - 1))
        el_centrality_distributed = el_cen/count_circuit
        feature.SetField('El_Cen', el_cen)
        feature.SetField('El_C_Distr', el_centrality_distributed)
        layer.SetFeature(feature)


if __name__ == "__main__":
    os.chdir(r'f:\YandexDisk\Projects\RFFI_Transport\Ural_Siberia')
    power_lines = 'Lines_P.shp'
    power_points = 'Points_P.shp'
    path_output = 'Output'

    output_shp = os.path.join(path_output, 'el_centrality.shp')
    edges = os.path.join(path_output, 'edges.shp')
    node_count, generation_count, substation_count = el_centrality(power_lines, power_points, 'Name',
                                                                   'Weight', 'Voltage', path_output)
    create_cpg(edges)
    data_source = ogr.GetDriverByName('ESRI Shapefile').Open(edges, 1)
    layer = data_source.GetLayer()
    geometry_extraction(layer)
    dissolve_layer(layer, output_shp, delete_fields=['ident', 'Geometry'], add_fields={'El_Cen': ogr.OFTReal,
                                                                'El_C_Distr': ogr.OFTReal}, stats_dict={'COUNT': 'FID'})
    centrality_normalization(output_shp, node_count, generation_count)
