# -*- coding: utf-8 -*-
import arcpy, sys
reload(sys)
import networkx as nx
import os
import nx_multi_shp as nxm
sys.setdefaultencoding('utf8')


folder = 'BackUp230201'
arcpy.env.workspace = r'F:\YandexDisk\Projects\MES_evolution\{0}\SHP'.format(folder)
arcpy.env.overwriteOutput = True


def count_dangles(KVL_dissolve, year):
    dangle_points = arcpy.FeatureVerticesToPoints_management(KVL_dissolve, 'Dangles', 'DANGLE')
    count_dangles = arcpy.Dissolve_management(dangle_points, "Count_dangles", "Name", "Name COUNT")
    dangle_one = arcpy.MakeFeatureLayer_management(count_dangles, "One_Dangles", "COUNT_Name = 1")
    if int(str(arcpy.GetCount_management(dangle_one))) > 0:
        raise Exception('Only one dangle for line in {0} year network!'.format(year))


def line_connectedness(lines, out, year):
    print(year)
    disconnected_lines = []
    for line in sorted(list(set(row[0] for row in arcpy.da.SearchCursor(lines, "Name")))):
        #print(line)
        selection = arcpy.MakeFeatureLayer_management(lines, "Selected_line", "Name = '{0}'".format(line))
        arcpy.FeatureClassToFeatureClass_conversion(selection, out, 'Line.shp')
        os.chdir(out)
        G = nxm.read_shp('Line.shp', 'Name').to_undirected()
        if nx.number_connected_components(G) > 1:
            disconnected_lines.append(line)
            print(line)
            print(" has {} components".format(nx.number_connected_components(G)))
    if len(disconnected_lines) > 0:
        print('{0} line(s) with disconnected segments in {1}'.format(len(disconnected_lines), year))


os.chdir(r'F:\YandexDisk\Projects\MES_evolution\{0}\SHP'.format(folder))
# for i in range(1965, 1966): #range(1936, 1937):
#     count_dangles('T{0}_lines'.format(i), i)
#     print(i)

for i in range(2021, 2023):
    line_connectedness('TL_{0}.shp'.format(i), 'F:\YandexDisk\Projects\MES_evolution\{0}\Components'.format(folder), i)
