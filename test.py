# -*- coding: utf-8 -*-
import arcpy

arcpy.env.workspace = r'D:\YandexDisk\Projects\GIS\Физ\Ex4\Satino.gdb'
arcpy.env.overwriteOutput = True

landuse = arcpy.Copy_management(r'Thematic\LandUse', r'Thematic\LandUse_copy')
arcpy.AddField_management(landuse, 'General_type', 'TEXT')
rows = arcpy.da.UpdateCursor(landuse, ['Land_Type', 'General_type'])
for row in rows:
    if row[0] == 'Выгоны':
        row[1] = 'Сельское хозяйство'
    if row[0] == 'Пашня':

    rows.updateRow(row)
