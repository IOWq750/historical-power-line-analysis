import arcpy


def check_line_attributes():
    rows = arcpy.da.SearchCursor('PL', ['Name', 'Voltage', 'Start', 'End', 'IsBranch', 'Branch_points', 'fid'])
    for row in rows:
        if str(row[1]) not in row[0]:
            print('voltage error {1} {0}'.format(row[0], row[6]))
        if row[2] not in row[0]:
            print('Start not in name of {1} {0}'.format(row[0], row[6]))
        if row[3] not in row[0]:
            print('End not in name of {1} {0}'.format(row[0], row[6]))
        if row[4] == 'с отп.' and row[4] not in row[0]:
            print('Branch error {1} {0}'.format(row[0], row[6]))
        if row[4] is None and 'с отп.' in row[0]:
            print('Branch error {1} {0}'.format(row[0], row[6]))
        if row[4] == 'с отп.' and row[5] is None:
            print('Branch points error {1} {0}'.format(row[0], row[6]))
    del row, rows


def check_branch_points_attributes():
    rows = arcpy.da.SearchCursor('Branch_Point', ['Name', 'Start', 'End', 'Branch_End'])
    for row in rows:
        if row[1] not in row[0]:
            print('Start not in name of {0}'.format(row[0]))
        if row[2] not in row[0]:
            print('End not in name of {0}'.format(row[0]))
        if ', ' in row[3]:
            print('Branch point not specified in {0}'.format(row[0]))
    del row, rows


def unique_values(table, field):
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({row[0] for row in cursor if row[0] is not None})


def check_point_name_consistency():
    lines = arcpy.da.SearchCursor('PL', ['Name', 'Voltage', 'Start', 'End', 'IsBranch', 'Branch_points'])
    branches = arcpy.da.SearchCursor('Branch_Point', ['Name', 'Start', 'End', 'Branch_End'])
    point_names = unique_values('Merge_Substations_Generation', 'Name')
    for line in lines:
        if line[2] not in point_names and line[1] != 110:
            print('Start name is not in point list in {0}'.format(line[0]))
        if line[3] not in point_names and line[1] != 110:
            print('End name is not in point list in {0}'.format(line[0]))
    for branch in branches:
        if branch[1] not in point_names:
            print('Start name is not in point list in {0}'.format(branch[0]))
        if branch[2] not in point_names:
            print('End name is not in point list in {0}'.format(branch[0]))
        if branch[3] not in point_names:
            print('Branch end name is not in point list in {0}'.format(branch[0]))

folder = 'BackUp240624'
arcpy.env.workspace = r'D:\YandexDisk\Projects\MES_evolution\{0}\MES_Evolution.gdb'.format(folder)
arcpy.env.overwriteOutput = True

check_line_attributes()
check_branch_points_attributes()
check_point_name_consistency()
