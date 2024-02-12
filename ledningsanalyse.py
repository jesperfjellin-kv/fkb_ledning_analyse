# -*- coding: windows-1252 -*-

from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union  # Include this line
import matplotlib.pyplot as plt
from descartes import PolygonPatch
import chardet
from shapely.geometry import MultiPolygon, Polygon

file1_path = 'C:\\Python\\SosiPythonLedning\\FKB.SOS'
file2_path = 'C:\\Python\\SosiPythonLedning\\Everk.SOS'

def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        return chardet.detect(file.read())['encoding']

file1_encoding = detect_encoding(file1_path)
file2_encoding = detect_encoding(file2_path)

print(f"Detected encoding for file 1: {file1_encoding}")
print(f"Detected encoding for file 2: {file2_encoding}")

def parse_sosi_geometry_2d_and_extent(file_path):
    geometries_with_attrs = []
    current_geom = []
    current_attrs = []
    geom_type = None
    reading_coordinates = False
    min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')

    def finalize_current_geometry():
        if not current_geom:
            return
        if geom_type == '.KURVE':
            geometry = LineString(current_geom)
        elif geom_type == '.PUNKT':
            geometry = Point(current_geom[0])
        elif geom_type == '.FLATE' and len(current_geom) >= 4:
            geometry = Polygon(current_geom)
        else:
            return  # Skip geometry if it doesn't meet requirements
        geometries_with_attrs.append((geometry, current_attrs.copy()))
        nonlocal min_x, min_y, max_x, max_y
        for x, y in current_geom:
            min_x, min_y, max_x, max_y = min(min_x, x), min(min_y, y), max(max_x, x), max(max_y, y)

    with open(file_path, 'r', encoding='utf-8-sig') as file:
        for line in file:
            stripped_line = line.strip()
            if stripped_line.startswith(('.KURVE', '.PUNKT', '.FLATE')):
                finalize_current_geometry()  # Finalize the previous geometry
                current_geom, current_attrs = [], [stripped_line]
                geom_type = stripped_line.split()[0]
                reading_coordinates = False
            elif stripped_line == '..N�HH':
                reading_coordinates = True
            elif reading_coordinates and stripped_line != '.SLUTT':
                try:
                    x, y = map(int, stripped_line.split()[:2])
                    current_geom.append((x, y))
                except ValueError:
                    pass
            else:
                if not reading_coordinates:
                    current_attrs.append(stripped_line)

    finalize_current_geometry()  # Finalize the last geometry

    extent = {'min_x': min_x, 'min_y': min_y, 'max_x': max_x, 'max_y': max_y}
    return geometries_with_attrs, extent

def visualize_geometries_with_buffers(geometries, buffer_distance):
    fig, ax = plt.subplots()
    for geom in geometries:
        # Ensure the geometry is valid before proceeding
        if not geom.is_valid:
            print("Invalid geometry, skipping...")
            continue

        # Generate the buffer
        buffer = geom.buffer(buffer_distance)

        # Check the buffer's type
        if isinstance(buffer, Polygon):
            print("Visualizing a Polygon buffer")
            patch = PolygonPatch(buffer, alpha=0.5, edgecolor='blue', facecolor='lightblue')
            ax.add_patch(patch)
        elif isinstance(buffer, MultiPolygon):
            print("Visualizing a MultiPolygon buffer")
            for part in buffer:
                patch = PolygonPatch(part, alpha=0.5, edgecolor='blue', facecolor='lightblue')
                ax.add_patch(patch)
        else:
            print(f"Unexpected buffer type: {type(buffer)}")

        # Visualize the original geometry
        x, y = geom.xy
        ax.plot(x, y, color='red', linewidth=2)

    ax.set_aspect('equal')
    plt.show()

def find_unique_geometries_everk(file1_geometries_with_attrs, file2_geometries_with_attrs, buffer_distance):
    # Buffer all geometries in file1 (FKB.SOS) for comparison
    buffered_geometries1 = [geom.buffer(buffer_distance) for geom, _ in file1_geometries_with_attrs]
    # Combine the buffered geometries in file1 to simplify overlap checking
    combined_buffered_geometries1 = unary_union(buffered_geometries1)

    unique_geometries_with_attrs_everk = []

    # Check each geometry in file2 (Everk.SOS) if it falls outside the combined buffer of file1
    for geom2, attrs2 in file2_geometries_with_attrs:
        if not geom2.intersects(combined_buffered_geometries1):
            unique_geometries_with_attrs_everk.append((geom2, attrs2))

    return unique_geometries_with_attrs_everk

# Assuming parse_sosi_geometry_2d_and_extent(file_path) returns a list of geometries for each file
file1_geometries, file1_extent = parse_sosi_geometry_2d_and_extent(file1_path)  # FKB.SOS
file2_geometries, file2_extent = parse_sosi_geometry_2d_and_extent(file2_path)  # Everk.SOS

combined_extent = {
    'min_x': min(file1_extent['min_x'], file2_extent['min_x']),
    'min_y': min(file1_extent['min_y'], file2_extent['min_y']),
    'max_x': max(file1_extent['max_x'], file2_extent['max_x']),
    'max_y': max(file1_extent['max_y'], file2_extent['max_y']),
}
def write_geometries_to_sosi(geometries_with_attrs, extent, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        # Header
        file.write(".HODE\n..TEGNSETT UTF-8\n..OMR�DE\n")
        file.write(f"...MIN-N�H  {int(extent['min_x'])}  {int(extent['min_y'])}\n")
        file.write(f"...MAX-N�H  {int(extent['max_x'])}  {int(extent['max_y'])}\n")
        file.write("..SOSI-VERSJON 5.0\n..SOSI-NIV� 3\n..TRANSPAR\n")
        file.write("...KOORDSYS 22\n...ORIGO-N�H 0  0\n...ENHET 0.000001\n...VERT-DATUM NN2000\n")
        file.write('..NGIS-ARKIV "Ledning_Norge"\n..OBJEKTKATALOG FKBLedning 5.0\n..PROSESS_HISTORIE "202402012 - Trans (Skt2lan1.dll 1.46): fra 23 til 22"\n')

        # Non-overlapping geometries
        for idx, (geom, attrs) in enumerate(geometries_with_attrs, start=1):
            for attr in attrs:  # Write attributes
                file.write(f'{attr}\n')
            file.write('..N�H\n')  # Start the coordinate list
            for coord in geom.coords:
                file.write(f'{int(coord[0])} {int(coord[1])}\n')
        
        file.write('.SLUTT\n')

buffer_distance = 10  # Adjust as needed

unique_everk_geometries = find_unique_geometries_everk(file1_geometries, file2_geometries, buffer_distance)

# Calculate the bounding box for the unique geometries
unique_everk_geometries_list = [geom for geom, attrs in unique_everk_geometries]
combined_unique_geometry = unary_union(unique_everk_geometries_list)
minx, miny, maxx, maxy = combined_unique_geometry.bounds
if not combined_unique_geometry.is_empty:
    minx, miny, maxx, maxy = combined_unique_geometry.bounds
    new_combined_extent = {
        'min_x': minx, 
        'min_y': miny, 
        'max_x': maxx, 
        'max_y': maxy
    }
else:
    print("No unique Everk geometries found outside the FKB buffer.")
    new_combined_extent = {
        'min_x': 0, 
        'min_y': 0, 
        'max_x': 0, 
        'max_y': 0
    }

output_sosi_path = 'C:\\Python\\SosiPythonLedning\\unique_everk_geometries.sos'

if not combined_unique_geometry.is_empty:
    write_geometries_to_sosi(unique_everk_geometries, new_combined_extent, output_sosi_path)
    print(f'Unique Everk.SOS geometries written to "{output_sosi_path}".')
else:
    print("Skipped writing the .SOS file due to no unique geometries found.")