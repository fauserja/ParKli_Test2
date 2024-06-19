import base64
import datetime
import io

import dash
from dash.dependencies import Input, Output, State
from dash import dcc, html, dash_table, callback


import pandas as pd

import numpy as np
import statistics 
import requests
import os
from geopy.distance import geodesic
from PIL import Image
import sys

import dash_bootstrap_components as dbc
from datetime import datetime
import plotly.express as px
import plotly.graph_objs as go

import requests
from geopy.distance import geodesic
import json
from pandas import json_normalize
from geopy.geocoders import Nominatim
import pyproj
from sqlalchemy import create_engine, MetaData, inspect, text
import configparser
from configparser import ConfigParser
import psycopg2
import datetime
from datetime import date, timedelta


# To create meta tag for each page, define the title, image, and description.
#dash.register_page(__name__,
                   #path='/',  # '/' is home page and it represents the url
                   #name='Home',  # name of page, commonly used as name of link
                   #title='Index',  # title that appears on browser's tab
                   #image='pg1.png',  # image in the assets folder
                   #description='ParKli Overview'
#)


# page 1 data
#df = px.data.gapminder()

##########################################################################################################################################
# Funktion zum Lesen der Datenbankverbindung aus einer Ini-Datei
def database_connection():
     # Pfad des aktuellen Skripts
    current_script_path = os.path.dirname(__file__)

    # Pfad zum Basisverzeichnis des Projekts
    base_directory_path = os.path.dirname(current_script_path)

    # Pfad zur config.ini im lib-Ordner
    config_file_path = os.path.join(base_directory_path, 'lib', 'config.ini')

    # Konfigurationsdatei lesen
    config = configparser.ConfigParser()
    config.read(config_file_path)

    # Datenbankverbindung herstellen
    db_params = config['database']
    connection_string = f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
    engine = create_engine(connection_string)
    return engine

#####################################################################################################################################################
# Funktion zum Abrufen der Daten aus der Datenbank
def fetch_data_from_db(engine):
    query = text('SELECT * FROM "greenSpaceHackCleanData"')
    return pd.read_sql(query, engine)


########################################################################################################################################################

url = f"https://api.inaturalist.org/v1/observations?project_id=parkli"
response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    #data["total_results"]
else:
    print("Fehler bei der Anfrage:", response.status_code)

########################################################################################################################################
def download_inaturalist_data(min_lat, max_lat, min_lon, max_lon):
     
    # Definieren Sie den geografischen Bereich
    swlat = min_lat  # Südliche Breite
    swlng = min_lon  # Westliche Länge
    nelat = max_lat  # Nördliche Breite
    nelng = max_lon  # Östliche Länge


    # Setzen Sie die Anfangsseite auf 1
    page = 1

    # Initialisieren Sie eine leere Liste zum Speichern der Beobachtungsdaten
    all_observations = []

    while True:
        
        if page > 3:
            break
        
        # Setzen Sie die API-Endpunkt-URL mit den entsprechenden Parametern
        url = f'https://api.inaturalist.org/v1/observations?swlat={swlat}&swlng={swlng}&nelat={nelat}&nelng={nelng}&page={page}&per_page=200'

        # Machen Sie eine GET-Anfrage an die iNaturalist API
        response = requests.get(url)

        # Extrahieren Sie die Beobachtungsdaten aus der API-Antwort (JSON-Format)
        data = response.json()

        # Überprüfen Sie, ob Beobachtungsdaten vorhanden sind
        if 'results' in data:
            # Fügen Sie die Beobachtungsdaten zur Liste hinzu
            all_observations.extend(data['results'])
            
            # Überprüfen Sie, ob die Anzahl der Beobachtungen kleiner als die maximale Seite ist
            if len(data['results']) < data['per_page']:
                break  # Beenden Sie die Schleife, wenn alle Beobachtungen abgerufen wurden

            # Inkrementieren Sie die Seite für die nächste Anfrage
            page += 1
        else:
            break  # Beenden Sie die Schleife, wenn keine Beobachtungen vorhanden sind
    # Ausgabe der Gesamtanzahl der heruntergeladenen Beobachtungen
    observation_count = len(all_observations)
    print(f'Anzahl der heruntergeladenen Beobachtungen: {observation_count}')
    
    df = pd.json_normalize(all_observations)
    df[['latitude', 'longitude']] = df['location'].str.split(',', expand=True)

    # Datentypen der neuen Spalten korrigieren
    df['latitude'] = df['latitude'].astype(float)
    df['longitude'] = df['longitude'].astype(float)
    df.head()
    print(len(df))
    return df 

#####################################################################################################################
# Function to download iNaturalist data from PostgreSQL
def download_data_from_postgresql(min_lat, max_lat, min_lon, max_lon):
    config = ConfigParser()
    config.read('config.ini')
    connection_details = {
        'dbname': config.get('database', 'dbname'),
        'user': config.get('database', 'user'),
        'password': config.get('database', 'password'),
        'host': config.get('database', 'host'),
        'port': config.get('database', 'port')
    }
    
    try:
        conn = psycopg2.connect(**connection_details)
        cursor = conn.cursor()
        query = """
        SELECT * FROM inaturalist_observations
        WHERE latitude BETWEEN %s AND %s
        AND longitude BETWEEN %s AND %s;
        """
        cursor.execute(query, (min_lat, max_lat, min_lon, max_lon))
        rows = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(rows, columns=colnames)
        cursor.close()
        conn.close()
        return df
    except Exception as e:
        print("Fehler beim Herunterladen der Daten:", e)
        return pd.DataFrame()



#######################################################################################################################################################################
 # Navigiert eine Ebene nach oben und dann in den Ordner 'assets'   
relative_path = os.path.join('..', 'assets', 'CSVPictureDate')
    
# Vollständiger Pfad zur Datei, ausgehend vom aktuellen Skriptverzeichnis
save_folder_CSV = os.path.join(os.path.dirname(__file__), relative_path)

# Überprüfen, ob bereits eine CSV-Datei existiert
csv_path = os.path.join(save_folder_CSV, 'data.csv')
if os.path.exists(csv_path):
# Lade das DataFrame aus der CSV-Datei
    dfEyeOnWater = pd.read_csv(csv_path)
    dfEyeOnWater['date_photo'] = pd.to_datetime(dfEyeOnWater['date_photo'])  # Automatisch das Format bestimmen
    #dfEyeOnWater['date_photo'] = pd.to_datetime(dfEyeOnWater['date_photo'], format='%m/%d/%Y %I:%M:%S %p')
    #dfEyeOnWater['month_year'] = dfEyeOnWater['date_photo'].dt.to_period("M")
    #dfEyeOnWater['month'] = pd.DatetimeIndex(dfEyeOnWater['date_photo']).month
    #dfEyeOnWater['day'] = dfEyeOnWater['date_photo'].dt.to_period("D")
    #dfEyeOnWater['month_year_period'] = pd.PeriodIndex(dfEyeOnWater['month_year'], freq='M')
    #dfEyeOnWater['month_year_period'] = dfEyeOnWater['month_year_period'].apply(lambda x: x.strftime('%Y-%m'))
    print(dfEyeOnWater.head())

else:
    dfEyeOnWater =0 

#########################################################################################################################################################################
try:
    #Laden der Daten von greenspacehack.com
   
    engine = database_connection()
    dfGreenSpaceHack = fetch_data_from_db(engine)
  
except Exception as e:
    print(f"Daten konnten nicht heruntergeladen werden: {e}")
    engine = database_connection()
    dfGreenSpaceHack = fetch_data_from_db(engine)
    if dfGreenSpaceHack is not None:
        print("Daten erfolgreich aus der Datenbank abgerufen.")
    else:
        print("Keine Daten in der Datenbank vorhanden.")
    
##############################################################################################################################################

card_iNaturalist = dbc.Card(
  
      #dbc.CardHeader("Anzahl Beobachtungen iNaturalist ParKli"),
      dbc.CardBody(
        [
            html.H4([html.I(className="bi bi-search"), " Beobachtungen iNaturalist ParKli"], className="text-nowrap"),
            html.H5(data["total_results"]),
          
        ], className="border-start border-success border-5"
    ),
    className="text-center m-4 shadow bg-light rounded",
  
)


card_GreenSpaceHack = dbc.Card(
    dbc.CardBody(
        [
            html.H4([html.I(className="bi bi-question-square"), " Anzahl Fragebögen Greenspace Hack"], className="text-nowrap"),
            html.H5(len(dfGreenSpaceHack)),
        ], className="border-start border-danger border-5"
    ),
    className="text-center m-4 shadow bg-light rounded",
)


card_EyeOnWater = dbc.Card(
    dbc.CardBody(
        [
            html.H4([html.I(className="bi bi-water"), " Anzahl Beobachtungen EyeOnWater"], className="text-nowrap"),
            html.H5(len(dfEyeOnWater)),
    
        ], className="border-start border-secondary border-5"
    ),
    className="text-center m-4 shadow bg-white rounded",
)

# Layout
layout = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(card_iNaturalist), 
                dbc.Col(card_GreenSpaceHack), 
                dbc.Col(card_EyeOnWater),
            ],
        ),
        html.Br(),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4([html.I(className="bi bi-calendar"), " Beobachtungszeitraum auswählen"], className="text-nowrap"),
                                dcc.DatePickerRange(
                                    id='date-range',
                                    start_date=datetime.datetime.today() - datetime.timedelta(days=720),
                                    end_date=datetime.datetime.today(),
                                    display_format='YYYY-MM-DD'
                                ),
                            ], className="border-start border-info border-5"
                        ),
                        className="text-center m-4 shadow bg-light rounded"
                    )
                )
            ]
        ),
        html.Br(),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4([html.I(className="bi bi-thermometer-sun"), " Heatmap der Beobachtungen EyeOnWater"], className="text-nowrap"),
                                dcc.Graph(id='density-eyeonwater')
                            ], className="border-start border-secondary border-5"
                        ),
                        className="text-center m-4 shadow bg-light rounded"
                    )
                )
            ]
        ),
        html.Br(),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4([html.I(className="bi bi-thermometer-sun"), " Heatmap der Beobachtungen iNaturalist"], className="text-nowrap"),
                                dcc.Graph(id='density-inaturalist')
                            ], className="border-start border-success border-5"
                        ),
                        className="text-center m-4 shadow bg-light rounded"
                    )
                )
            ]
        ),
        html.Br(),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4([html.I(className="bi bi-thermometer-sun"), " Heatmap der Beobachtungen GreenSpaceHack"], className="text-nowrap"),
                                dcc.Graph(id='density-greenspacehack')
                            ], className="border-start border-danger border-5"
                        ),
                        className="text-center m-4 shadow bg-light rounded"
                    )
                )
            ]
        )
    ]
)

# Callback for updating density map for EyeOnWater
@callback(
    Output('density-eyeonwater', 'figure'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    prevent_initial_call=True
)
def update_density_eyeonwater(start_date, end_date):
    mask = (dfEyeOnWater['date_photo'] >= start_date) & (dfEyeOnWater['date_photo'] <= end_date)
    filtered_df = dfEyeOnWater.loc[mask]
    fig = px.density_mapbox(
        filtered_df, lat='lat', lon='lng', z='fu_processed',
        radius=10, center=dict(lat=48.4914, lon=9.2043), zoom=10,
        mapbox_style="open-street-map"
    )
    return fig



# Function to fetch iNaturalist data for invasive and threatened species
def fetch_inaturalist_data_(start_date, end_date):
    url = f"https://api.inaturalist.org/v1/observations?project_id=parkli&d1={start_date}&d2={end_date}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.json_normalize(data['results'])
        df[['latitude', 'longitude']] = df['location'].str.split(',', expand=True)
        df['latitude'] = df['latitude'].astype(float)
        df['longitude'] = df['longitude'].astype(float)
        df['taxon.threatened'] = df['taxon.threatened'].replace({'true': True, 'false': False}).fillna(False)
        df['taxon.introduced'] = df['taxon.introduced'].replace({'true': True, 'false': False}).fillna(False)
        return df
    return pd.DataFrame()
def fetch_inaturalist_data(start_date, end_date):
    config = ConfigParser()
    config.read('config.ini')
    connection_details = {
        'dbname': config.get('database', 'dbname'),
        'user': config.get('database', 'user'),
        'password': config.get('database', 'password'),
        'host': config.get('database', 'host'),
        'port': config.get('database', 'port')
    }
    
    try:
        conn = psycopg2.connect(**connection_details)
        cursor = conn.cursor()
        query = """
        SELECT * FROM inaturalist_observations
        WHERE latitude BETWEEN %s AND %s
        AND longitude BETWEEN %s AND %s;
        """
        cursor.execute(query, (min_lat, max_lat, min_lon, max_lon))
        rows = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(rows, columns=colnames)
        cursor.close()
        conn.close()
        return df
    except Exception as e:
        print("Fehler beim Herunterladen der Daten:", e)
        return pd.DataFrame()


# Callback for updating density map for iNaturalist
@callback(
    Output('density-inaturalist', 'figure'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    prevent_initial_call=True
)
def update_density_inaturalist(start_date, end_date):
    df = fetch_inaturalist_data(start_date, end_date)
    if df.empty:
        return go.Figure()

    invasive_df = df[df['taxon.introduced'] == True]
    threatened_df = df[df['taxon.threatened'] == True]

    fig = go.Figure()

    if not invasive_df.empty:
        fig.add_trace(go.Densitymapbox(lat=invasive_df['latitude'], lon=invasive_df['longitude'], z=invasive_df['taxon.name'], radius=10, name='Invasive Species'))
    
    if not threatened_df.empty:
        fig.add_trace(go.Densitymapbox(lat=threatened_df['latitude'], lon=threatened_df['longitude'], z=threatened_df['taxon.name'], radius=10, name='Threatened Species'))

    fig.update_layout(mapbox_style="open-street-map", mapbox_center={"lat": 48.4914, "lon": 9.2043}, mapbox_zoom=10)
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    return fig

# Callback for updating density map for GreenSpaceHack
@callback(
    Output('density-greenspacehack', 'figure'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    prevent_initial_call=True
)
def update_density_greenspacehack(start_date, end_date):
    #mask = (dfGreenSpaceHack['date'] >= start_date) & (dfGreenSpaceHack['date'] <= end_date)
    #filtered_df = dfGreenSpaceHack.loc[mask]
    fig = px.density_mapbox(
        dfGreenSpaceHack, lat='location.1', lon='location.0', z='Overall NEST score',
        radius=10, center=dict(lat=48.4914, lon=9.2043), zoom=10,
        mapbox_style="open-street-map"
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig


