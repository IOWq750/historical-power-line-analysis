# -*- coding: utf-8 -*-
import arcpy, sys, re
reload(sys)
sys.setdefaultencoding('utf8')

arcpy.env.workspace = r'F:\YandexDisk\Projects\MES_evolution\MES_2022.gdb'
arcpy.env.overwriteOutput = True

# Process: Project
def projecting_dataset(projection):
    arcpy.CreateFeatureDataset_management(arcpy.env.workspace, "Network", projection)
    arcpy.env.outputZFlag = "Disabled"
    arcpy.env.outputCoordinateSystem = projection
    input_lines_p = arcpy.FeatureClassToFeatureClass_conversion(r"Placemarks\Polylines", "Network", "Lines_p")
    input_points_p = arcpy.FeatureClassToFeatureClass_conversion(r"Placemarks\Points", "Network", "Points_p")
    for field in ["Type", "Complexity", "Trace_Version", "Status"]:
        arcpy.AddField_management(input_lines_p, field, "TEXT")
    arcpy.AddField_management(input_points_p, "Point_Type", "TEXT")
    arcpy.AddField_management(input_points_p, "Voltage", "LONG")
    arcpy.AddField_management(input_lines_p, "Voltage", "LONG")
    return input_lines_p, input_points_p


# Extract line type to the attribute table
def line_type_extraction(input_lines_p):
    rows = arcpy.da.UpdateCursor(input_lines_p, ["FolderPath", "Type", "Name", "Trace_Version", "Status"])
    for row in rows:
        if "/ВЛ" in str(row[0]):
            row[1] = "ВЛ"
            row[4] = "Действующая"
        elif "/КЛ" in str(row[0]):
            row[1] = "КЛ"
            row[4] = "Действующая"
        elif "/Строительство" in str(row[0]):
            row[4] = "Строительство"
        if "!" in row[2]:
            row[3] = "Схематически точная"
            row[2] = row[2][1:]
        else:
            row[3] = "Геометрически точная"
        rows.updateRow(row)
    del row
    del rows


# Extract voltage to the attribute table
def voltage_extraction(input):
    rows = arcpy.da.UpdateCursor(input, ["Name", "Voltage"])
    for row in rows:
        volt = re.search(r'\s35|\s110|\s150|\s220|\s330|\s400|\s500|\s750', str(row[0]))
        if volt is not None:
            row[1] = volt.group(0)[1:]
        rows.updateRow(row)
    del row
    del rows


# Extract point names from the line name
def ends_extraction(input_lines):
    for item in ["Start", "End", "Circuit", "Operate_Name"]:
        arcpy.AddField_management(input_lines, item, "TEXT")
    rows = arcpy.da.UpdateCursor(input_lines, ["Name", "Start", "End", "Circuit", "Operate_Name"])
    for row in rows:
        res0 = re.split(r'\s–\s', str(row[0]))
        if len(res0) == 2:
            # Точка начала
            res1 = re.split(r'\s', res0[0])
            row[1] = re.sub(r'_', r' ', res1[-1])
            # Диспетчерский номер линии
            if len(res1) == 3:
                row[4] = res1[1]
            # Точка конца
            res2 = re.split(r'\s', res0[1])
            row[2] = re.sub(r'_', r' ', res2[0])
            # Список потенциальных наименований кратных цепей
            circuits_names = ['1', '2', '3', '4', '5', '6', '4А', '4Б', '5А', '5Б', 'I', 'II', 'III', 'IV', 'V', 'VI',
                              'VII', 'южная', 'северная', 'восточная', 'западная', 'левая', 'правая', 'А', 'Б', 'синяя',
                              'красная', 'зеленая', 'желтая']
            for name in circuits_names:
                if res2[1] == name:
                    row[3] = name
        else:
            row[1] = ""
            row[2] = ""
        rows.updateRow(row)
    del row
    del rows


def name_correction(input_lines):
    rows = arcpy.da.UpdateCursor(input_lines, ["Name"])
    for row in rows:
        row[0] = re.sub(r'_', r' ', row[0])
        rows.updateRow(row)
    del row
    del rows


# Extract point names from the point
def name_extraction(input_points):
    for item in ["Point_Name", "Owner", "Operate_Number"]:
        arcpy.AddField_management(input_points, item, "TEXT")
    rows = arcpy.da.UpdateCursor(input_points, ["Name", "Point_Name", "Owner", "Operate_Number", "Point_Type"])
    for row in rows:
        arcpy.AddMessage(row[0])
        if row[4] == r'ЗКРП' or row[4] == r'СП' or row[4] == r'ПП':
            res0 = re.split(r'\s', row[0], maxsplit=1)
            if len(re.findall(u'\u2116'+r'\d', res0[1]))>0:
                row[3] = re.split(r'\s', res0[1], maxsplit=1)[0][1:]
        elif row[4] == r'ЭС':
            row[1] = row[0]
        elif row[4] == 'РУ':
            res0 = re.split(r'\s', row[0], maxsplit=1)
            row[1] = re.split(r'\s35|\s110|\s150|\s220|\s330|\s400|\s500|\s750', res0[1], maxsplit=1)[0]
        else:
            res0 = re.split(r'\s', row[0], maxsplit=1)
            # Поиск "№\d"
            if len(re.findall(u'\u2116'+r'\d', res0[1]))>0 and res0[1][0] == u'\u2116':
                res1 = re.split(r'\s', res0[1], maxsplit=1)[1]
                # Присвоение номера ПС при наличии
                row[3] = re.split(r'\s', res0[1], maxsplit=1)[0][1:]
            else:
                res1 = res0[1]
                if 'ГПП' in res0[0] or 'РПП' in res0[0]:
                    gpp = re.split(r'\s35|\s110|\s150|\s220|\s330|\s400|\s500|\s750', res0[1], maxsplit=1)
                    if len(gpp) > 1:
                        row[1] = res0[0] + ' ' + re.sub(u'\u0430\u0431.', '', gpp[0])
                    else:
                        row[1] = res0[0]
            res2 = re.split(r'аб\.|тяг\.|-тяговая', str(res1))
            if len(res2) == 2:
                # Запись имени ПС
                if "-тяговая" in str(res1):
                    row[1] = res2[0] + "-тяговая"
                elif row[1] is None:
                    row[1] = res2[0].strip()
                if "аб." in str(res1):
                    # Обозначение абонентских подстанций
                    row[2] = 'абонентская'
                else:
                    # Обозначение тяговых подстанций
                    row[2] = 'тяговая'
            else:
                row[2] = 'ТСО'
                res3 = re.split(r'\s35|\s110|\s150|\s220|\s330|\s400|\s500|\s750', res2[0], maxsplit=1)
                if len(res3) == 2 and row[1] is None:
                    # Запись имени ПС
                    row[1] = res3[0]
            if row[1] is None and row[3] is not None:
                row[1] = str(res0[0]) + " №" + str(row[3])
            if row[1] is None and res0[0][0:4] == "ТП-":
                row[1] = str(res0[0])
        rows.updateRow(row)
    del row
    del rows


# Extract point type
def point_type_extraction(point):
    rows = arcpy.da.UpdateCursor(point, ["FolderPath", "Point_Type"])
    for row in rows:
        generation = re.search(r'/Электростанции|/ЭС', str(row[0]))
        if generation is not None:
            row[1] = 'ЭС'
        else:
            p_type = re.search(r'/ПС|/ПП|/РП|/СП|/ЭС|/ЗКРП|/РУ|/\?', str(row[0]))
            if p_type is not None:
                row[1] = p_type.group(0)[1:]
        rows.updateRow(row)
    del row, rows
    arcpy.DeleteField_management(point, ['FolderPath', 'SymbolID', 'AltMode', 'Base', 'Snippet', 'PopupInfo', 'HasLabel',
                                  'LabelID'])


# Integrating and planarizing network with dangles
def integrating_network(lines, tolerance="0 Meters"):
    overhead_lines = arcpy.FeatureClassToFeatureClass_conversion(lines, "Network", "Lines_over_p",
                                                where_clause="Type = 'ВЛ'")
    cable_lines = arcpy.FeatureClassToFeatureClass_conversion(lines, "Network", "Lines_cable_p",
                                                where_clause="Type = 'КЛ'")
    arcpy.Integrate_management(overhead_lines, tolerance)
    arcpy.Integrate_management(cable_lines, "0.1 Meters")
    lines = arcpy.Merge_management([overhead_lines, cable_lines], "Lines_merge")
    split = arcpy.SplitLine_management(lines, "SplitLine")
    find = arcpy.FindIdentical_management(split, "in_memory/Find_Ident", ["Shape", "Name", "Voltage"],
                                          xy_tolerance=tolerance, output_record_option="ONLY_DUPLICATES")
    joined_split = arcpy.JoinField_management(split, "OBJECTID", find, "IN_FID")
    arcpy.DeleteIdentical_management(joined_split, ["Shape", "Name", "Voltage"], "0.1 Meters")
    unsplit = arcpy.Dissolve_management(joined_split, "Unsplited_Lines",
                ["Name", "Voltage", "Type", "Start", "End", "Circuit", "Operate_Name", "Trace_Version", "Status"],
                multi_part="MULTI_PART")
    return unsplit


# Создадим поле веса и словарь, обозначающий соответствие напряжения пропускной способности ЛЭП
def set_edge_weight(KVL_Dissolve):
    arcpy.AddField_management(KVL_Dissolve, "Capacity", "FLOAT")
    dictionary = {35: 0.07,
                  110: 0.02,
                  150: 0.01,
                  220: 0.005,
                  330: 0.0025,
                  400: 0.001428571,
                  500: 0.001111111,
                  750: 0.000454545,
                  None: None}
    rows = arcpy.da.UpdateCursor(KVL_Dissolve, ["Voltage", "Capacity"])
    for row in rows:
        row[1] = dictionary[row[0]]
        rows.updateRow(row)
    del row, rows
    arcpy.DeleteField_management(KVL_Dissolve,
                                 ['SymbolID', 'AltMode', 'Base', 'Clamped', 'Extruded', 'Snippet', 'PopupInfo'])
    single_part = arcpy.MultipartToSinglepart_management(KVL_Dissolve, "Single_Part")
    lines_p = arcpy.FeatureClassToFeatureClass_conversion(single_part, "Network", "Lines_p",
                                                where_clause="Status <> 'Строительство'")
    return lines_p


# kmz = arcpy.GetParameterAsText(0)
# path_gdb = arcpy.GetParameterAsText(1)
# name_gdb = arcpy.GetParameterAsText(2)
kmz = r'f:\YandexDisk\Projects\MES_evolution\Магистральные.kmz'
path_gdb = r'f:\YandexDisk\Projects\MES_evolution'
name_gdb = 'MES_2022'
tolerance = "0.5 Meters"
projection = "PROJCS['Asia_North_Equidistant_Conic',GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Equidistant_Conic'],PARAMETER['False_Easting',0.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',95.0],PARAMETER['Standard_Parallel_1',15.0],PARAMETER['Standard_Parallel_2',65.0],PARAMETER['Latitude_Of_Origin',30.0],UNIT['Meter',1.0]]"
# Convert kml to gdb
try:
    arcpy.KMLToLayer_conversion(kmz, path_gdb, name_gdb)
except:
    arcpy.Delete_management(r'{0}\{1}.gdb'.format(path_gdb, name_gdb))
    arcpy.KMLToLayer_conversion(kmz, path_gdb, name_gdb)
arcpy.env.workspace = (r'{0}\{1}.gdb'.format(path_gdb, name_gdb))
input_lines_p = projecting_dataset(projection)[0]
input_points_p = projecting_dataset(projection)[1]
point_type_extraction(input_points_p)
voltage_extraction(input_points_p)
name_extraction(input_points_p)
line_type_extraction(input_lines_p)
voltage_extraction(input_lines_p)
ends_extraction(input_lines_p)
name_correction(input_lines_p)
unsplit = integrating_network(input_lines_p, tolerance)
lines_p = set_edge_weight(unsplit)
list = [unsplit, "SplitLine", "Placemarks", "in_memory", "Dangles", "Near_Table", "Single_Part",
        "Ends", "Ends_Dissolve", "Identical", "Network/Lines_over_p", "Network/Lines_cable_p", "Lines_merge", "KVL_Dissolve_Temp"]
for item in list:
    arcpy.Delete_management(item)
arcpy.AddMessage("Network dataset is created")
