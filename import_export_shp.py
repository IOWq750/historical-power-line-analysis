# -*- coding: utf-8 -*-
import networkx as nx
import nx_multi_shp
import os


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
        G = nx_multi_shp.read_shp(r'{0}'.format(input_shp), parallel_edges_attribute, simplify=True,
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
        nx_multi_shp.write_shp(G, multy_attribute, output_workspace)
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
        nx_multi_shp.write_shp(new_graph, 'ident', output_workspace)
    else:
        nx.write_shp(new_graph, output_workspace)
