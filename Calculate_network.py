# -*- coding: utf-8 -*-
import arcpy, sys
import networkx as nx
import os
import nx_multi_shp as nxm
reload(sys)
sys.setdefaultencoding('utf8')


folder = 'BackUp230201'
arcpy.env.workspace = r'F:\YandexDisk\Projects\MES_evolution\{0}'.format(folder)
arcpy.env.overwriteOutput = True

for i in range(1933, 2023):
    print(i)
    arcpy.FeatureClassToFeatureClass_conversion(r'MES_Queries.gdb\P_{0}'.format(i), r'SHP', 'P_{0}.shp'.format(i))
    # gen = arcpy.MakeFeatureLayer_management(r'MES_Queries.gdb\P_{0}'.format(i),
    #                                         'generation', where_clause="Type = 'ЭС' OR Type = 'РУ'")
    # subs = arcpy.MakeFeatureLayer_management(r'MES_Queries.gdb\P_{0}'.format(i),
    #                                         'substations', where_clause="Type = 'ПС' OR Type = 'РП'")
    # arcpy.FeatureClassToFeatureClass_conversion(gen, r'SHP', 'Gen_{0}.shp'.format(i))
    # arcpy.FeatureClassToFeatureClass_conversion(subs, r'SHP', 'Sub_{0}.shp'.format(i))
