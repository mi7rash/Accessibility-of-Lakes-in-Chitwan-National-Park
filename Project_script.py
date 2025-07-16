
#Import the required modules
import os
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import folium
import matplotlib.patches as mpatches

# please ensure from Tools >> Preferences >> working directory >> (Set the working directory to the folder where this script is located.)
#It is crucial to set the directory beforerunning as it was changing frequently. Please make sure of it.
try:
    from spyder_kernels.utils import path as spy_path
    active_script = spy_path.get_active_script_filename()
    script_dir = os.path.dirname(active_script)
    print(f"Detected Spyder script path: {active_script}")
except (ImportError, AttributeError):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"Detected __file__: {__file__}")
    except NameError:
        script_dir = os.getcwd()
        print("No __file__; using cwd.")

print(f"Final script_dir: {script_dir}")

data_dir = os.path.join(script_dir, 'Data')
print(f"Data directory: {data_dir}")


#Read the shapefiles
shapefiles = {
    "boundary": os.path.join(data_dir, 'Chitwan_National_Park.shp'),
    "lakes": os.path.join(data_dir, 'Lakes_CNP.shp'),
    "roads": os.path.join(data_dir, 'CNP_Road.shp'),
    "trails": os.path.join(data_dir, 'Trail.shp'),
    "buffer": os.path.join(data_dir, 'CNP_Buffer_Zone.shp'),
}

#Please make sure to select the "C:\Paudel" or whichever you set as the path from top-right corner before running this specific code. It is changing the directory all the time as well.
data = {key: gpd.read_file(path) for key, path in shapefiles.items()}

#plot the data to get a raw map including all the data sets
fig, ax = plt.subplots(figsize=(12, 8))
data['boundary'].plot(ax=ax, edgecolor='black', facecolor='none', linewidth=1)
data['buffer'].plot(ax=ax, edgecolor='green', facecolor='none', linewidth=1)
data['roads'].plot(ax=ax, color='red', linewidth=1)
data['trails'].plot(ax=ax, color='orange', linewidth=1)
data['lakes'].plot(ax=ax, color='blue')

#Add legend to the map
legend_patches = [
    mpatches.Patch(edgecolor='black', facecolor='none', label='Park Boundary'),
    mpatches.Patch(edgecolor='green', facecolor='none', label='Buffer Zone'),
    mpatches.Patch(color='red', label='Roads'),
    mpatches.Patch(color='orange', label='Trails'),
    mpatches.Patch(color='blue', label='Lakes')
]

ax.legend(handles=legend_patches, loc='upper right')
ax.set_title('Map of Chitwan National Park with lakes')
ax.axis('off')

# Save the map
output_path = os.path.join(script_dir, 'result', 'Raw_map.png')
plt.savefig(output_path, dpi=300, bbox_inches='tight')
plt.show()

print(f"Static map saved to: {output_path}")


# Reprojecting CRS to (WGS84), ((EPSG=32644)
roads_RE = data['roads'].to_crs(epsg=32644)
lakes_RE = data['lakes'].to_crs(epsg=32644)
boundary_RE = data['boundary'].to_crs(epsg=32644)
trails_RE = data['trails'].to_crs(epsg=32644)
buffer_RE = data['buffer'].to_crs(epsg=32644)

# Ensure if the CRS matches with a created dictionary of reprojected layers
reprojected_data = {
    "roads": roads_RE,
    "lakes": lakes_RE,
    "boundary": boundary_RE,
    "trails": trails_RE,
    "buffer": buffer_RE,
}

# Read the new CRS from reprojected layers
crs_set = {layer.crs for layer in reprojected_data.values()}

# Check if all reprojected layers have the same CRS
assert len(crs_set) == 1, f"CRS mismatch after reprojection! Found: {crs_set}"

print("Unique CRS after reprojection:", crs_set.pop())


# Create 1 km buffer (1000 meters)
roads_buffer = roads_RE.copy()
roads_buffer['geometry'] = roads_buffer.buffer(1000)  


# Create 1 km buffer (1000 meters)
trails_buffer = trails_RE.copy()
trails_buffer['geometry'] = trails_buffer.buffer(1000)

#Combine buffers
combined_buffers = gpd.overlay(roads_buffer, trails_buffer, how='union', keep_geom_type=False)
ax = combined_buffers.plot(facecolor='lightgray', edgecolor='red')

#plot the combined buffers
fig, ax = plt.subplots(figsize=(12, 8))
combined_buffers.plot(ax=ax, color='lightgray', edgecolor='red')  
ax.set_title('Combined Buffers')
ax.axis('off')

output_path = os.path.join(script_dir, 'result', 'combined buffer.png')
plt.savefig(output_path, dpi=300, bbox_inches='tight')
plt.show()

print(f"combined buffer saved to: {output_path}")


# Find accessible lakes that intersects to the buffers of road and trail
accessible_lakes = gpd.sjoin(lakes_RE, combined_buffers, predicate='intersects', how='inner')
ax = accessible_lakes.plot(facecolor='blue', edgecolor='blue')
ax.set_title('Accessible lakes')
plt.show()

#Count total number of lakes within the park
total_lakes = lakes_RE["geometry"].nunique()
print(f"Total number of unique lakes in the dataset: {total_lakes}")

#count the number of lakes touching the road and trails
num_lakes_touching = accessible_lakes["geometry"].nunique()
print(f"\nNumber of unique lakes that intersect the 1000m combined buffer: {num_lakes_touching}")


#Create the static map

fig, ax = plt.subplots(figsize=(12, 6))
boundary_RE.plot(ax=ax, edgecolor='black', facecolor='none', linewidth=1)
buffer_RE.plot(ax=ax, edgecolor='green', facecolor='none', linewidth=1)
combined_buffers.plot(ax=ax, edgecolor='red', facecolor='lightgray', alpha=0.3)
accessible_lakes.plot(ax=ax, color='blue')

legend_patches = [
    mpatches.Patch(edgecolor='black', facecolor='none', label='Park Boundary'),
    mpatches.Patch(edgecolor='green', facecolor='none', label='Buffer Zone'),
    mpatches.Patch(edgecolor='red', facecolor='lightgray', alpha=0.3, label='Road/Trail Buffer'),
    mpatches.Patch(color='blue', label='Accessible Lakes')
]

ax.legend(handles=legend_patches, loc='upper right')
plt.title('Accessibility of Lakes in Chitwan National Park')
plt.savefig(os.path.join(script_dir, 'result','static_map.png'))
plt.show()



#Create the interactive map

map = folium.Map(location=[27.6, 84.4], zoom_start=11, tiles='cartodbpositron', control_scale=True)

# Add park boundary
folium.GeoJson(
    boundary_RE,
    name='Park Boundary',
    style_function=lambda x: {'color': 'black', 'weight': 2, 'fillOpacity': 0}
).add_to(map)

# Add the buffer zone
folium.GeoJson(
    buffer_RE,
    name='Buffer Zone',
    style_function=lambda x: {'color': 'green', 'weight': 2, 'fillOpacity': 0}
).add_to(map)

# Add combined road/trail buffer
folium.GeoJson(
    combined_buffers,
    name='Road/Trail Buffer',
    style_function=lambda x: {'color': 'red', 'weight': 1, 'fillOpacity': 0.2}
).add_to(map)

# Add accessible lakes
folium.GeoJson(
    accessible_lakes,
    name='Accessible Lakes',
    style_function=lambda x: {'color': 'blue', 'weight': 1, 'fillOpacity': 0.5}
).add_to(map)

# Add layer control
folium.LayerControl().add_to(map)

# Toggleable legend with a button
legend_html = '''
<div id="legendBox" style="
    position: fixed; bottom: 40px; left: 20px; z-index:9999;
    background-color: white; border:2px solid grey; padding: 10px; display: none;">
    <b>Legend</b><br>
    <i style="background:gray; width:10px; height:10px; border-radius:50%; display:inline-block"></i> All Stops<br>
    <i style="background:red; width:10px; height:10px; border-radius:50%; display:inline-block"></i> No Healthcare (1km)<br>
    <i style="background:green; width:10px; height:10px; border-radius:50%; display:inline-block"></i> Healthcare POIs
</div>
<button onclick="var x = document.getElementById('legendBox'); 
                 x.style.display = (x.style.display === 'none') ? 'block' : 'none';"
        style="position: fixed; bottom: 10px; left: 20px; z-index:9999;
               background-color: white; border: 1px solid #ccc; padding: 5px;">
    Toggle Legend
</button>
'''

# Save interactive map
interactive_map_path = os.path.join(script_dir, 'result', 'interactive_map.html')
map.save(interactive_map_path)

print(f"Interactive map saved to: {interactive_map_path}")



