# -*- coding: windows-1252 -*-

from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union  # Include this line
import matplotlib.pyplot as plt
from descartes import PolygonPatch
import chardet
from shapely.geometry import MultiPolygon, Polygon

file1_path = 'C:\\Python\\SosiPythonLedning\\Liten_FKB.SOS'
file2_path = 'C:\\Python\\SosiPythonLedning\\Liten_Everk.SOS'

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
            elif stripped_line == '..NØH':
                reading_coordinates = True
            elif reading_coordinates and stripped_line != '.SLUTT':
                try:
                    x, y = map(int, stripped_line.split()[:2])
                    current_geom.append((x, y))
                except ValueError:
                    print(f"Error parsing coordinates: {stripped_line}")
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

def find_non_overlapping_geometries(file1_geometries_with_attrs, file2_geometries, buffer_distance):
    non_overlapping_geometries_with_attrs = []

    # Buffer all geometries in file2 for more efficient comparison
    buffered_geometries2 = [geom.buffer(buffer_distance) for geom, _ in file2_geometries]
    # Combine the buffered geometries in file2 to simplify overlap checking
    combined_geometries2 = unary_union(buffered_geometries2)

    for geom1, attrs1 in file1_geometries_with_attrs:
        # Buffer the current geometry from file1
        buffered_geom1 = geom1.buffer(buffer_distance)
        # Check if buffered_geom1 overlaps with any geometry in combined_geometries2
        if not buffered_geom1.intersects(combined_geometries2):
            non_overlapping_geometries_with_attrs.append((geom1, attrs1))

    return non_overlapping_geometries_with_attrs

# Assuming parse_sosi_geometry_2d_and_extent(file_path) returns a list of geometries for each file
file1_geometries = parse_sosi_geometry_2d_and_extent(file1_path)
file2_geometries = parse_sosi_geometry_2d_and_extent(file2_path)

file1_geometries, file1_extent = parse_sosi_geometry_2d_and_extent(file1_path)
file2_geometries, file2_extent = parse_sosi_geometry_2d_and_extent(file2_path)

combined_extent = {
    'min_x': min(file1_extent['min_x'], file2_extent['min_x']),
    'min_y': min(file1_extent['min_y'], file2_extent['min_y']),
    'max_x': max(file1_extent['max_x'], file2_extent['max_x']),
    'max_y': max(file1_extent['max_y'], file2_extent['max_y']),
}
def write_geometries_to_sosi(geometries_with_attrs, extent, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        # Header
        file.write(".HODE\n..TEGNSETT UTF-8\n..OMRÅDE\n")
        file.write(f"...MIN-NØ  {int(extent['min_x'])}  {int(extent['min_y'])}\n")
        file.write(f"...MAX-NØ  {int(extent['max_x'])}  {int(extent['max_y'])}\n")
        file.write("..SOSI-VERSJON 5.0\n..SOSI-NIVÅ 3\n..TRANSPAR\n")
        file.write("...KOORDSYS 22\n...ORIGO-NØ 0  0\n...ENHET 0.000001\n...VERT-DATUM NN2000\n")
        file.write('..NGIS-ARKIV "Ledning_Norge"\n..OBJEKTKATALOG FKBLedning 5.0\n..PROSESS_HISTORIE "202402012 - Trans (Skt2lan1.dll 1.46): fra 23 til 22"\n')

        # Non-overlapping geometries
        for idx, (geom, attrs) in enumerate(geometries_with_attrs, start=1):
            for attr in attrs:  # Write attributes
                file.write(f'{attr}\n')
            file.write('..NØH\n')  # Start the coordinate list
            for coord in geom.coords:
                file.write(f'{int(coord[0])} {int(coord[1])}\n')
        
        file.write('.SLUTT\n')

# Specify the buffer distance for comparison
buffer_distance = 10  # Adjust as needed
non_overlapping = find_non_overlapping_geometries(file1_geometries, file2_geometries, buffer_distance)
print(f'Found {len(non_overlapping)} non-overlapping geometries.')

# Define the path for the new .SOSI file that will contain the non-overlapping geometries
output_sosi_path = 'C:\\Python\\SosiPythonLedning\\non-overlapping_geometries.sos'

# Find non-overlapping geometries based on the buffer distance
non_overlapping = find_non_overlapping_geometries(file1_geometries, file2_geometries, buffer_distance)

# Write the non-overlapping geometries to the new .SOSI file
write_geometries_to_sosi(non_overlapping, combined_extent, output_sosi_path)

print(f'Non-overlapping geometries written to "{output_sosi_path}".')
