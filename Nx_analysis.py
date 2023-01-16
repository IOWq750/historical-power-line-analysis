# -*- coding: utf-8 -*-
import sys
import networkx as nx
import os
import time
import ogr
import nx_multi_shp as nxm
import Electric_Network_Centrality_Simple as elcen
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
#reload(sys)
#sys.setdefaultencoding('utf8')

def convert_shp_to_graph(input_shp, directed, multigraph, parallel_edges_attribute):
    """Converts a shapefile to networkx graph object in accordance to the given parameters.
        It can directed or undirected, simple graph or multigraph

        Parameters
        ----------
        input_shp: str
            shapefile path

        directed: str
            If value is true – directed graph will be created.
            If value is false - undirected graph will be created

        multigraph: str
            If value is true – multigraph will be created
            If value is false – simple graph will be created

        parallel_edges_attribute: str
            Field of the shapefile which allows to distinguish parallel edges.
            Note that it could be a field of different types, but all values of this attribute should be filled
        Returns
        -------
        Graph
        """
    if multigraph == 'true':
        G = nxm.read_shp(r'{0}'.format(input_shp), parallel_edges_attribute, simplify=True,
                                  geom_attrs=True, strict=True)
    else:
        G = nx.read_shp(r'{0}'.format(input_shp))
    if directed == 'true':
        graph = G
    else:
        graph = G.to_undirected()
    return graph


def export_graph_to_shp(G, multy, output_workspace, multy_attribute=None):
    """Export networkx graph object to shapefile

        Parameters
        ----------
        G: networkx graph object

        multy: str
            If value is true – multigraph will be created
            If value is false – simple graph will be created

        output_workspace: str
            path to the folder with output shapefile

        multy_attribute: str
            Field of the shapefile which allows to distinguish parallel edges.
            Note that it could be a field of different types, but all values of this attribute should be filled

        Returns
        -------
        None

    """
    for item in ['edges.shp', 'nodes,shp']:
        filename = os.path.join(output_workspace, item)
        if os.path.exists(filename):
            os.remove(filename)
    if multy == 'true':
        nxm.write_shp(G, multy_attribute, output_workspace)
    else:
        nx.write_shp(G, output_workspace)


def export_path_to_shp(G, multy, output_workspace, path_dict_list):
    """Export of path (list of nodes) through graph to shapefile

        Parameters
        ----------
        G: networkx graph object

        multy: str
            If value is true – multigraph will be created
            If value is false – simple graph will be created

        output_workspace: str
            path to the folder with output shapefile

        path_dict_list: list
            list of dicts kind of {start: [node1, node2, node3]}

        Returns
        -------
        None
    """
    new_graph = nx.MultiGraph(crs=G.graph['crs'])
    e = 0
    for path_dict in path_dict_list:
        a = 0
        for node in path_dict:
            path_list = path_dict[node]
            path_list.insert(0, node)
            b = 0
            for edge in G.edges(keys=True, data=True):
                attribute_data = new_graph.get_edge_data(*edge)
                new_attribute_data = {}
                Wkt = attribute_data['Wkt']
                c = 0
                for i in range(len(path_list) - 1):
                    identifier = str(e) + str(a) + str(b) + str(c)
                    if tuple([tuple(path_list[i]), tuple(path_list[i + 1])]) == tuple(edge[:2])\
                            or tuple([tuple(path_list[i + 1]), tuple(path_list[i])]) == tuple(edge[:2]):
                        new_graph.add_edge(edge[0], edge[1], identifier, Name=edge[2], ident=identifier, Wkt=Wkt)
                        new_attribute_data[edge[0], edge[1], identifier] = attribute_data
                        nx.set_edge_attributes(new_graph, new_attribute_data)
                    c += 1
                b += 1
            a += 1
        e += 1
    if multy == 'true':
        nxm.write_shp(new_graph, 'ident', output_workspace)
    else:
        nx.write_shp(new_graph, output_workspace)


def node_betweenness_centrality(G, normalization, weight):
    """Calculation of betweenness centrality for nodes"""
    bc = nx.betweenness_centrality(G, normalized=normalization, weight=weight)
    nx.set_node_attributes(G, bc, 'BC')


def edge_betweenness_centrality(G, normalization, weight):
    """Calculation of betweenness centrality for edges"""
    ebc = nx.edge_betweenness_centrality(G, normalized=normalization, weight=weight)
    return ebc


def betweenness_multiedge_distribution(G, ebc):
    """Distribution of value equally between parallel edges in multigraph"""
    multiedges = [(element[0], element[1]) for element in G.edges(keys=True)]
    edge_betweenness_values = {}
    for edge in multiedges:
        count = multiedges.count(edge)
        betweenness = ebc[edge]/count
        for item in G.edges(keys=True):
            if edge == tuple([item[0], item[1]]):
                edge_betweenness_values[item] = betweenness
    nx.set_edge_attributes(G, edge_betweenness_values, 'BC')


def create_cpg(shapefile):
    """Encoding description file creation"""
    with open('{}.cpg'.format(shapefile), 'w') as cpg:
        cpg.write('cp1251')


os.chdir(r'F:\YandexDisk\Projects\MES_evolution\ALL')
# for i in range(1936, 2021):
#     G = convert_shp_to_graph('T{0}_lines.shp'.format(i), 'false', 'true', 'Name')
#     normalization = True
#     node_betweenness_centrality(G, normalization, 'Weight')
#     ebc = edge_betweenness_centrality(G, normalization, 'Weight')
#     betweenness_multiedge_distribution(G, ebc)
#     print(i)
#     try:
#         export_graph_to_shp(G, 'true', r'BC_Output\{0}_BC'.format(i), 'Name')
#     except:
#         os.mkdir(r'BC_Output\{0}_BC'.format(i))
#         export_graph_to_shp(G, 'true', r'BC_Output\{0}_BC'.format(i), 'Name')
#     create_cpg(r'BC_Output\{0}_BC\edges'.format(i))
#     create_cpg(r'BC_Output\{0}_BC\nodes'.format(i))

# Calculation of electrical network centrality
for i in range(2020, 2021):
    print(i)
    power_lines = r'T{0}_lines.shp'.format(i)
    power_points = r'Points_{0}.shp'.format(i)
    path_output = 'EC'

    output_shp = os.path.join(path_output, 'el_centrality_{0}.shp'.format(i))
    edges = os.path.join(path_output, 'edges.shp')
    node_count, generation_count, substation_count = elcen.el_centrality(power_lines, power_points, 'Name',
                                                                   'Weight', 'Voltage_st', path_output)
    elcen.create_cpg(edges)
    data_source = ogr.GetDriverByName('ESRI Shapefile').Open(edges, 1)
    layer = data_source.GetLayer()
    elcen.geometry_extraction(layer)
    elcen.dissolve_layer(layer, output_shp, delete_fields=['ident', 'Geometry'], add_fields={'El_Cen': ogr.OFTReal,
                                                                'El_C_Distr': ogr.OFTReal}, stats_dict={'COUNT': 'FID'})
    elcen.centrality_normalization(output_shp, node_count, generation_count)


# Calculation of degree
# degree_list = []
# for i in range(2020, 2021):
#     print(i)
#     G = nxm.read_shp('T{0}_lines.shp'.format(i), 'Name').to_undirected()
#     degree_sequence = sorted((d for n, d in G.degree()), reverse=True)
#     dmax = max(degree_sequence)
#
#     ax2 = fig.add_subplot(axgrid[3:, 2:])
#     ax2.bar(*np.unique(degree_sequence, return_counts=True))
#     ax2.set_title("Degree histogram")
#     ax2.set_xlabel("Degree")
#     ax2.set_ylabel("# of Nodes")
#
#     fig.tight_layout()
#     plt.show()


# # Calculation of degree
# glob_eff_list = []
# degree_list = []
# for i in range(1936, 2021):
#     print(i)
#     G = nxm.read_shp('T{0}_lines.shp'.format(i), 'Name').to_undirected()
#     #print(nx.average_shortest_path_length(G, weight='Shape_Leng')) #weight='Weight' weight='Shape_Leng'
#     #glob_eff_list.append(nx.global_efficiency(G))
#     degree_sequence = sorted((d for n, d in G.degree()), reverse=True)
# fig, ax = plt.subplots()  # Create a figure containing a single axes.
# ax.plot(range(1936, 2021), glob_eff_list)  # Plot some data on the axes.
# plt.show()
#
# for i in range(1936, 2021):
#     print(i)
#     G = nxm.read_shp('T{0}_lines.shp'.format(i), 'Name').to_undirected()
#     cc = nx.closeness_centrality(G)
#     nx.set_node_attributes(G, cc, 'CC')
#     nxm.write_shp(G, 'Name', r'CC\{0}_CC'.format(i))

# for i in range(1936, 2021):
#     G = nx.read_shp('T{0}_lines.shp'.format(i)).to_undirected()
#     ave_len_weight = nx.average_shortest_path_length(G, 'Weight')
#     ave_len_shape = nx.average_shortest_path_length(G, 'Shape_Leng')
#     ave_len = nx.average_shortest_path_length(G)
#     clust_coef = nx.average_clustering(G)
#     print(clust_coef)

# i = 2020
# G = nx.read_shp('T{0}_lines.shp'.format(i)).to_undirected()
# R = nx.random_reference(G)
# nx.write_shp(R, r'Random'.format(i))
# L = nx.lattice_reference(G)
# nx.write_shp(L, r'Lattice'.format(i))
# start = time.time()
# print(i)
# print(nx.sigma(G))
# print(nx.omega(G))
# print(time.time() - start)


# for i in range(1987, 1988):
#     G = nxm.read_shp('T{0}_lines.shp'.format(i), 'Name').to_undirected()
#     print('network in {0} has {1} connected components'.format(i, nx.number_connected_components(G)))
#     S = [G.subgraph(c).copy() for c in nx.connected_components(G)]
#     print(S)
#
#     nxm.write_shp(S[0], 'Name', r'components\1')
#     nxm.write_shp(S[1], 'Name', r'components\2')
#nxm.write_shp(S[2], r'components\3')
#nxm.write_shp(S[3], r'components\4')
#nxm.write_shp(S[4], r'components\5')
# nx.write_shp(S[5], r'components\6')