import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import plotly.express as px
import dash_leaflet as dl
import numpy as np

df = pd.read_csv("2021-04.csv")
df['Departure'] = pd.to_datetime(df['Departure'], format='mixed', errors='coerce')
df['Weekday'] = df['Departure'].dt.day_name()
df['Hour'] = df['Departure'].dt.hour

departure_stations = df['Departure station name'].dropna().unique()
return_stations = df['Return station name'].dropna().unique()
departure_stations.sort()
return_stations.sort()

station_coords = {}
np.random.seed(42)
base_lat, base_lon = 60.1699, 24.9384
all_stations = np.unique(np.concatenate((departure_stations, return_stations)))
for name in all_stations:
    lat = base_lat + np.random.normal(0, 0.02)
    lon = base_lon + np.random.normal(0, 0.03)
    station_coords[name] = [lat, lon]

external_stylesheets = [dbc.themes.LUX]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "Helsinki Bike Route Viewer"

app.layout = dbc.Container([
    html.H1("🚲 Helsinki Bike Route Viewer", className="text-center my-4"),
    dbc.Card([
        dbc.CardHeader("Select Route & Filters"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Departure Station"),
                    dcc.Dropdown(
                        id='departure-dropdown',
                        options=[{'label': name, 'value': name} for name in departure_stations],
                        value=departure_stations[0]
                    )
                ], md=6),
                dbc.Col([
                    html.Label("Return Station"),
                    dcc.Dropdown(
                        id='return-dropdown',
                        options=[{'label': name, 'value': name} for name in return_stations],
                        value=return_stations[0]
                    )
                ], md=6)
            ]),
            html.Br(),
            dbc.Row([
                dbc.Col([
                    html.Label("Date Range"),
                    dcc.DatePickerRange(
                        id='date-range',
                        min_date_allowed=df['Departure'].min().date(),
                        max_date_allowed=df['Departure'].max().date(),
                        start_date=df['Departure'].min().date(),
                        end_date=df['Departure'].max().date()
                    )
                ], md=6),
                dbc.Col([
                    html.Label("Weekdays"),
                    dcc.Checklist(
                        id='weekday-filter',
                        options=[{'label': day, 'value': day} for day in df['Weekday'].dropna().unique()],
                        value=list(df['Weekday'].dropna().unique()),
                        inline=True
                    )
                ], md=6)
            ])
        ])
    ], className="mb-4"),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📊 Trip Stats"),
                dbc.CardBody(id='stats-output')
            ])
        ])
    ]),
    dbc.Card([
        dbc.CardHeader("🗺️ Trip Route Map"),
        dbc.CardBody([
            dl.Map(center=[60.1699, 24.9384], zoom=11, children=[
                dl.TileLayer(),
                dl.LayerGroup(id="trip-map")
            ], style={'width': '100%', 'height': '500px'})
        ])
    ], className="my-4"),
    dbc.Card([
        dbc.CardHeader("📅 Hourly Trip Heatmap (Use Slider to Animate)"),
        dbc.CardBody([
            dcc.Slider(id='hour-slider', min=0, max=23, step=1, value=0,
                       marks={i: str(i) for i in range(0, 24)}, tooltip={"placement": "bottom"}),
            dcc.Graph(id='heatmap')
        ])
    ])
], fluid=True)

@app.callback(
    Output('stats-output', 'children'),
    Output('trip-map', 'children'),
    Output('heatmap', 'figure'),
    Input('departure-dropdown', 'value'),
    Input('return-dropdown', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    Input('weekday-filter', 'value'),
    Input('hour-slider', 'value')
)
def update_dashboard(dep_station, ret_station, start_date, end_date, weekdays, selected_hour):
    filt = (
        (df['Departure station name'] == dep_station) &
        (df['Return station name'] == ret_station) &
        (df['Departure'] >= pd.to_datetime(start_date)) &
        (df['Departure'] <= pd.to_datetime(end_date)) &
        (df['Weekday'].isin(weekdays))
    )
    trip_df = df[filt]
    trip_count = len(trip_df)
    avg_dist = trip_df['Covered distance (m)'].mean() / 1000 if not trip_df.empty else 0
    avg_dur = trip_df['Duration (sec.)'].mean() / 60 if not trip_df.empty else 0
    stats = html.Div([
        html.P(f"Total Trips: {trip_count}"),
        html.P(f"Average Distance: {avg_dist:.2f} km"),
        html.P(f"Average Duration: {avg_dur:.2f} minutes")
    ])
    markers = []
    polyline = []
    if dep_station in station_coords:
        lat1, lon1 = station_coords[dep_station]
        markers.append(dl.Marker(position=[lat1, lon1], children=dl.Popup(f"Departure: {dep_station}")))
    else:
        lat1, lon1 = None, None
    if ret_station in station_coords:
        lat2, lon2 = station_coords[ret_station]
        markers.append(dl.Marker(position=[lat2, lon2], children=dl.Popup(f"Return: {ret_station}")))
    else:
        lat2, lon2 = None, None
    if lat1 is not None and lat2 is not None:
        polyline = [
            dl.Polyline(positions=[[lat1, lon1], [lat2, lon2]], color='blue', weight=4, children=dl.Tooltip(f"{dep_station} ➜ {ret_station}"))
        ]
    if trip_df.empty:
        heatmap_fig = px.imshow([[0]], labels=dict(x="Hour", y="Weekday", color="Trips"),
                                x=[0], y=["No Data"], text_auto=True)
    else:
        hour_df = trip_df[trip_df['Hour'] == selected_hour]
        heat_data = hour_df.groupby('Weekday').size().reset_index(name='Trips')
        week_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heat_data['Weekday'] = pd.Categorical(heat_data['Weekday'], categories=week_order, ordered=True)
        heat_data = heat_data.sort_values('Weekday')
        heatmap_fig = px.bar(heat_data, x='Weekday', y='Trips',
                             title=f"Trips by Weekday at {selected_hour}:00",
                             labels={'Trips': 'Trip Count', 'Weekday': 'Day'})
    return stats, markers + polyline, heatmap_fig

if __name__ == '__main__':
    app.run(debug=True)
