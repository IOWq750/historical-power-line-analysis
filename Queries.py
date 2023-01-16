# -*- coding: utf-8 -*-
import arcpy
import os


def get_year_state_lines(lines, year, output_workspace):
    """"Constructing a power lines state layer for the certain year"""
    clause = "Year_start_name <= {0} AND (Year_end_name IS NULL OR Year_end_name > {0})".format(year)
    lines_year = arcpy.FeatureClassToFeatureClass_conversion(lines, output_workspace, 'PL', clause)
    arcpy.AddField_management(lines_year, 'Voltage_str', 'TEXT')
    arcpy.CalculateField_management(lines_year, "Voltage_str", '!Voltage!', "PYTHON_9.3")
    arcpy.Dissolve_management(lines_year, os.path.join(output_workspace, 'L_{0}'.format(year)),
                              ['Name', 'Start', 'End', 'Branch_points', 'Voltage_str'])


def get_year_state_points(points, year, output_workspace):
    clause = "Year_start <= {0} AND (Year_end IS NULL OR Year_end > {0})".format(year)
    arcpy.FeatureClassToFeatureClass_conversion(points, output_workspace, 'P_{0}'.format(year), clause)


arcpy.env.workspace = r'F:\YandexDisk\Projects\MES_evolution\BackUp230109\MES_Evolution.gdb'
arcpy.env.overwriteOutput = True
initial_data = r'F:\YandexDisk\Projects\MES_evolution\BackUp230109\MES_Evolution.gdb'
out = r'F:\YandexDisk\Projects\MES_evolution\BackUp230109\MES_Queries.gdb'
for i in range(1933, 2021):
    get_year_state_lines('PL', i, out)
    get_year_state_points('Merge_Substations_Generation', i, out)
    print(i)
