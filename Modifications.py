# -*- coding: utf-8 -*-
import arcpy
import os


def unique_values(table, field):
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({row[0] for row in cursor})


def relation_redundancy_decrease(lines, out):
    arcpy.env.workspace = out
    arcpy.env.overwriteOutput = True
    copy_lines = arcpy.Copy_management(lines, 'PL_Spat_Time')
    arcpy.DeleteIdentical_management(copy_lines, "geometry;Type;Year_start;Year_end")
    arcpy.DeleteField_management(copy_lines, "Type;Voltage;Name;Start;End;Circuit;IsBranch;Branch_points;Capacity;"
                                             "Year_start_name;Year_end_name;Doubt_Years;Doubt_geometry")
    sp_join = arcpy.SpatialJoin_analysis(copy_lines, lines,  "PL_Attributes", "JOIN_ONE_TO_MANY", "KEEP_ALL",
                               match_option="ARE_IDENTICAL_TO")
    arcpy.DeleteField_management(sp_join, "Join_Count;Year_start_1;Year_end_1;geometry_Length_1")
    print("Redundancy decreased")


def voltage_modification(lines, line_attrs):
    """"Identification of voltage modification (decrease or increase in nominal class) for segment in a certain year
    Parameters
    ----------

    lines:  ESRI GDB polyline feature class
        Feature class with unique geometry and time span borders

    line_attrs:  ESRI GDB table with unique attribute values for power line segment
        Feature class with all attributes
    """
    arcpy.AddField_management(line_attrs, 'Modification', 'TEXT')  # Field for segment classification
    with arcpy.da.SearchCursor(lines, ['fid']) as segments:
        for segment in segments:
            id = segment[0]
            attributes = arcpy.MakeFeatureLayer_management(line_attrs, "lines", "TARGET_FID = {0}".format(id))
            voltages = unique_values(attributes, 'Voltage')
            years_start = unique_values(attributes, 'Year_start_name')
            years_end = unique_values(attributes, 'Year_end_name')
            if len(voltages) == 2:  # Only two unique values of voltage is possible
                print(id)
                mod_dict = {}
                with arcpy.da.SearchCursor(attributes, ['Year_start_name', 'Voltage']) as rows:
                    for row in rows:
                        mod_dict[row[0]] = row[1]
                first_voltage = mod_dict[years_start[0]]
                i = 0
                while mod_dict[years_start[i]] == first_voltage:
                    if i < len(years_start) - 1:
                        i += 1
                else:
                    year_of_voltage_mod = years_start[i]
                    print("Year of modification ", years_start[i])
                with arcpy.da.UpdateCursor(attributes, ['Year_start_name', 'Modification']) as rows2:
                    for row in rows2:
                        # Second condition for cases when there is a time gap between
                        # line implementations (year_start_name – year_end_name)
                        if row[0] == year_of_voltage_mod and row[0] in years_end:
                            row[1] = "Voltage modification"
                        rows2.updateRow(row)


def end_year_check(lines, line_attrs):
    """"Identification of voltage modification (decrease or increase in nominal class) for segment in a certain year
    Parameters
    ----------

    lines:  ESRI GDB polyline feature class
        Feature class with unique geometry and time span borders

    line_attrs:  ESRI GDB table with unique attribute values for power line segment
        Feature class with all attributes
    """
    with arcpy.da.SearchCursor(lines, ['fid', 'Year_end']) as segments:
        for segment in segments:
            id = segment[0]
            attributes = arcpy.MakeFeatureLayer_management(line_attrs, "lines", "TARGET_FID = {0}".format(id))
            years_end = unique_values(attributes, 'Year_end_name')
            if segment[1] not in years_end:
                print(id)

def get_morphological_modifications(year, initial_data, out):
    """"Constructing a layer for power lines segment modifications for the certain year"""
    arcpy.env.workspace = out
    arcpy.env.overwriteOutput = True
    geom = os.path.join(initial_data, 'PL_Spat_Time')
    attrs = os.path.join(initial_data, 'PL_Attributes')
    lines = arcpy.Copy_management(attrs, 'PL')
    arcpy.JoinField_management(lines, "TARGET_FID", geom, 'fid')
    branch_points = os.path.join(initial_data, 'Branch_Point')
    clause = "Year_start_name <= {0} AND (Year_end_name IS NULL OR Year_end_name > {0}) OR (Year_end = {0} AND " \
             "Year_end_name = {0})".format(year)

    selected_lines = arcpy.FeatureClassToFeatureClass_conversion(attrs, out,
                                                                'selected_lines_{0}'.format(year), clause)
    arcpy.AddField_management(selected_lines, 'Dissolution', 'TEXT')  # Field for segment classification
    rows = arcpy.da.UpdateCursor(selected_lines,
                                 ['Year_start', 'Year_end', 'Year_start_name', 'Year_end_name', 'Dissolution', 'Voltage', 'Modification'])
    for row in rows:
        if row[0] == row[2] == year:
            row[4] = "New"
        elif row[1] == row[3] == year:
            row[4] = "Old"
        elif row[6] == "Voltage modification" and row[2] == year:
            row[4] = "Modify"
        else:
            row[4] = "Exist"
        rows.updateRow(row)
    if 'row' in locals():
        del row, rows
    # Dissolution of segments to obtain the whole new, old and existing segments
    dissolved_lines_single = arcpy.Dissolve_management(selected_lines, 'dissolved_lines',
                                    ['Name', 'Voltage', 'Start', 'End', 'Dissolution', 'Circuit'], "", "SINGLE_PART")
    # Buffering of the segments to identify branches and other complex edges as one object
    dissolved_buffer = arcpy.Buffer_analysis(dissolved_lines_single, "selected_buffer", "1 Meters", "FULL", "ROUND",
                                           "LIST", ['Name', 'Voltage', 'Start', 'End', 'Dissolution', 'Circuit'])
    dissolved_buffer_single = arcpy.MultipartToSinglepart_management(dissolved_buffer, "Dissolved_buffer_single")
    arcpy.AddField_management(dissolved_buffer_single, 'MULTIPART_ID', 'SHORT')
    arcpy.CalculateField_management(dissolved_buffer_single, 'MULTIPART_ID', '[OBJECTID]')
    dissolved_lines = arcpy.SpatialJoin_analysis(dissolved_lines_single, dissolved_buffer_single,
                                                 'modification_lines_{0}'.format(year), 'JOIN_ONE_TO_MANY',
                                                   field_mapping='{3} "{3}" true true false 4 Long 0 0 ,First,#,{0},{3}'
                                                                 ',-1,-1;{2} "{2}" true true false 255 Text 0 0 ,First,'
                                                                 '#,{0},{2},-1,-1;{4} "{4}" true true false 255 Text 0 '
                                                                 '0 ,First,#,{0},{4},-1,-1;{5} "{5}" true true false '
                                                                 '255 Text 0 0 ,First,#,{0},{5},-1,-1;{7} "{7}" true '
                                                                 'true false 4 Long 0 0 ,First,#,{0},{7},-1,-1;{6} "{6}'
                                                                 '" true true false 255 Text 0 0 ,First,#,{0},{6},-1,-1'
                                                                 ';{8} "{8}" false true true 8 Double 0 0 ,First,#,{0},'
                                                                 '{8},-1,-1;{9} "{9}" true true false 2 Short 0 0 ,'
                                                                 'First,#,{1},{9},-1,-1'.format(dissolved_lines_single,
                                                    dissolved_buffer_single, "Name", "Voltage", "Start", "End",
                                                                                                "Dissolution",
                                                                            "Circuit", "Shape_Length", "MULTIPART_ID"),
                                                   match_option="COMPLETELY_WITHIN")
    # layer with new segments
    new_lines_lyr = arcpy.MakeFeatureLayer_management(dissolved_lines, "new_lines", "Dissolution = 'New'".format(year))
    new_ends = arcpy.FeatureVerticesToPoints_management(new_lines_lyr, r'new_ends', 'BOTH_ENDS')
    dismantled_segments = arcpy.FeatureClassToFeatureClass_conversion(dissolved_lines, arcpy.env.workspace,
                                                                            'dismantled_segments'.format(year),
                                                                            "Dissolution = 'Old'")
    # Spatial join of dismantled segments with adjacent vertices of the new segments.
    spat_join_dismantled = arcpy.SpatialJoin_analysis(dismantled_segments, new_ends, 'spat_join_dismantled'.format(year),
                                           "JOIN_ONE_TO_MANY", match_option="INTERSECT")
    # Dissolution of doubled dismantled segments to obtain the names of the ends in new segment
    dissolved_spat_join = arcpy.Dissolve_management(spat_join_dismantled, r'dissolved_spat_join',
                                                    ['TARGET_FID', 'Name', 'Voltage', 'Start', 'End', 'Dissolution',
                                                        'MULTIPART_ID'], [['Start_1', 'FIRST'], ['Start_1', 'LAST'],
                                                                          ['End_1', 'FIRST'], ['End_1', 'LAST'],
                                                                          ['JOIN_FID', 'COUNT'], ['Circuit_1', 'FIRST'],
                                                                          ['Circuit_1', 'LAST']], "MULTI_PART")
    part_count_dict = {}  # Dictionary for calculating the number of parts in ex-multipart feature
    rows = arcpy.da.SearchCursor(dissolved_spat_join, ['MULTIPART_ID'])
    for row in rows:
        if row[0] not in part_count_dict:
            part_count_dict[row[0]] = 1
        else:
            part_count_dict[row[0]] = part_count_dict[row[0]] + 1
    if 'row' in locals():
        del row, rows
    # Adding field to calculate a number of unique end names
    arcpy.AddField_management(dissolved_spat_join, 'Ends_number', 'FLOAT')
    rows = arcpy.da.UpdateCursor(dissolved_spat_join, ['Start', 'End', 'FIRST_start_1', 'LAST_start_1',
                                                       'FIRST_end_1', 'LAST_end_1', 'Ends_number', 'COUNT_JOIN_FID',
                                                       'FIRST_Circuit_1', 'LAST_Circuit_1', 'MULTIPART_ID'])
    for row in rows:
        num_1 = len(list({row[0], row[1], row[2], row[4]}))
        num_2 = len(list({row[0], row[1], row[3], row[5]}))
        num_3 = len(list({row[2], row[3], row[4], row[5]}))
        num_4, num_5 = len(list({row[0], row[2], row[3]})), len(list({row[0], row[4], row[5]}))
        num_6, num_7 = len(list({row[1], row[2], row[3]})), len(list({row[1], row[4], row[5]}))
        if (num_1 == 3 or num_2 == 3) and num_3 != 2 and num_1 != 2 and num_2 != 2 and row[7] == 2 and min(num_4,num_5, num_6, num_7) != 1:
            row[6] = 3  # detection of cut
        elif num_1 + num_2 == 5:
            row[6] = 2.5
        elif (num_1 == num_2 == 2 and row[8] == row[9]) or (num_3 == 2 and row[7] == 2 and row[8] == row[9]):
            row[6] = 2  # detection of re-routing
        elif (num_1 == 3 or num_2 == 3) and num_3 == 2 and part_count_dict[row[10]] > 2:
            row[6] = 3  # detection of cut as a replacement of the branch
        else:
            row[6] = 1
        rows.updateRow(row)
    if 'row' in locals():
        del row, rows
    dismantled_lines_lyr = arcpy.MakeFeatureLayer_management(dissolved_spat_join, "dismantled")
    arcpy.AddField_management(dissolved_lines, 'Segment_Type', 'TEXT')
    selected_lines_lyr = arcpy.MakeFeatureLayer_management(dissolved_lines, "selected_lines")
    new_ends_lyr = arcpy.MakeFeatureLayer_management(new_ends, "new_ends_lyr")
    branch_points_lyr = arcpy.MakeFeatureLayer_management(branch_points, "branch_point_lyr",
                                                          "Year_start <= {0} AND (Year_end >= {0} OR Year_end IS NULL)".format(year))
    # Cut dismantling detection
    arcpy.SelectLayerByAttribute_management(dismantled_lines_lyr, "NEW_SELECTION", "Ends_number = 3")
    arcpy.SelectLayerByLocation_management(selected_lines_lyr, "ARE_IDENTICAL_TO", dismantled_lines_lyr)
    arcpy.CalculateField_management(selected_lines_lyr, 'Segment_Type', '"Cut dismantling"')
    # Re-routing dismantling detection
    arcpy.SelectLayerByAttribute_management(dismantled_lines_lyr, "NEW_SELECTION", "Ends_number = 2")
    arcpy.SelectLayerByLocation_management(selected_lines_lyr, "ARE_IDENTICAL_TO", dismantled_lines_lyr)
    arcpy.CalculateField_management(selected_lines_lyr, 'Segment_Type', '"Re-routing dismantling"')
    # Cut construction detection
    arcpy.SelectLayerByAttribute_management(dismantled_lines_lyr, "NEW_SELECTION", "Ends_number = 3")
    arcpy.SelectLayerByLocation_management(new_ends_lyr, "INTERSECT", dismantled_lines_lyr)
    arcpy.SelectLayerByLocation_management(new_lines_lyr, "INTERSECT", new_ends_lyr)
    arcpy.SelectLayerByLocation_management(new_ends_lyr, "INTERSECT", new_lines_lyr, "", "ADD_TO_SELECTION")
    arcpy.SelectLayerByLocation_management(new_lines_lyr, "INTERSECT", new_ends_lyr, "", "ADD_TO_SELECTION")
    arcpy.CalculateField_management(new_lines_lyr, 'Segment_Type', '"Cut construction"')
    # Re-routing construction detection
    arcpy.SelectLayerByAttribute_management(dismantled_lines_lyr, "NEW_SELECTION", "Ends_number = 2")
    arcpy.SelectLayerByLocation_management(new_ends_lyr, "INTERSECT", dismantled_lines_lyr)
    arcpy.SelectLayerByLocation_management(new_lines_lyr, "INTERSECT", new_ends_lyr)
    arcpy.SelectLayerByAttribute_management(new_lines_lyr, "SUBSET_SELECTION", "Segment_Type IS NULL")
    arcpy.CalculateField_management(new_lines_lyr, 'Segment_Type', '"Re-routing construction"')
    # New line construction detection
    arcpy.SelectLayerByAttribute_management(new_lines_lyr, "NEW_SELECTION",
                                            "Dissolution = 'New' AND Segment_Type IS NULL")
    arcpy.CalculateField_management(new_lines_lyr, 'Segment_Type', '"New line construction"')
    arcpy.SelectLayerByAttribute_management(new_lines_lyr, "CLEAR_SELECTION")
    # Line dismantling detection
    arcpy.SelectLayerByAttribute_management(selected_lines_lyr, "NEW_SELECTION",
                                            "Dissolution = 'Old' AND Segment_Type IS NULL")
    arcpy.CalculateField_management(selected_lines_lyr, 'Segment_Type', '"Line dismantling"')
    arcpy.SelectLayerByAttribute_management(dismantled_lines_lyr, "CLEAR_SELECTION")
    # Branch segment construction detection
    arcpy.SelectLayerByAttribute_management(branch_points_lyr, "NEW_SELECTION", "Year_start = {0}".format(year))
    id_list = [r[0] for r in arcpy.da.SearchCursor(branch_points_lyr, ['OBJECTID'])]
    for id in id_list:
        arcpy.SelectLayerByAttribute_management(branch_points_lyr, "NEW_SELECTION", "OBJECTID = {0}".format(id))
        arcpy.SelectLayerByLocation_management(new_lines_lyr, "INTERSECT", branch_points_lyr, "", "NEW_SELECTION")
        selection_layer = arcpy.MakeFeatureLayer_management(new_lines_lyr, 'Selection')
        shp_length = [r[0] for r in arcpy.da.SearchCursor(selection_layer, ['Shape_Length'])]
        if len(shp_length) == 3:
            expression = "Shape_Length < {0} AND Shape_Length > {1}".format(min(shp_length) + 1, min(shp_length) - 1)
            arcpy.SelectLayerByAttribute_management(selection_layer, "NEW_SELECTION", expression)
            arcpy.CalculateField_management(selection_layer, 'Segment_Type', '"Branch construction"')
        elif len(shp_length) == 4:
            expression = "Shape_Length < {0} AND Shape_Length > {1}".format(min(shp_length) + 1, min(shp_length) - 1)
            arcpy.SelectLayerByAttribute_management(selection_layer, "NEW_SELECTION", expression)
            shp_length.remove(min(shp_length))
            expression = "Shape_Length < {0} AND Shape_Length > {1}".format(min(shp_length) + 1, min(shp_length) - 1)
            arcpy.SelectLayerByAttribute_management(selection_layer, "ADD_TO_SELECTION", expression)
            arcpy.CalculateField_management(selection_layer, 'Segment_Type', '"Branch construction"')
        elif len(shp_length) == 1:
            arcpy.CalculateField_management(selection_layer, 'Segment_Type', '"Branch construction"')
    # Branch segment dismantling detection
    arcpy.SelectLayerByAttribute_management(branch_points_lyr, "NEW_SELECTION", "Year_end = {0}".format(year))
    end_branch_layer = arcpy.MakeFeatureLayer_management(branch_points_lyr, 'End_branch')
    id_list = [r[0] for r in arcpy.da.SearchCursor(end_branch_layer, ['OBJECTID'])]
    for id in id_list:
        arcpy.SelectLayerByLocation_management(selected_lines_lyr, "ARE_IDENTICAL_TO", dismantled_lines_lyr, "",
                                               "NEW_SELECTION")
        arcpy.SelectLayerByAttribute_management(end_branch_layer, "NEW_SELECTION", "OBJECTID = {0}".format(id))
        arcpy.SelectLayerByLocation_management(selected_lines_lyr, "INTERSECT", end_branch_layer, "", "SUBSET_SELECTION")
        selection_layer = arcpy.MakeFeatureLayer_management(selected_lines_lyr, 'Selection')
        shp_length = [r[0] for r in arcpy.da.SearchCursor(selection_layer, ['Shape_Length'])]
        if len(shp_length) == 3:
            expression = "Shape_Length < {0} AND Shape_Length > {1}".format(min(shp_length) + 1, min(shp_length) - 1)
            arcpy.SelectLayerByAttribute_management(selection_layer, "NEW_SELECTION", expression)
            arcpy.CalculateField_management(selection_layer, 'Segment_Type', '"Branch dismantling"')
        elif len(shp_length) == 4:
            expression = "Shape_Length < {0} AND Shape_Length > {1}".format(min(shp_length) + 1, min(shp_length) - 1)
            arcpy.SelectLayerByAttribute_management(selection_layer, "NEW_SELECTION", expression)
            shp_length.remove(min(shp_length))
            expression = "Shape_Length < {0} AND Shape_Length > {1}".format(min(shp_length) + 1, min(shp_length) - 1)
            arcpy.SelectLayerByAttribute_management(selection_layer, "ADD_TO_SELECTION", expression)
            arcpy.CalculateField_management(selection_layer, 'Segment_Type', '"Branch dismantling"')
        elif len(shp_length) in [1, 2]:
            arcpy.CalculateField_management(selection_layer, 'Segment_Type', '"Branch dismantling"')
    # Voltage modification detection
    arcpy.SelectLayerByAttribute_management(selected_lines_lyr, "NEW_SELECTION",
                                            "Dissolution = 'Modify'")
    arcpy.CalculateField_management(selected_lines_lyr, 'Segment_Type', '"Voltage modification"')
    arcpy.SelectLayerByAttribute_management(dismantled_lines_lyr, "CLEAR_SELECTION")


arcpy.env.workspace = r'F:\YandexDisk\Projects\MES_evolution\BackUp230109\MES_Evolution.gdb'
arcpy.env.overwriteOutput = True
initial_data = r'F:\YandexDisk\Projects\MES_evolution\BackUp230109\MES_Evolution.gdb'
out = r'F:\YandexDisk\Projects\MES_evolution\BackUp230109\MES_Queries.gdb'
modifications = r'F:\YandexDisk\Projects\MES_evolution\BackUp230109\MES_Modifications.gdb'
#relation_redundancy_decrease(r'F:\YandexDisk\Projects\MES_evolution\BackUp230109\MES_Evolution.gdb\PL', modifications)
arcpy.env.workspace = modifications
#voltage_modification("PL_Spat_Time", "PL_Attributes")
for i in range(1978, 2023):
    get_morphological_modifications(i, modifications, modifications)
    print(i)
