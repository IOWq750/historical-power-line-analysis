# -*- coding: utf-8 -*-
import arcpy
import networkx as nx
import os
import nx_multi_shp as nxm

def coordinates_replacement(geometry, part_number, old_coords, new_coords, vertices_array):
    for v in geometry.getPart(part_number):
        if (v.X, v.Y) == old_coords:
            v.X, v.Y = new_coords
        vertices_array.add(v)


def edit_geometry(line, point, end):
    for point in arcpy.da.SearchCursor(point, ['SHAPE@X', 'SHAPE@Y']):
        point_coords = point[0], point[1]
    for point in arcpy.da.SearchCursor(end, ['SHAPE@X', 'SHAPE@Y']):
        end_coords = point[0], point[1]
    with arcpy.da.UpdateCursor(line, ['SHAPE@']) as rows:
        for row in rows:
            polyline = row[0]
            v_array = arcpy.Array()
            if polyline.isMultipart is True:
                for part in range(polyline.partCount):
                    v_array_part = arcpy.Array()
                    coordinates_replacement(polyline, part, end_coords, point_coords, v_array_part)
                    v_array.add(v_array_part)
            else:
                coordinates_replacement(polyline, 0, end_coords, point_coords, v_array)
            new_polyline = arcpy.Polyline(v_array)
            row[0] = new_polyline
            rows.updateRow(row)
    del row, rows


# Creation of a list with unique values in attribute field
def unique_values(table, field):
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({row[0] for row in cursor if row[0] is not None})


# Creating dictionary of names and alternative names for future selection
def create_name_dict(line_class, point_class, exclusion_dict):
    lines = arcpy.da.SearchCursor(line_class, ["OBJECTID", "Name", "Start", "End", "Branch_points", "Voltage_str"])
    alt_name_dict = {}
    unique_alt_names = unique_values(point_class, 'Alternative_name')
    for p in arcpy.da.SearchCursor(point_class, ["Name", "Alternative_name", "Type"]):
        if p[1] is not None and p[2] == 'РУ':
            alt_name_dict[p[0]] = p[1]
        elif p[0] not in unique_alt_names:
            alt_name_dict[p[0]] = p[0]
    # For 110 PL it could be no appropriate points in feature class, so we should add names in dictionary from PL attributes
    for line in lines:
        if line[5] == '110':
            if line[4] is not None:
                name_list = line[4].split(r', ')
                name_list.append(line[2])
                name_list.append(line[3])
            else:
                name_list = [line[2], line[3]]
            for name in name_list:
                if name not in alt_name_dict:
                    alt_name_dict[name] = name
    for element in alt_name_dict:
        if element in exclusion_dict:
            alt_name_dict[element] = element
    # print(alt_name_dict)
    return alt_name_dict


def selecting_dangles(point_layer, oid, dangle_selection, snap_radius, point_name):
    point_selected = arcpy.SelectLayerByAttribute_management(point_layer, "NEW_SELECTION",
                                                             "OBJECTID = {0}".format(oid))
    dangle_snap_selection = arcpy.SelectLayerByLocation_management(dangle_selection, "WITHIN_A_DISTANCE",
                                                                   select_features=point_selected,
                                                                   search_distance="{0} Meters".format(
                                                                       snap_radius),
                                                                   selection_type="NEW_SELECTION")
    #print(point_name)
    # Selection of the dangle point with the corresponding start, end or branch end
    expression = "Start = '{0}' OR End = '{0}' OR Branch_points LIKE '%{0}%'".format(point_name)
    #print(expression)
    dangle_name_selection = arcpy.SelectLayerByAttribute_management(dangle_snap_selection, "SUBSET_SELECTION",
                                                                    expression)
    return point_selected, dangle_name_selection


# Selecting appropriate points for each dangle using dictionary of names and attribute fields in dangles
def selecting_points(KVL_dissolve, input_points_p, snap_radius, year):
    """ Snaps power lines to the substations and power plants according to their remoteness and names

        Parameters
        ----------
        KVL_dissolve: feature class
            Dissolved lines

        input_points_p: feature class
           point feature class with electrical substations and power plants

        snap_radius: float
            radius of snapping in meters

        Returns
        -------
        None

        Examples
        --------

        """
    dangle_points = arcpy.FeatureVerticesToPoints_management(KVL_dissolve, 'Dangles', 'DANGLE')
    lines_search = arcpy.da.SearchCursor(KVL_dissolve, ["OBJECTID", "Name", "Start", "End", "Branch_points", "Voltage_str"])
    alt_name_dict = create_name_dict(KVL_dissolve, input_points_p, exclusion_dict)
    for line in lines_search:
        #print(line[1])
        line_layer = arcpy.MakeFeatureLayer_management(KVL_dissolve, "Selected_line_{0}".format(year),
                                                       where_clause="OBJECTID = {0}".format(line[0]))
        if line[4] is not None:
            branch_name_list = [n for n in line[4].split(r', ')]
            point_name_list = branch_name_list + [line[2], line[3]]
        else:
            point_name_list = [line[2], line[3]]
        alt_name_list = []
        for name in point_name_list:
            keys = [i for i in alt_name_dict if alt_name_dict[i] == name]
            for key in keys:
                alt_name_list.append(key)
        # Selection of points, that potentially corresponds to the ends of the line
        point_layer = arcpy.MakeFeatureLayer_management(input_points_p, "Selected_point_{0}".format(year), "Name IN ({0})"
                                                        .format(", ".join(["'"'{0}'"'".format(n) for n in alt_name_list])))
        dangle_selection = arcpy.MakeFeatureLayer_management(dangle_points, "Selected_dangles_{0}".format(year),
                                                             "Name = '{0}'".format(line[1]))
        counter = snapping_dangles(point_layer, dangle_selection, snap_radius, alt_name_dict, line_layer)
        ends_amount = len(point_name_list)
        if counter < ends_amount and line[5] != '110':
            print("{0} dangle(s) is(are) not snapped in line {1} in {2}".format(ends_amount - counter, line[1], year))


# Snapping selected feature layers of dangles to the selected points
def snapping_dangles(point_layer, dangle_selection, snap_radius, alt_name_dict, line_layer):
        counter = 0
        for point in arcpy.da.SearchCursor(point_layer, ["OBJECTID", "Name", "Alternative_name", "Type"]):
            point_selected, dangle_name_selection = selecting_dangles(point_layer, point[0], dangle_selection, snap_radius,
                                                      alt_name_dict[point[1]])
            if int(str(arcpy.GetCount_management(dangle_name_selection))) == 1:
                # Dangle corresponds to the point
                point_selected = arcpy.SelectLayerByAttribute_management(point_layer, "NEW_SELECTION",
                                                                               "OBJECTID = {0}".format(point[0]))
                edit_geometry(line_layer, point_selected, dangle_name_selection)
                counter += 1
            elif int(str(arcpy.GetCount_management(dangle_name_selection))) > 1:
                # If there are several options for snapping within the radius with the same name
                near = arcpy.GenerateNearTable_analysis(point_selected, dangle_name_selection, "near",
                                                            '{0} Meters'.format(snap_radius))
                min_dist = min([i[0] for i in arcpy.da.SearchCursor(near, ['NEAR_DIST'])])
                for row in arcpy.da.SearchCursor(near, ['NEAR_FID', 'NEAR_DIST']):
                    if row[1] == min_dist:
                        one_dangle_selection = arcpy.SelectLayerByAttribute_management(dangle_name_selection,
                                                                                           "SUBSET_SELECTION",
                                                                                           "OBJECTID= {0}".format(row[0]))
                        edit_geometry(line_layer, point_selected, one_dangle_selection)
                        counter += 1
        return counter


# Deleting loops
def delete_loops(lines, year):
    ids_count = 100  # initial counter value (random positive) for while loop
    while ids_count > 0:
        singleparts = arcpy.MultipartToSinglepart_management(lines, "Lines_singlepart")
        ends = arcpy.FeatureVerticesToPoints_management(singleparts, 'Ends', 'BOTH_ENDS')
        identical = arcpy.FindIdentical_management(ends, "Ends_FindIdentical", "Shape;ORIG_FID")
        arcpy.JoinField_management(ends, "OBJECTID", identical, "IN_FID", fields="FEAT_SEQ")
        dissolved_ends = arcpy.Dissolve_management(ends, 'Ends_Dissolve', ['ORIG_FID', 'FEAT_SEQ'], 'FEAT_SEQ COUNT', 'SINGLE_PART')
        ids = [end[0] for end in arcpy.da.SearchCursor(dissolved_ends, ['ORIG_FID', 'COUNT_FEAT_SEQ']) if end[1] > 1]
        ids_count = len(ids)
        if ids_count != 0:
            singleparts_lyr = arcpy.MakeFeatureLayer_management(singleparts, "Selected_singleparts",
                                                                 "OBJECTID IN ({0})".format(", ".join(
                                                                                   ["{0}".format(n) for n in ids])))
            arcpy.DeleteFeatures_management(singleparts_lyr)
            lines = arcpy.Dissolve_management(singleparts, 'T{0}_lines'.format(year),
                                      ['Name', 'Start', 'End', 'Branch_points', 'Voltage_str'])
            print("Loops {0} are removed".format(ids))
        else:
            break


# Deleting artifact dangles
def delete_dangles(lines, points, year):
    dangle_points = arcpy.FeatureVerticesToPoints_management(lines, 'Dangles2', 'DANGLE')
    lines_singlepart = arcpy.MultipartToSinglepart_management(lines, "Lines_singlepart")
    lines_lyr = arcpy.MakeFeatureLayer_management(lines_singlepart, "Lines")
    erased_dangles = arcpy.Erase_analysis(dangle_points, points, 'Erased_dangles')
    erased_dangles_lyr = arcpy.MakeFeatureLayer_management(erased_dangles, "Erased_Dangles")
    selected_artifact_dangles = arcpy.SelectLayerByLocation_management(lines_lyr, "INTERSECT", select_features=erased_dangles_lyr)
    selected_lines = arcpy.SelectLayerByAttribute_management(selected_artifact_dangles, "SWITCH_SELECTION")
    arcpy.Dissolve_management(selected_lines, 'T{0}_lines'.format(year),
                              ['Name', 'Start', 'End', 'Branch_points', 'Voltage_str'])
    #arcpy.AddMessage("Artifact dangles for {0} year are removed".format(year))


def set_edge_weight(KVL_Dissolve):
    arcpy.AddField_management(KVL_Dissolve, "Weight", "FLOAT")
    dictionary = {u"35": 0.07,
                  u"110": 0.02,
                  u"150": 0.01,
                  u"220": 0.005,
                  u"330": 0.0025,
                  u"400": 0.001428571,
                  u"500": 0.001111111,
                  u"750": 0.000454545,
                  u"800": 0.000004545,
                  None: None}
    rows = arcpy.da.UpdateCursor(KVL_Dissolve, ["Voltage_str", "Weight"])
    for row in rows:
        row[1] = dictionary[row[0]]
        rows.updateRow(row)
    del row, rows


def del_empty_name_feature(KVL_Dissolve):
    rows = arcpy.da.UpdateCursor(KVL_Dissolve, ['Name'])
    for row in rows:
        if row[0] == "" or row[0] is None:
            rows.deleteRow()
    del rows, row


folder = 'BackUp241106'
arcpy.env.workspace = r'D:\YandexDisk\Projects\MES_evolution\{0}\MES_Queries.gdb'.format(folder)
arcpy.env.overwriteOutput = True
# Exclusions for distribution devices of some generation points which are represented as substations
exclusion_dict = {'Курчатовская': 'Курчатовская',
                  'Копорская': 'Копорская'}

for i in range(1933, 2023):
    print(i)
    lines = 'L_{0}'.format(i)
    points = 'P_{0}'.format( i)
    selecting_points(lines, points, 2000, i)
    delete_dangles(lines, points, i)
    delete_loops(lines, i)
    set_edge_weight(lines)
    del_empty_name_feature(lines)
    arcpy.FeatureClassToFeatureClass_conversion(lines,
                                                r'D:\YandexDisk\Projects\MES_evolution\{0}\SHP'.format(folder), 'TL_{0}.shp'.format(i))
    os.chdir(r'D:\YandexDisk\Projects\MES_evolution\{0}\SHP'.format(folder))
    G = nxm.read_shp('TL_{0}.shp'.format(i), 'Name').to_undirected()
    components = nx.connected_components(G)
    subgraphs = [G.subgraph(c).copy() for c in nx.connected_components(G)]
    j = 0
    for subgraph in subgraphs:
        os.makedirs("{0}_{1}".format(i, j), mode=0o777, exist_ok=True)
        nxm.write_shp(subgraph, "Name", "{0}_{1}".format(i, j))
        j =+ 1
    print('network in {0} has {1} connected components'.format(i, nx.number_connected_components(G)))


