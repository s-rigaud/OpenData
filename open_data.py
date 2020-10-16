# Authors: Mélissa Mérat, Gaetan Pelerin, Samuel Rigaud
# Date: 13/10/2020
# Original file to download: https://www.data.gouv.fr/fr/datasets/r/3004168d-bec4-44d9-a781-ef16f41856a2

# TODO
# Local mean with Department sqaure €
# panda mean or attribute search

import csv
import json
import os
import pickle
from typing import Iterable

import folium
import pandas as pd
import requests
from folium import plugins

addresses_cache = {}
addresses_base_url = "https://api-adresse.data.gouv.fr/search/?q="

base_directory = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(base_directory):
    os.makedirs(base_directory)
data_directory = os.path.join(base_directory, "data")
if not os.path.exists(data_directory):
    os.makedirs(data_directory)
addresses_cache_file = os.path.join(data_directory, "addresses_cache_file.txt")
map_directory = os.path.join(base_directory, "maps")
if not os.path.exists(map_directory):
    os.makedirs(map_directory)


def load_addresses_cache():
    if not os.path.exists(addresses_cache_file):
        with open(addresses_cache_file, "wb") as f:
            pickle.dump(addresses_cache, f)

    with open(addresses_cache_file, "rb") as f:
        addresses_cache.update(pickle.load(f))
        print(f"Already {len(addresses_cache)} addresses in cache")
        return addresses_cache


def save_addresses_cache():
    with open(addresses_cache_file, "wb") as f:
        pickle.dump(addresses_cache, f)


def save_map(folium_map: folium.Map, filename: str):
    """Save maps in the dedicated folder"""
    location = os.path.join(map_directory, filename)
    folium_map.save(location)


def get_address_from_row(row: pd.core.series.Series) -> str:
    return (
        " ".join(
            (
                str(row["No voie"]),
                str(row["Voie"]),
                str(row["Code postal"]),
                str(row["Commune"]),
                str(row["Code departement"]),
                str(row["Code commune"]),
            )
        )
        .strip()
        .lower()
    )


def get_coordinates(row: pd.core.series.Series) -> tuple:
    """For given french addresses formatted parameters, we
    call the government API to retrieve the GPS position of the
    location

    We are using a pickled file base cache to avoid spamming the API
    """
    address = get_address_from_row(row)

    if not addresses_cache.get(address):
        response = requests.get(addresses_base_url + address)
        addresses = json.loads(response.text)

        features = addresses["features"]
        if features:
            res = (
                features[0]["geometry"]["coordinates"][0],
                features[0]["geometry"]["coordinates"][1],
            )
        else:
            res = (0, 0)
        addresses_cache[address] = res

    return addresses_cache[address]


def create_distribution_heatmap(name: str, lats: list, lons: list):
    """Create a folonium distribution heatmap
    It plots a point for every couple of latitude and longitude given
    """
    url_base = "http://server.arcgisonline.com/ArcGIS/rest/services/"
    service = "NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}"
    tileset = url_base + service

    heatmap_map = folium.Map(
        location=[45, 8],
        zoom_start=2,
        control_scale=True,
        tiles=tileset,
        attr="USGS style",
    )
    data = [lon_lat for lon_lat in zip(lats, lons)]

    hm = plugins.HeatMap(data)
    heatmap_map.add_child(hm)
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


def create_markup_map(name: str, df):
    """Test function to create nice Leaflet html files"""
    map_ = folium.Map(
        location=[45, 8],
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
        housing_type = row["Type local"]
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

        price = int(row["Valeur fonciere"])
        address = get_address_from_row(row)
        context.add_child(
            folium.Marker(
                (row["lat"], row["lon"]),
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


def create_area_map(lats: list, lons: list):
    for scale in ["departement", "region"]:
        france_data = pd.read_csv(
            os.path.join(data_directory, f"local_avg_{scale}.csv")
        )
        france_geo = f"https://france-geojson.gregoiredavid.fr/repo/{scale}s.geojson"

        m = folium.Map(location=[48, -102], zoom_start=3)
        folium.Choropleth(
            geo_data=france_geo,
            name=f"{scale.capitalize()} mapping",
            data=france_data,
            columns=["id", "€(avg)"],
            key_on="feature.properties.code",
            fill_color="YlGn",
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name="Housing value (avg €)",
        ).add_to(m)

        folium.LayerControl().add_to(m)
        save_map(m, f"area_map_{scale}.html")


if __name__ == "__main__":
    load_addresses_cache()

    print("Loading and cleaning CSV file ...")
    df = pd.read_csv(
        os.path.join(data_directory, "valeursfoncieres-2019.csv"),
        delimiter="|",
        encoding="utf-8",
    )
    df = df.head(10000)

    # Cleaning df
    df["Valeur fonciere"] = (
        df["Valeur fonciere"].str.replace(",", ".").astype(float)
    )

    print("Loading addresses using cache ...")
    lons = []
    lats = []
    for _, row in df.iterrows():
        print(_)
        lon, lat = get_coordinates(row)
        lons.append(lon)
        lats.append(lat)
    df["lon"] = lons
    df["lat"] = lats
    # Filter points without positions -> NaN or 0
    df = df[
        (pd.notnull(df["lon"]) & df["lon"] != 0)
        & (pd.notnull(df["lat"]) & df["lat"] != 0)
        & (df["Valeur fonciere"] > 0)
    ]
    import ipdb; ipdb.set_trace()
    dep_value = df[['Code departement', 'Valeur fonciere', "Type local"]]
    avg_dep_value_houses = dep_value[dep_value["Type local"] == "Maison"].groupby(['Code departement']).mean().astype(int)

    print("Creating maps ...")
    create_distribution_heatmap(
        name="distribution_heatmap.html", lats=df["lat"], lons=df["lon"]
    )
    create_markup_map(name="markup_map.html", df=df)
    create_area_map(lats=df["lat"], lons=df["lon"])
    save_addresses_cache()
