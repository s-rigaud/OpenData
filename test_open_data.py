from open_data import load_addresses_cache, save_addresses_cache, get_coordinates, addresses_cache


def test_get_coordinates_cache():
    assert not addresses_cache
    addresses_cache["rue des coquelicots"] = (44, 55)
    save_addresses_cache()
    addresses = load_addresses_cache()
    assert addresses["rue des coquelicots"] == (44, 55)

test_get_coordinates_cache()