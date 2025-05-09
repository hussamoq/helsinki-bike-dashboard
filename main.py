import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import plotly.express as px

st.set_page_config(page_title="Helsinki Bike Trips", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("2021-04.csv")
    df['Departure'] = pd.to_datetime(df['Departure'], errors='coerce')
    df['Weekday'] = df['Departure'].dt.day_name()
    df['Hour'] = df['Departure'].dt.hour
    return df

df = load_data()

st.title("🚲 Helsinki Bike Trip Explorer")

station_names = df['Departure station name'].dropna().unique()
station_names.sort()

col1, col2 = st.columns(2)

with col1:
    dep_station = st.selectbox("Select Departure Station", station_names)
with col2:
    ret_station = st.selectbox("Select Return Station", df['Return station name'].dropna().unique())

col3, col4 = st.columns(2)

with col3:
    start_date = st.date_input("Start Date", df['Departure'].min().date())
with col4:
    end_date = st.date_input("End Date", df['Departure'].max().date())

weekdays = st.multiselect("Select Weekdays", options=df['Weekday'].unique(), default=list(df['Weekday'].unique()))

filtered = df[(df['Departure station name'] == dep_station) &
              (df['Return station name'] == ret_station) &
              (df['Departure'].dt.date >= start_date) &
              (df['Departure'].dt.date <= end_date) &
              (df['Weekday'].isin(weekdays))]

st.markdown("---")

st.subheader("📊 Trip Stats")
col5, col6, col7 = st.columns(3)

col5.metric("Total Trips", len(filtered))
col6.metric("Average Duration (min)", f"{(filtered['Duration (sec.)'].mean() / 60):.2f}" if not filtered.empty else "0")
col7.metric("Average Distance (km)", f"{(filtered['Covered distance (m)'].mean() / 1000):.2f}" if not filtered.empty else "0")

st.markdown("---")

st.subheader("🗺️ Trip Route Map")

station_coords = {}
np.random.seed(42)
base_lat, base_lon = 60.1699, 24.9384
all_stations = df['Departure station name'].dropna().unique().tolist() + df['Return station name'].dropna().unique().tolist()

for name in np.unique(all_stations):
    lat = base_lat + np.random.normal(0, 0.02)
    lon = base_lon + np.random.normal(0, 0.03)
    station_coords[name] = [lat, lon]

if dep_station in station_coords and ret_station in station_coords:
    dep_coord = station_coords[dep_station]
    ret_coord = station_coords[ret_station]

    map_df = pd.DataFrame([{
        "lat": dep_coord[0], "lon": dep_coord[1], "label": "Departure"
    }, {
        "lat": ret_coord[0], "lon": ret_coord[1], "label": "Return"
    }])

    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=pdk.ViewState(latitude=60.1699, longitude=24.9384, zoom=11),
        layers=[
            pdk.Layer("ScatterplotLayer",
                      data=map_df,
                      get_position='[lon, lat]',
                      get_fill_color='[200, 30, 0, 160]',
                      get_radius=80),
            pdk.Layer("LineLayer",
                      data=map_df,
                      get_source_position='[lon, lat]',
                      get_target_position='[lon, lat]',
                      get_color='[0, 0, 255, 160]',
                      auto_highlight=True)
        ]
    ))

st.markdown("---")

st.subheader("📅 Hourly Trip Breakdown")
selected_hour = st.slider("Select Hour of Day", min_value=0, max_value=23, value=8)
hour_data = filtered[filtered['Hour'] == selected_hour]

if not hour_data.empty:
    chart_data = hour_data.groupby('Weekday').size().reset_index(name='Trips')
    week_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    chart_data['Weekday'] = pd.Categorical(chart_data['Weekday'], categories=week_order, ordered=True)
    chart_data = chart_data.sort_values('Weekday')
    fig = px.bar(chart_data, x='Weekday', y='Trips', title=f"Trips at {selected_hour}:00 by Weekday")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No trip data available for this hour and filters.")
