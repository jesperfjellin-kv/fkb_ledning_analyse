import matplotlib.pyplot as plt
from shapely.geometry import Point

# Create a point and a buffer around it
point = Point(0, 0)
buffer = point.buffer(10)  # Create a buffer of 10 units

# Extract the exterior coordinates of the buffer
x, y = buffer.exterior.xy

# Plotting
plt.figure()
plt.fill(x, y, alpha=0.5, label='Buffer')
plt.plot(point.x, point.y, 'ro', label='Original Point')
plt.xlabel('X Coordinate')
plt.ylabel('Y Coordinate')
plt.title('Point and Its Buffer')
plt.legend()
plt.axis('equal')  # Ensures that distances in X and Y are represented equally
plt.show()
