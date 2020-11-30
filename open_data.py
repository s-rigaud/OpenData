# Authors: Mélissa Mérat, Gaetan Pelerin, Samuel Rigaud
# Date: 13/10/2020
# Original file to download: https://www.data.gouv.fr/fr/datasets/r/3004168d-bec4-44d9-a781-ef16f41856a2

import csv
import json
import os
import pickle

import folium
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
addresses_cache_file = os.path.join(data_directory, "addresses_cache_file.txt")


def load_addresses_cache():
    """Load already saved addresses and GPS positions
    saved in a picled file
    """
    if not os.path.exists(addresses_cache_file):
        with open(addresses_cache_file, "wb") as f:
            pickle.dump(addresses_cache, f)

    with open(addresses_cache_file, "rb") as f:
        addresses_cache.update(pickle.load(f))
        print(f"Already {len(addresses_cache)} addresses in cache")
        return addresses_cache


def save_addresses_cache():
    """Save the address cache file"""
    with open(addresses_cache_file, "wb") as f:
        pickle.dump(addresses_cache, f)


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
    print(address)

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
        region_code.append(mapping[row["Code departement"]])

    df["Code region"] = region_code


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
        dep_value = df[[f"Code {area}", "Valeur fonciere", "Type local"]].rename(
            columns={f"Code {area}": "id", "Valeur fonciere": "€(Median)"}
        )
        median_dep_value_houses = (
            dep_value[dep_value["Type local"] == "Maison"]
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
    """First we load data from csv file. Next we call the external API
    to retrieve the exact loaction. Finally we plot every point on the
    three different type of maps.
    (heatmap, point map & region/department map)
    """
    print("Loading and cleaning CSV file ...")
    df = pd.read_csv(
        os.path.join(data_directory, "valeurs_foncieres.txt"),
        delimiter="|",
        encoding="utf-8",
    )
    # Cleaning df
    df["Valeur fonciere"] = df["Valeur fonciere"].str.replace(",", ".").astype(float)
    df["Code departement"] = df["Code departement"].map("{:0>2}".format)

    # sample_df = df.head(600000).copy()
    sample_df = df.iloc[400000:600000].copy()

    print("Loading addresses using cache ...")
    load_addresses_cache()
    lons = []
    lats = []
    for _, row in sample_df.iterrows():
        try:
            lon, lat = get_coordinates(row)
        except Exception as exc:
            lon, lat = 0, 0
            print(exc)
        lons.append(lon)
        lats.append(lat)
        if (_ % 100 == 0):
            print(_)
            print("Saving addresses")
            save_addresses_cache()

    sample_df["lon"] = lons
    sample_df["lat"] = lats
    # Filter points without positions -> NaN or 0
    sample_df = sample_df[
        (pd.notnull(sample_df["lon"]) & sample_df["lon"] != 0)
        & (pd.notnull(sample_df["lat"]) & sample_df["lat"] != 0)
        & (sample_df["Valeur fonciere"] > 0)
    ]

    save_addresses_cache()

    print("Creating maps ...")
    create_distribution_heatmap(
        name="distribution_heatmap.html", lats=sample_df["lat"], lons=sample_df["lon"]
    )
    create_markup_map(name="markup_map.html", df=sample_df)

    # Heavy process
    create_area_maps(sample_df)

if __name__ == "__main__":
    load_data_and_create_maps()
