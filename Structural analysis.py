import networkx as nx
import geopandas as gpd
import momepy
import matplotlib.pyplot as plt
import os

# Путь к вашим файлам
os.chdir(r"d:\YandexDisk\Projects\Networks\MES\Topologized")

# Словарь для хранения данных по компонентам
omega_by_components = {}

# Цикл по годам
for year in range(1950, 1970):
    try:
        # Загрузка данных
        net = gpd.read_file(r"d:\YandexDisk\Projects\Networks\MES\Topologized\TL_{0}.shp".format(year))
        net = net.explode(index_parts=True)
        net = net.reset_index(drop=True)  # Сброс индексов

        # Преобразование в граф
        G = momepy.gdf_to_nx(net)
        G = nx.Graph(G)  # Преобразование в неориентированный граф

        # Вычисление значений omega для каждой связной компоненты
        components = list(nx.connected_components(G))
        for idx, component in enumerate(components):
            subgraph = G.subgraph(component).copy()

            # Проверка на минимальное количество узлов
            if subgraph.number_of_nodes() < 4:
                continue

            # Вычисление omega с использованием функции networkx
            omega = nx.omega(subgraph)

            # Сохранение данных по компонентам
            if idx not in omega_by_components:
                omega_by_components[idx] = {'years': [], 'omega_values': []}
            omega_by_components[idx]['years'].append(year)
            omega_by_components[idx]['omega_values'].append(omega)

            print(f"Year: {year}, Component Index: {idx}, Omega: {omega}")

    except Exception as e:
        print(f"Error processing year {year}: {e}")

# Построение графика
plt.figure(figsize=(12, 6))

for idx, data in omega_by_components.items():
    years = data['years']
    omega_values = data['omega_values']

    # Соединение точек линией для каждой компоненты
    plt.plot(years, omega_values, 'o-', label=f'Component {idx}', alpha=0.7)

plt.xlabel('Year')
plt.ylabel('Omega Value')
plt.title('Dependence of Omega Value on Year (by Connected Component)')
plt.grid(True)
plt.legend()
plt.show()
