import arcpy


def simplify_lines(line):
    with arcpy.da.UpdateCursor(line, ['SHAPE@']) as rows:
        for row in rows:
            polyline = row[0]
            new_parts = arcpy.Array()

            if polyline.isMultipart:
                for part in polyline:
                    if len(part) > 1:  # Убедимся, что есть хотя бы две вершины
                        simplified_part = arcpy.Array([part[0], part[-1]])
                        new_parts.add(simplified_part)
            else:
                part = polyline.getPart(0)
                if len(part) > 1:  # Аналогично, проверяем на количество вершин
                    simplified_part = arcpy.Array([part[0], part[-1]])
                    new_parts.add(simplified_part)

            # Создаем новую линию из упрощенных частей
            new_polyline = arcpy.Polyline(new_parts, polyline.spatialReference)
            row[0] = new_polyline
            rows.updateRow(row)

    del row, rows


# Вызов функции
for year in range(1933, 2023):
    fc = r'D:\YandexDisk\Projects\Networks\MES\Topologized\TL_{0}.shp'.format(year)
    print(year)
    simplify_lines(fc)
