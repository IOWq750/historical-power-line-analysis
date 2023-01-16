import arcpy

lines = r'F:\YandexDisk\Projects\MES_evolution\test.shp'

new_coords = (424777.000, 6169619.000)
with arcpy.da.UpdateCursor(lines, ['SHAPE@']) as rows:
    for row in rows:
        geometry = row[0]
        v_array = arcpy.Array()
        if geometry.isMultipart is True:
            print('line consists of {0} parts'.format(geometry.partCount))
            for i in range(geometry.partCount):
                print('part {0}'.format(i))
                for v in geometry.getPart(i):
                    print(v)
                    print(geometry.firstPoint, 'first point')
                    print(v.X)
                    print(v.Y)
                    if v.X == geometry.firstPoint.X:
                        v.X, v.Y = new_coords
                    v_array.add(v)
            new_polyline_geometry = arcpy.Polyline(v_array)
            row[0] = new_polyline_geometry
            rows.updateRow(row)
        else:
            for v in geometry.getPart(0):
                print(v)

