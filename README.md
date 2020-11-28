
## To watch the maps
Go to the map folder and choose the one you are searching for. [→ Overview](#overview)

## To lauch and manipulate the project

Download the latest file from the [French government website](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres) and move it in the data folder.

Ensure you have python 3 or more running on your computer.

Next open a terminal and type:
```shell
pip install -r requirements.txt
python open_data.py
```

NB: we used the 2019 dataset that you can find [here](https://www.data.gouv.fr/fr/datasets/r/3004168d-bec4-44d9-a781-ef16f41856a2)

## The main goals

* Exploiting the file containing all of the real estate values recorded in the public French governement website
* Creating simple maps to easily understand and make a rought idea of what the dataset contains
* Have some fun using and modelizing with Python 3

## General workflow

We are using csv and pandas modules to load and handle more than 2 million record of real estate values.
The main file does not contains any exploitable coordinates but only raw address attributes.
To obtain the exact location, we are calling an external API which given the address in an appropriate format returns the
latitude and the longitude. Then we can deal with the location and place the point on a map created using the folium python module based over [Leaflet](https://leafletjs.com).

To avoid calling the external API to often we created a pickled address cache file mapping between requests and locations.


## Overview <a name="overview"></a>

###### Heat Map
![Heat map](https://github.com/s-rigaud/OpenData/raw/master/overview/heatmap.png)

###### Point Map
![Point map](https://github.com/s-rigaud/OpenData/raw/master/overview/pointmap.png)

###### Department Map
![Department map](https://github.com/s-rigaud/OpenData/raw/master/overview/department.png)

###### Region Map
![Region map](https://github.com/s-rigaud/OpenData/raw/master/overview/region.png)

## Sources

### Valeurs foncières

[Licence Ouverte / Open Licence version 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence)

https://www.data.gouv.fr/fr/datasets/5cc1b94a634f4165e96436c1/

Download from https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/

### French department/region mapping

Download and modified from  https://gist.github.com/gzurbach/b0ccdeda51ec2fe135d5

### Addresses API from French government

[Licence Ouverte / Open Licence version 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence)

Call on https://api-adresse.data.gouv.fr/search

See documentation : https://geo.api.gouv.fr/adresse & https://geo.api.gouv.fr/faq
