import networkx as nx
import geopandas as gpd
import momepy
import os
import random
import math
import matplotlib.pyplot as plt
from shapely.geometry import LineString

# Путь к вашим файлам
os.chdir(r"d:\YandexDisk\Projects\Networks\MES\Topologized_WGS")

def geo_distance(node1, node2):
    """Вычисляет сферическое расстояние между двумя узлами на основе их геодезических координат (широты и долготы) с использованием формулы гаверсинуса."""
    R = 6371.0  # Радиус Земли в километрах

    # Преобразование координат из градусов в радианы
    lat1, lon1 = map(math.radians, node1)
    lat2, lon2 = map(math.radians, node2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Формула гаверсинуса
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def geo_latticization(graph, max_iterations=1000, threshold_coef=5):
    for _ in range(max_iterations):
        edges = list(graph.edges())
        edge1 = random.choice(edges)
        a, b = edge1  # Узлы первого ребра

        # Находим подходящее второе ребро
        for c, d in edges:
            if len({a, b, c, d}) == 4 and min(geo_distance(a, c), geo_distance(b, d)) <= geo_distance(a,
                                                                                                      b) * threshold_coef:
                # Выполняем перестройку, если найдено подходящее ребро
                original_length = geo_distance(a, b) + geo_distance(c, d)
                new_length_1 = geo_distance(a, c) + geo_distance(b, d)
                new_length_2 = geo_distance(a, d) + geo_distance(b, c)

                if new_length_1 < original_length or new_length_2 < original_length:
                    if graph.has_edge(a, b):
                        graph.remove_edge(a, b)
                    if graph.has_edge(c, d):
                        graph.remove_edge(c, d)

                    if new_length_1 < new_length_2:
                        graph.add_edge(a, c)
                        graph.add_edge(b, d)
                    else:
                        graph.add_edge(a, d)
                        graph.add_edge(b, c)

                    # Проверка на сохранение связности
                    if not nx.is_connected(graph):
                        # Откат изменений, если граф потерял связность
                        if graph.has_edge(a, c):
                            graph.remove_edge(a, c)
                        if graph.has_edge(b, d):
                            graph.remove_edge(b, d)
                        if graph.has_edge(a, d):
                            graph.remove_edge(a, d)
                        if graph.has_edge(b, c):
                            graph.remove_edge(b, c)
                        graph.add_edge(a, b)
                        graph.add_edge(c, d)

                # Завершаем поиск подходящего ребра после успешной попытки
                break

    return graph


def graph_visualisation(subgraph, geo_regularized_graph, random_graph):
    fig, ax = plt.subplots(figsize=(12, 8))

    original_nodes, original_edges = momepy.nx_to_gdf(subgraph, points=True, lines=True)
    geo_nodes, geo_edges = momepy.nx_to_gdf(geo_regularized_graph, points=True, lines=True)
    random_nodes, random_edges = momepy.nx_to_gdf(random_graph, points=True, lines=True)

    # Визуализация оригинального графа
    original_edges.plot(ax=ax, color='red', linewidth=2, label='Original Graph')
    # Визуализация георегулярного графа
    geo_edges.plot(ax=ax, color='green', linewidth=1, label='Geo-Regularized Graph')
    # Визуализация рандомизированного графа
    random_edges.plot(ax=ax, color='blue', linewidth=0.5, label='Randomized Graph')

    plt.legend()
    plt.title(f'Graph Visualization for Year {year}')
    plt.show()


def geolattisized_omega(year, niter=10):
    def omega_analysis(year):
        # Загрузка данных
        net = gpd.read_file(r"TL_{0}.shp".format(year))
        net = net.explode(index_parts=True)
        net = net.reset_index(drop=True)

        # Преобразование в граф
        G = momepy.gdf_to_nx(net)
        G = nx.Graph(G)

        # Нахождение крупнейшей компоненты связности
        largest_component = max(nx.connected_components(G), key=len)
        subgraph = G.subgraph(largest_component).copy()

        # Создание георегулярного аналога
        geo_regularized_graph = geo_latticization(subgraph.copy(), max_iterations=len(subgraph.copy().edges()))
        for u, v, data in geo_regularized_graph.edges(data=True):
            data['geometry'] = LineString([u, v])
        random_graph = nx.random_reference(subgraph.copy())  # random_rewiring(subgraph.copy())
        for u, v, data in random_graph.edges(data=True):
            data['geometry'] = LineString([u, v])

        avg_length_rnd = nx.average_shortest_path_length(random_graph)
        avg_length = nx.average_shortest_path_length(subgraph)
        clustering = nx.average_clustering(subgraph)
        clustering_latt = nx.average_clustering(geo_regularized_graph)
        omega = (avg_length_rnd / avg_length) - (clustering / clustering_latt)

        return omega

    total_omega = 0
    for _ in range(niter):
        total_omega += omega_analysis(year)
    return total_omega / niter


#year = 1970  # Укажите год для анализа
for year in [1970, 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015]:
    print(geolattisized_omega(year))
