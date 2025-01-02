import geopandas as gpd
import math
from sqlalchemy import create_engine
from shapely import Polygon


db = "postgresql://postgres:123456789@localhost:5432/satino"
con = create_engine(db)
sql = "SQL * FROM base.land_parcels"
parcels = gpd.GeoDataFrame.from_postgis(sql, con)

parcels.plot()

# Работа с координатами
print(parcels.geometry)
print(type(parcels.geometry))
print(len(parcels.geometry[0].geoms))
print(parcels.geometry[0].geoms[0].exterior.coords[0])


#geom = parcels.geometry[0]

def bbox_multipolygon(geom):
    xmin = math.inf
    ymin = math.inf
    xmax = -math.inf
    ymax = -math.inf
    for g in geom.geoms:
        for xy in g.exterior.coords:
            if xy[0] < xmin:
                xmin = xy[0]
            if xy[1] < ymin:
                ymin = xy[1]
            if xy[0] > xmax:
                xmax = xy[0]
            if xy[1] > ymax:
                ymax = xy[1]
    box_coords = ((xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin))
    return Polygon(box_coords)

#bbox_multipolygon(parcels.geometry[0])

boxes = gpd.GeoSeries(map(bbox_multipolygon, parcels.geometry))
print(boxes)

geom_name = list(parcels.select_dtypes('geometry'))[0] # список названий всех столбцов, содержащих геометрию
result = gpd.GeoDataFrame(
    parcels.drop(columns=geom_name),
    geometry=boxes,
    crs=parcels.crs
)

result.plot()

result.to_postgis('land_parcels_bbox', con, 'base', 'replace')

# Вычисление направлений линий

def get_dirs(layer):
