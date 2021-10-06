# -*- coding: utf-8 -*-
import arcpy
import os
arcpy.env.workspace = r'F:\YandexDisk\Projects\MES_evolution\Queries.gdb'
arcpy.env.overwriteOutput = True
initial_data = r'F:\YandexDisk\Projects\MES_evolution\Moscow_MES_Evolution.gdb'


def get_year_state(year: int):
    """"Constructing a power lines state layer for the certain year"""
    lines = os.path.join(initial_data, 'PL')
    clause = "Year_start_name <= {0} AND (Year_end_name IS NULL OR Year_end_name > {0})".format(year)
    lines_year = arcpy.FeatureClassToFeatureClass_conversion(lines, arcpy.env.workspace, 'PL_{0}'.format(year), clause)
    arcpy.AddField_management(lines_year, 'Voltage_str', 'TEXT')
    arcpy.CalculateField_management(lines_year, "Voltage_str", '!Voltage!', "PYTHON_9.3")
    arcpy.Dissolve_management(lines_year, r'F:\YandexDisk\Projects\MES_evolution\SHP\{0}_lines.shp'.format(year),
                              ['Type', 'Name', 'Voltage_str'])


def get_modifications(year: int):
    """"Constructing a layer for power lines segment modifications for the certain year"""
    branch_points = os.path.join(initial_data, 'Branch_Point')
    lines = os.path.join(initial_data, 'PL')
    clause = "Year_start_name <= {0} AND (Year_end_name IS NULL OR Year_end_name > {0}) OR (Year_end = {0} AND " \
             "Year_end_name = {0})".format(year)
    selected_lines = arcpy.FeatureClassToFeatureClass_conversion(lines, arcpy.env.workspace,
                                                                'selected_lines_{0}'.format(year), clause)
    arcpy.AddField_management(selected_lines, 'Dissolution', 'TEXT')  # Field for segment classification
    rows = arcpy.da.UpdateCursor(selected_lines,
                                 ['Year_start', 'Year_end', 'Year_start_name', 'Year_end_name', 'Dissolution'])
    for row in rows:
        if row[0] == row[2] == year:
            row[4] = "New"
        elif row[1] == row[3] == year:
            row[4] = "Old"
        else:
            row[4] = "Exist"
        rows.updateRow(row)
    if 'row' in locals():
        del row, rows
    # Dissolution of segments to obtain the whole new, old, existing segments
    dissolved_lines_single = arcpy.Dissolve_management(selected_lines, 'dissolved_lines',
                                    ['Name', 'Voltage', 'Start', 'End', 'Dissolution', 'Circuit'], "", "SINGLE_PART")
    # Buffering of the segments to identify branches and other complex edges as one object
    dissolved_buffer = arcpy.Buffer_analysis(dissolved_lines_single, "selected_buffer", "1 Meters", "FULL", "ROUND",
                                           "LIST", ['Name', 'Voltage', 'Start', 'End', 'Dissolution', 'Circuit'])
    dissolved_buffer_single = arcpy.MultipartToSinglepart_management(dissolved_buffer, "Dissolved_buffer_single")
    arcpy.AddField_management(dissolved_buffer_single, 'MULTIPART_ID', 'SHORT')
    arcpy.CalculateField_management(dissolved_buffer_single, 'MULTIPART_ID', '[OBJECTID]')
    dissolved_lines = arcpy.SpatialJoin_analysis(dissolved_lines_single, dissolved_buffer_single,
                                                 'dissolved_lines_{0}'.format(year), 'JOIN_ONE_TO_MANY',
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


for i in range(1936, 2021):
    get_modifications(i)
    get_year_state(i)
    print(i)
