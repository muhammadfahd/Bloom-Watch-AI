


import streamlit as st
import ee
import geemap.foliumap as geemap
import pandas as pd
import numpy as np 
import folium.plugins

# ------------------ Earth Engine Authentication ------------------
try:
    ee.Initialize(project='bloomwatch-474212')
except Exception as e:
    # NOTE: In a hackathon setting, this often requires manual steps 
    # and might need to be run outside the app first.
    # We assume ee.Initialize() succeeds here for the app to run.
    ee.Authenticate()
    ee.Initialize(project='bloomwatch-474212')

# ------------------ App Configuration ------------------
st.set_page_config(page_title="BloomWatch AI", layout="wide", page_icon="🌸")

# ------------------ App Header ------------------
st.title("🌸 BloomWatch AI — Global Flowering Tracker")
st.markdown(
    """
    **BloomWatch AI** is your window into Earth's greenness 🌍. 
    It uses **NASA’s MODIS NDVI (Normalized Difference Vegetation Index)** data via 
    **Google Earth Engine (GEE)** to help visualize vegetation health, bloom patterns, 
    and seasonal changes across the globe.
    """
)

# ------------------ Sidebar Navigation ------------------
st.sidebar.title("📍 Navigation")
menu = st.sidebar.radio("Choose a section:", ["🏠 Home", "🧭 Explore", "ℹ️ About"])

# ------------------ HELPER FUNCTION FOR GEE PROCESSING ------------------

@st.cache_resource
def get_index_image(year, month_index_1_based, selected_index):
    """Fetches and computes the mean index image for a given month/year."""
    # Define start and end dates
    start_date_ee = ee.Date.fromYMD(int(year), month_index_1_based, 1)
    end_date_ee = start_date_ee.advance(1, 'month') 

    # Select the dataset and filter by date
    dataset = ee.ImageCollection('MODIS/061/MOD13Q1').select(selected_index)
    filtered_collection = dataset.filterDate(start_date_ee, end_date_ee)

    if filtered_collection.size().getInfo() == 0:
        return None
    
    # Compute the mean over the time period
    return filtered_collection.mean()

# @st.cache_data
# def get_time_series_data(year_range, month_index_1_based, selected_index, region_geometry, scale=250):
#     """Calculates the mean index value for a region across a range of years."""
#     data = []
    
#     if region_geometry is None:
#         return pd.DataFrame() 
        
#     for year in year_range:
#         image = get_index_image(year, month_index_1_based, selected_index)
        
#         if image:
#             clipped_image = image.clip(region_geometry)
            
#             mean_dict = clipped_image.reduceRegion(
#                 reducer=ee.Reducer.mean(),
#                 geometry=region_geometry,
#                 scale=scale,
#                 maxPixels=1e9
#             )
            
#             mean_value = mean_dict.get(selected_index).getInfo()
            
#             if mean_value is not None:
#                 data.append({
#                     'Year': year, 
#                     f'Avg {selected_index}': mean_value / 10000.0 
#                 })
#             else:
#                 data.append({'Year': year, f'Avg {selected_index}': np.nan}) 
#         else:
#             data.append({'Year': year, f'Avg {selected_index}': np.nan}) 

#     df = pd.DataFrame(data).set_index('Year')
#     return df

@st.cache_data
def get_time_series_data(year_range, month_index_1_based, selected_index, _region_geometry, scale=250):
    """Calculates the mean index value for a region across a range of years."""
    data = []
    
    # Check for a valid geometry (using the ignored variable name)
    if _region_geometry is None or _region_geometry == ee.Geometry.BBox(-180, -90, 180, 90):
        # Added check for global bounds as well, since that's a fallback geometry
        return pd.DataFrame() 
        
    for year in year_range:
        image = get_index_image(year, month_index_1_based, selected_index)
        
        if image:
            # Clip the image to the region before calculating the mean
            clipped_image = image.clip(_region_geometry)
            
            # Calculate the mean value for the region
            mean_dict = clipped_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=_region_geometry, # Use the ignored variable here
                scale=scale,
                maxPixels=1e9
            )
            
            mean_value = mean_dict.get(selected_index).getInfo()
            
            if mean_value is not None:
                data.append({
                    'Year': year, 
                    f'Avg {selected_index}': mean_value / 10000.0 
                })
            else:
                data.append({'Year': year, f'Avg {selected_index}': np.nan}) 
        else:
            data.append({'Year': year, f'Avg {selected_index}': np.nan}) 

    df = pd.DataFrame(data).set_index('Year')
    return df

# ------------------ HOME PAGE ------------------
if menu == "🏠 Home":
    st.header("🌿 Welcome to BloomWatch AI")
    st.markdown(
        """
        This platform helps you explore **how green our planet is** using real satellite data.

        ### 💡 What You Can Do:
        - View **NDVI maps** for any month and year 
        - **Compare** current vegetation to historical averages (Anomaly Detection)
        - View **time-series charts** of average vegetation index over multiple years
        - Focus on specific regions or countries, or **draw your own area of interest** ✏️ **<-- NEW!**
        - Adjust color palettes to visualize vegetation more clearly 
        - Track changes in greenness over time 
        """
    )
    st.markdown("---")
    st.markdown("""
        🛰️ **NDVI (Normalized Difference Vegetation Index)** is a key indicator for vegetation health. 
        Values close to `1.0` mean dense green vegetation, while values near `0.0` or negative indicate barren land or water.
    """)

# ------------------ EXPLORE PAGE ------------------
elif menu == "🧭 Explore":
    st.sidebar.header("🧭 Filters")

    # --- Region selection (Unchanged) ---
    st.markdown("### 🌍 Explore Global Vegetation")
    st.markdown(
        "Select a region and time period to visualize **vegetation bloom intensity** from satellite data."
    )

    region_option = st.sidebar.radio("Select Region Input Method", ["🌍 Choose from List", "✏️ Enter Manually"])

    if region_option == "🌍 Choose from List":
        region = st.sidebar.selectbox(
            "Select Region",
            ["Pakistan", "India", "United States", "China", "Brazil", "Australia", "Canada",
             "United Kingdom", "South Africa", "Indonesia", "Saudi Arabia", "Argentina"]
        )
    else:
        region = st.sidebar.text_input("Enter Custom Region", "Pakistan")

    # --- Date filters ---
    month_list = ["January","February","March","April","May","June",
                  "July","August","September","October","November","December"]
    month = st.sidebar.selectbox(
        "Select Month",
        month_list,
        index=4 # Default to May
    )
    month_index_1_based = month_list.index(month) + 1
    
    # --- TIME-SERIES FEATURE: Reference/Comparison Years ---
    st.sidebar.markdown("### ⏱️ Time-Series Analysis")
    analysis_mode = st.sidebar.radio(
        "Analysis Mode", 
        ["Single View (Current Year)", "Anomaly Detection (Compare Years)"]
    )
    
    all_years = [str(y) for y in range(2024, 2017, -1)] 
    current_year = st.sidebar.selectbox("Select **Current Year**", all_years, index=0)
    
    if analysis_mode == "Anomaly Detection (Compare Years)":
        reference_year_options = [y for y in all_years if y != current_year]
        reference_year = st.sidebar.selectbox(
            "Select **Reference Year** (Historical Baseline)", 
            reference_year_options, 
            index=3 # Default to 2021
        )
    else:
        reference_year = None

    # --- CHART FILTER ---
    st.sidebar.markdown("### 📊 Chart Filters")
    min_chart_year, max_chart_year = st.sidebar.select_slider(
        'Select **Year Range** for Chart:',
        options=[str(y) for y in range(2000, 2025)], 
        value=('2018', '2024')
    )
    chart_year_range = [str(y) for y in range(int(min_chart_year), int(max_chart_year) + 1)]

    # --- Vegetation Index Selection ---
    st.sidebar.markdown("### 🌿 Index Selection")
    selected_index = st.sidebar.selectbox(
        "Choose Vegetation Index",
        ["NDVI", "EVI"],
        index=0
    )

    # --- Visualization Settings ---
    st.sidebar.markdown("### 🎨 Visualization Settings")
    index_min_default = 0
    index_max_default = 9000 
    index_min, index_max = st.sidebar.slider(f"{selected_index} Range (Scaled by 10000)", -2000, 10000, (index_min_default, index_max_default))

    palette_choice = st.sidebar.selectbox(
        "Color Palette",
        ["White-Green", "Yellow-Red", "Blue-Purple", "Brown-Green", "Green-Red"]
    )
    palette_map = {
        "White-Green": ['white', 'green'],
        "Yellow-Red": ['yellow', 'red'],
        "Blue-Purple": ['blue', 'purple'],
        "Brown-Green": ['brown', 'green'],
        "Green-Red": ['00FF00', 'FF0000'] 
    }

    # ------------------- GEE DATA LOADING & REGION GEOMETRY -------------------
    
    # 1. Load Current Year Image
    current_image = get_index_image(current_year, month_index_1_based, selected_index)

    if current_image is None:
        st.warning(f"⚠️ No MODIS data found for {selected_index} for {month} {current_year}. Please try a different date/year.")
        Map = geemap.Map(center=[20,0], zoom=2)
        Map.to_streamlit(height=600)
        st.stop()
        
    # --- Get country boundary (CRITICAL SECTION MODIFIED) ---
    countries = ee.FeatureCollection("FAO/GAUL/2015/level0")
    region_geometry = None 
    center = [20, 0] 
    zoom_level = 2 
    region_found = True # Flag for messaging later

    try:
        region_feature = countries.filter(ee.Filter.eq('ADM0_NAME', region)).first()
        
        # Check if the feature exists AND is not empty
        if region_feature and region_feature.getInfo() is not None and 'id' in region_feature.getInfo(): 
            region_geometry = region_feature.geometry()
            center = region_geometry.centroid().coordinates().getInfo()[::-1]
            zoom_level = 5
            
            # Clip the image to the region
            current_image = current_image.clip(region_geometry) 
        else:
            # --- START OF NEW FEATURE IMPLEMENTATION ---
            region_found = False
            st.warning(f"⚠️ Could not locate region **'{region}'** in the dataset. Showing global view instead.")
            st.info("💡 **TIP:** Use the **drawing tools** (pencil icon ✏️ on the map) to define a custom Area of Interest!")
            region_geometry = ee.Geometry.BBox(-180, -90, 180, 90) # Use global bounds
            # --- END OF NEW FEATURE IMPLEMENTATION ---
            
    except Exception as e:
        region_found = False
        st.warning(f"⚠️ An error occurred while fetching region '{region}': {e}. Showing global view instead.")
        region_geometry = ee.Geometry.BBox(-180, -90, 180, 90) 

    
    # ------------------- MAP VISUALIZATION -------------------
    st.markdown("---")
    
    # Initialize Map with drawing tools enabled for user fallback
    Map = geemap.Map(center=center, zoom=zoom_level)
    
    # --- ADD DRAWING TOOLS ---
 # ------------------- MAP VISUALIZATION -------------------
    st.markdown("---")
    
    # Initialize Map with drawing tools enabled for user fallback
    Map = geemap.Map(center=center, zoom=zoom_level)
    
    # --- ADD DRAWING TOOLS using folium.plugins.Draw ---
    # This replaces the incorrect Map.add_tools() call
    folium.plugins.Draw(
        export=False, 
        position='topleft', 
        draw_options={
            'polyline': False, 
            'circle': False, 
            'marker': False, 
            'circlemarker': False
        }
    ).add_to(Map)
    # ----------------------------------------------------
    # ... (Rest of your map layer code remains here)
    # -------------------------

    # --- Decide which layer to show on the map (Single View or Anomaly) ---
    if analysis_mode == "Single View (Current Year)":
        st.subheader(f"🌿 {selected_index} Visualization for **{region if region_found else 'Global View'}** — {month} {current_year}") 
        index_vis = {'min': index_min, 'max': index_max, 'palette': palette_map[palette_choice]} 

        Map.addLayer(current_image, index_vis, f"{selected_index} {month} {current_year}") 
        Map.add_colorbar(vis_params=index_vis, label=f"{selected_index} (Vegetation Index)") 
        st.caption(f"Showing raw {selected_index} values. Higher values (green) mean denser vegetation.")

    elif analysis_mode == "Anomaly Detection (Compare Years)":
        
        reference_image = get_index_image(reference_year, month_index_1_based, selected_index)
        
        if reference_image is None or not region_found:
             st.warning(f"⚠️ Could not load data for the reference year {reference_year} or region not found. Showing Single View instead.")
             # Fallback to Single View map parameters
             index_vis = {'min': index_min, 'max': index_max, 'palette': palette_map[palette_choice]} 
             Map.addLayer(current_image, index_vis, f"{selected_index} {month} {current_year}") 
             Map.add_colorbar(vis_params=index_vis, label=f"{selected_index} (Vegetation Index)") 
             st.caption(f"Showing raw {selected_index} values (Anomaly data failed to load).")

        else:
            if region_geometry:
                 reference_image = reference_image.clip(region_geometry) 

            difference_image = current_image.subtract(reference_image)
            
            diff_vis = {
                'min': -2000,
                'max': 2000,
                'palette': ['FF0000', 'FFFFFF', '00FF00'], 
                'opacity': 0.8
            }
            
            st.subheader(f"📊 {selected_index} Anomaly for **{region}** — {month} {current_year} vs {reference_year}")
            
            Map.addLayer(difference_image, diff_vis, f"ANOMALY: {current_year} - {reference_year}")
            Map.add_colorbar(
                vis_params=diff_vis, 
                label=f"{selected_index} Anomaly (Difference in Vegetation Index)",
                tick_labels=['Much Drier','No Change','Much Greener']
            )
            st.caption("This map highlights areas that are significantly **Greener** (positive change) or **Drier** (negative change) than the historical reference year.")
    
    # --- Boundary visualization (Applies only if region was successfully found) ---
    if region_found: 
        boundary_vis_params = {
            'color': 'AAAAAA',
            'width': 1,
            'fillColor': '00000000'
        }
        Map.addLayer(region_geometry, boundary_vis_params, f"{region} Boundary")
    
    Map.to_streamlit(height=600)

    # ------------------- INTERACTIVE CHART -------------------
    st.markdown("---")
    st.subheader(f"📊 {selected_index} Time-Series Trend for **{region if region_found else 'Selected Area'}**")
    st.caption(f"Showing the average index value for **{month}** across the years {min_chart_year} to {max_chart_year}.")

    # Fetch and display data only if a country boundary was successfully found
    if region_found:
        chart_data = get_time_series_data(
            chart_year_range, 
            month_index_1_based, 
            selected_index, 
            region_geometry
        )
        
        if not chart_data.empty:
            st.line_chart(
                chart_data, 
                use_container_width=True, 
                y=f'Avg {selected_index}',
                height=350
            )
            st.markdown(f"The values shown are the **actual average {selected_index}** for the region, where a value of **1.0** indicates maximum greenness.")
        else:
             st.warning("⚠️ Data retrieval for the chart failed. Check GEE connection or selected region/time.")
    else:
        st.info("Select a recognized country region to see the time-series chart. (Or draw a custom area for an advanced version!)")

# ------------------ ABOUT PAGE ------------------
elif menu == "ℹ️ About":
    st.header("📘 About BloomWatch AI")
    st.markdown("""
    **BloomWatch AI** is a research and visualization project designed to help scientists, 
    students, and environmentalists track **global vegetation dynamics** in an interactive way.

    ### ⚙️ Technologies Used
    - 🛰️ [Google Earth Engine](https://earthengine.google.com/) for satellite data 
    - 🧠 Streamlit for an interactive Python UI 
    - 🌍 MODIS NDVI dataset from NASA for vegetation analysis 

    ### 👨‍💻 Developed By
    **Fahad Bashir** B.S. Software Engineering | AI & Geospatial Enthusiast 🌱 

    ### 🌟 Future Plans
    - Real-time vegetation health tracking 
    - Integration with NASA satellite APIs 
    - AI-driven bloom prediction system
    """)

    st.info("💡 Tip: Try switching between months to see how vegetation changes seasonally!")