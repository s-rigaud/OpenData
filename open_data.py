# Authors: Mélissa Mérat, Gaetan Pelerin, Samuel Rigaud
# Date: 13/10/2020
# Original file to download: https://www.data.gouv.fr/fr/datasets/r/3004168d-bec4-44d9-a781-ef16f41856a2

import csv
import json
import os
import pickle

import folium
import ipdb
import pandas as pd
import requests
from folium import plugins

addresses_cache = {}
addresses_base_url = "https://api-adresse.data.gouv.fr/search/?q="
france_location = [48.52, 2.19]

base_directory = os.path.dirname(os.path.abspath(__file__))
data_directory = os.path.join(base_directory, "data")
map_directory = os.path.join(base_directory, "maps")
for directory in (base_directory, data_directory, map_directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def save_map(folium_map: folium.Map, filename: str):
    """Save maps in the dedicated "maps" folder"""
    location = os.path.join(map_directory, filename)
    folium_map.save(location)


def get_address_from_row(row: pd.core.series.Series) -> str:
    """Concatenate row attributes to recreate a french
    formatted address
    """
    return (
        " ".join(
            (
                str(row["adresse_code_voie"]),
                str(row["adresse_nom_voie"]),
                str(row["code_postal"]),
                str(row["nom_commune"]),
            )
        )
        .strip()
        .lower()
    )


def create_distribution_heatmap(name: str, lats: list, lons: list):
    """Create a folonium distribution heatmap.
    It plots a point for every couple of latitude and longitude given
    """
    url_base = "http://server.arcgisonline.com/ArcGIS/rest/services/"
    service = "NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}"
    tileset = url_base + service

    heatmap_map = folium.Map(
        location=france_location,
        zoom_start=2,
        control_scale=True,
        tiles=tileset,
        attr="USGS style",
    )
    data = [lon_lat for lon_lat in zip(lats, lons)]

    heatmap_map.add_child(plugins.HeatMap(data))
    heatmap_map.add_child(plugins.MeasureControl())
    heatmap_map.add_child(
        plugins.Fullscreen(
            position="topright",
            title="Expand me",
            title_cancel="Exit me",
            force_separate_button=True,
        )
    )
    heatmap_map.add_child(plugins.MeasureControl())
    heatmap_map.add_child(plugins.MiniMap())
    save_map(heatmap_map, name)


def create_markup_map(name: str, df: pd.core.frame.DataFrame):
    """Place a markup for each point with a valid
    housing price evaluation and position
    """
    map_ = folium.Map(
        location=france_location,
        zoom_start=3,
        control_scale=True,
        tiles="openstreetmap",
    )
    mcg = folium.plugins.MarkerCluster(control=False)
    map_.add_child(mcg)

    houses = folium.plugins.FeatureGroupSubGroup(mcg, "houses")
    appartements = folium.plugins.FeatureGroupSubGroup(mcg, "appartements")
    others = folium.plugins.FeatureGroupSubGroup(mcg, "others")
    map_.add_child(houses)
    map_.add_child(appartements)
    map_.add_child(others)

    for _, row in df.iterrows():
        housing_type = row["type_local"]
        if housing_type == "Maison":
            color = "darkgreen"
            icon = "home"
            context = houses

        elif housing_type == "Appartement":
            color = "red"
            icon = "pause"
            context = appartements
        else:
            color = "black"
            icon = "info-sign"
            context = others

        price = int(row["valeur_fonciere"])
        address = get_address_from_row(row)
        context.add_child(
            folium.Marker(
                (row["latitude"], row["longitude"]),
                popup=folium.Popup(
                    f"{housing_type}</br> {address} <b>{price}€</b>",
                    # Not working properly
                    max_width="400px",
                    min_width="200px",
                ),
                tooltip=housing_type,
                icon=folium.Icon(color=color, icon=icon),
            )
        )

    map_.add_child(
        plugins.Fullscreen(
            position="topright",
            title="Expand me",
            title_cancel="Exit me",
            force_separate_button=True,
        )
    )
    map_.add_child(folium.LayerControl(collapsed=False))
    map_.add_child(plugins.MeasureControl())
    map_.add_child(plugins.MiniMap())
    save_map(map_, name)


def add_region_code(df: pd.core.frame.DataFrame):
    """Add the Code region column in the dataframe
    using a mapping based over the Code departement column
    """
    print("Retreving departement - region mapping ...")
    mapping = {}
    mapping_file = os.path.join(data_directory, "mapping_dep_regions.csv")
    with open(mapping_file, newline="") as csvfile:
        spamreader = csv.reader(csvfile, delimiter=",")
        for csv_row in spamreader:
            mapping[csv_row[0]] = csv_row[2]

    print("Assigning region code for each row")
    region_code = []
    for _, row in df.iterrows():
        try:
            region_code.append(mapping[row["code_departement"]])
        except:
            import ipdb; ipdb.set_trace()

    df["code_region"] = region_code


def create_area_maps(df: pd.core.frame.DataFrame):
    """Create maps with region and department shaped areas
    colored following the median housing price value
    """
    add_region_code(df)

    areas = {
        "departement": {
            "location": france_location,
            "zoom_start": 5,
        },
        "region": {
            "location": france_location,
            "zoom_start": 3,
        },
    }

    for area, scale in areas.items():
        dep_value = df[[f"code_{area}", "valeur_fonciere", "type_local"]].rename(
            columns={f"code_{area}": "id", "valeur_fonciere": "€(Median)"}
        )
        median_dep_value_houses = (
            dep_value[dep_value["type_local"] == "Maison"]
            .groupby(["id"])
            .median()
            .astype(int)
        ).reset_index()

        france_geo = f"https://france-geojson.gregoiredavid.fr/repo/{area}s.geojson"
        m = folium.Map(**scale)
        m.add_child(
            folium.Choropleth(
                geo_data=france_geo,
                name=f"{area.capitalize()} mapping",
                data=median_dep_value_houses,
                columns=["id", "€(Median)"],
                key_on="feature.properties.code",
                fill_color="YlGnBu",
                fill_opacity=0.7,
                line_opacity=0.2,
                legend_name="Housing value (Median €)",
            )
        )
        m.add_child(folium.LayerControl())
        save_map(m, f"area_map_{area}.html")

def load_data_and_create_maps():
    """First we load data from csv file. Next we filter lines without
    interesting data. Finally we plot every point on the three
    different type of maps. (heatmap, point map & region/department map)
    """
    print("Loading and cleaning CSV file ...")
    df = pd.read_csv(
        os.path.join(data_directory, "etalab_dvf_2019.csv"),
        delimiter=",",
        encoding="utf-8",
    )

    # Filter points without positions -> NaN or 0
    df = df[
        pd.notnull(df["longitude"])
        & pd.notnull(df["latitude"])
        & (df["valeur_fonciere"] > 0)
    ]
    df["code_departement"] = df["code_departement"].map("{:0>2}".format)

    sample_df = df.sample(n=5000).copy()

    print("Creating maps ...")
    """create_distribution_heatmap(
        name="distribution_heatmap.html", lats=sample_df["latitude"], lons=sample_df["longitude"]
    )"""
    create_markup_map(name="markup_map.html", df=sample_df)

    # Heavy process
    # create_area_maps(df=sample_df)

if __name__ == "__main__":
    load_data_and_create_maps()
