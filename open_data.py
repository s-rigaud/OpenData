# Authors: Mélissa Mérat, Gaetan Pelerin, Samuel Rigaud
# Date: 13/10/2020

# TODO
# Use folonium stickers
# Heat map €
# Local mean €
# panda mean or attribute search

import csv
import json
import pickle
from typing import Iterable

import folium
import requests
from folium import plugins


addresses_cache = {}
addresses_cache_file = "addresses_cache_file.txt"
addresses_base_url = "https://api-adresse.data.gouv.fr/search/?q="


def load_addresses_cache():
    with open(addresses_cache_file, "rb") as f:
        addresses_cache.update(pickle.load(f))
        return addresses_cache


def save_addresses_cache():
    with open(addresses_cache_file, "wb") as f:
        pickle.dump(addresses_cache, f)


def get_rows() -> Iterable:
    """Retrive every row from a CSV file provided by the french
    government under under 'Libre xx' licence which indexes every
    house price evaluation for the year 2019
    """
    with open("valeursfoncieres-2019.csv", newline="", encoding='utf-8') as csvfile:
        yield from csv.reader(csvfile, delimiter="|")


def get_coordinates(*args) -> tuple:
    """For given french addresses formatted parameters, we
    call the government API to retrieve the GPS position of the
    location

    We are using a pickled file base cache to avoid spamming the API
    """
    address_like = " ".join(args).strip().lower()

    if not addresses_cache.get(address_like):
        response = requests.get(addresses_base_url + address_like)
        addresses = json.loads(response.text)

        features = addresses["features"]
        if features:
            res = (
                features[0]["geometry"]["coordinates"][0],
                features[0]["geometry"]["coordinates"][1],
            )
        else:
            res = (0, 0)
        addresses_cache[address_like] = res

    return addresses_cache[address_like]


def create_distribution_heatmap(name: str, lats: list, lons: list):
    """Create a folonium distribution heatmap
    It plots a point for every couple of latitude and longitude given
    """
    url_base = "http://server.arcgisonline.com/ArcGIS/rest/services/"
    service = "NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}"
    tileset = url_base + service

    heatmap_map = folium.Map(
        location=[50, 10],
        zoom_start=2,
        control_scale=True,
        tiles=tileset,
        attr="USGS style",
    )
    data = [(lat, lon) for lat, lon in zip(lats, lons)]

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
    heatmap_map.save(name)


def create_markup_map(
    name: str, lats: list, lons: list, housing_types: tuple, prices: tuple
):
    """Test function to create nice Leaflet html files"""
    data = [(lat, lon) for lat, lon in zip(lats, lons)]

    map_ = folium.Map(
        location=[50, 10], zoom_start=2, control_scale=True, tiles="openstreetmap",
    )
    mcg = folium.plugins.MarkerCluster(control=False)
    map_.add_child(mcg)

    houses = folium.plugins.FeatureGroupSubGroup(mcg, 'houses')
    appartements = folium.plugins.FeatureGroupSubGroup(mcg, 'appartements')
    others = folium.plugins.FeatureGroupSubGroup(mcg, 'others')
    map_.add_child(houses)
    map_.add_child(appartements)
    map_.add_child(others)

    for i, d in enumerate(data):
        housing_type = housing_types[i]
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

        formatted_price = (
            f"{int(float(prices[i].replace(',', '.'))):,}".replace(",", "⠀")
            if prices[i]
            else "Undefined"
        )
        folium.Marker(
            [d[0], d[1]],
            popup=f"{housing_type} <b>{formatted_price}€</b>",
            tooltip=housing_types[i],
            icon=folium.Icon(color=color, icon=icon),
        ).add_to(context)

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
    map_.save(name)


if __name__ == "__main__":
    lats = []
    lons = []
    housing_types = []
    prices = []
    load_addresses_cache()
    rows = get_rows()
    # Avoiding header row
    next(rows)

    for row in rows:
        (
            code_service_ch,
            reference_document,
            articles_cgi_1,
            articles_cgi_2,
            articles_cgi_3,
            articles_cgi_4,
            articles_cgi_5,
            no_disposition,
            date_mutation,
            nature_mutation,
            valeur_fonciere,
            no_voie,
            b_t_q,
            type_de_voie,
            code_voie,
            voie,
            code_postal,
            commune,
            code_departement,
            code_commune,
            prefixe_de_section,
            section,
            no_plan,
            no_volume,
            premier_lot,
            surface_carrez_du_1er_lot,
            second_lot,
            surface_carrez_du_2eme_lot,
            troisieme_lot,
            surface_carrez_du_3eme_lot,
            quatrieme_lot,
            surface_carrez_du_4eme_lot,
            cinquieme_lot,
            surface_carrez_du_5eme_lot,
            nombre_de_lots,
            code_type_local,
            type_local,
            identifiant_local,
            surface_reelle_bati,
            nombre_pieces_principales,
            nature_culture,
            nature_culture_speciale,
            surface_terrain,
        ) = row

        x, y = get_coordinates(
            no_voie,
            type_de_voie,
            voie,
            code_postal,
            commune,
            code_departement,
            code_commune,
        )
        if x and y:
            lons.append(x)
            lats.append(y)
            housing_types.append(type_local)
            prices.append(valeur_fonciere)

        # break point
        if len(lats) > 1000:
            break

    create_distribution_heatmap(name="distribution_heatmap.html", lats=lats, lons=lons)
    create_markup_map(
        name="test_map1.html", lats=lats, lons=lons, housing_types=housing_types, prices=prices
    )
    save_addresses_cache()
