import networkx as nx
import geopandas as gpd
import momepy
import matplotlib.pyplot as plt
import os
import numpy as np
from scipy.spatial import distance

# Путь к вашим файлам
os.chdir(r"d:\YandexDisk\Projects\Networks\MES\Topologized")

# Функции для расчета автокорреляции
def morans_i(graph, values):
    n = len(values)
    mean_value = np.mean(values)
    num, denom = 0, 0
    for i in range(n):
        for j in range(n):
            if graph.has_edge(i, j):
                num += (values[i] - mean_value) * (values[j] - mean_value)
            denom += (values[i] - mean_value) ** 2
    weight_sum = len(graph.edges())
    return (n / weight_sum) * (num / denom) if denom != 0 else 0

def getis_ord_g(graph, values, threshold):
    total_value_sum = sum(values)
    g_statistic = 0
    for i in range(len(values)):
        local_sum = sum(values[j] for j in range(len(values)) if graph.has_edge(i, j) and distance.euclidean(graph.nodes[i]['pos'], graph.nodes[j]['pos']) <= threshold)
        g_statistic += local_sum * values[i]
    return g_statistic / (total_value_sum ** 2) if total_value_sum != 0 else 0

# Списки для хранения данных
years = []
morans_i_values = []
getis_ord_values = []

# Цикл по годам
for year in range(2020, 2021):
    try:
        # Загрузка данных
        net = gpd.read_file(r"d:\YandexDisk\Projects\Networks\MES\Topologized\TL_{0}.shp".format(year))
        net = net.explode(index_parts=True)
        net = net.reset_index(drop=True)  # Сброс индексов

        # Преобразование в граф
        G = momepy.gdf_to_nx(net)
        G = nx.Graph(G)  # Преобразование в неориентированный граф

        # Обработка несвязного графа: выделение самой большой компоненты
        if not nx.is_connected(G):
            largest_component = max(nx.connected_components(G), key=len)
            G = G.subgraph(largest_component).copy()

        # Добавление координат узлов (пример)
        positions = {i: (row.geometry.centroid.x, row.geometry.centroid.y) for i, row in net.iterrows()}
        nx.set_node_attributes(G, positions, 'pos')

        # Значения для анализа (например, степени узлов, без учета весов)
        avg_path_lengths = [len(list(G.neighbors(u))) for u in G.nodes()]  # Использование количества соседей (степени узлов)

        # Рассчет индексов для пространственного лага
        thresholds = np.linspace(0.1, 1.0, 10)  # Примерные значения лагов
        morans_i_values_year = []
        getis_ord_values_year = []

        for threshold in thresholds:
            morans_i_value = morans_i(G, avg_path_lengths)
            getis_ord_value = getis_ord_g(G, avg_path_lengths, threshold)

            morans_i_values_year.append(morans_i_value)
            getis_ord_values_year.append(getis_ord_value)

        # Сохранение значений
        years.append(year)
        morans_i_values.append(morans_i_values_year)
        getis_ord_values.append(getis_ord_values_year)

        print(f"Year: {year} completed.")

    except Exception as e:
        print(f"Error processing year {year}: {e}")

# Построение графика зависимости
plt.figure(figsize=(12, 6))
for i, year in enumerate(years):
    plt.plot(thresholds, morans_i_values[i], marker='o', linestyle='-', label=f'Moran\'s I ({year})', alpha=0.7)
    plt.plot(thresholds, getis_ord_values[i], marker='s', linestyle='--', label=f'Getis-Ord G ({year})', alpha=0.7)

plt.xlabel('Spatial Lag Threshold')
plt.ylabel('Autocorrelation Index Value')
plt.title('Dependence of Autocorrelation Index on Spatial Lag (Largest Connected Component, No Edge Weights)')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True)
plt.show()
