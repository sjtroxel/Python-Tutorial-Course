"""
Tests for server.py — the Flask routes.

Flask gives us a "test client": a fake browser that sends requests to
our app IN MEMORY, with no real server running and no real network.
client.get("/weather?city=London") returns a response object whose
.status_code and .data (the raw bytes of the HTML) we can assert on.

Just like in test_weather.py, we don't want real API calls. The routes
call get_current_weather(), so for the route tests we patch
"server.get_current_weather" — note it's patched where it's USED
(in server.py's namespace), not where it's defined. We feed it a fake
weather dict and check that the route renders the right template with
the right values.
"""
from unittest.mock import patch

import pytest

from server import app


@pytest.fixture
def client():
    # TESTING=True makes Flask propagate errors to us (useful below) and
    # is the standard switch for tests. The test_client() is our fake browser.
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# A realistic OpenWeather success payload, trimmed to the fields server.py reads.
FAKE_WEATHER = {
    "cod": 200,
    "name": "London",
    "weather": [{"description": "clear sky"}],
    "main": {"temp": 59.04, "feels_like": 57.31},
}


def test_index_route_renders_form(client):
    resp = client.get("/")
    assert resp.status_code == 200
    # The index template's heading. resp.data is bytes, so we compare to bytes (b"...").
    assert b"Get Weather Conditions" in resp.data


def test_index_alias_route(client):
    # server.py maps BOTH "/" and "/index" to the same view function.
    resp = client.get("/index")
    assert resp.status_code == 200
    assert b"Get Weather Conditions" in resp.data


@patch("server.get_current_weather")
def test_weather_success_renders_data(mock_weather, client):
    mock_weather.return_value = FAKE_WEATHER

    resp = client.get("/weather?city=London")

    assert resp.status_code == 200
    # Title: weather.html shows "{{ title }} Weather"
    assert b"London Weather" in resp.data
    # Status is .capitalize()'d ("clear sky" -> "Clear sky") and temp is
    # formatted to 1 decimal ("59.04" -> "59.0"); template joins them with " and ".
    assert b"Clear sky and 59.0" in resp.data
    # feels_like also formatted to 1 decimal.
    assert b"Feels like 57.3" in resp.data


@patch("server.get_current_weather")
def test_weather_passes_the_requested_city_through(mock_weather, client):
    mock_weather.return_value = FAKE_WEATHER

    client.get("/weather?city=Tokyo")

    # The route should have called get_current_weather with the city we asked for.
    mock_weather.assert_called_once_with("Tokyo")


@patch("server.get_current_weather")
def test_blank_city_defaults_to_kansas_city(mock_weather, client):
    mock_weather.return_value = FAKE_WEATHER

    # A whitespace-only city. server.py does `if not bool(city.strip())`,
    # so "   " is treated as empty and replaced with "Kansas City".
    client.get("/weather?city=%20%20%20")  # %20 = a space, URL-encoded

    mock_weather.assert_called_once_with("Kansas City")


@patch("server.get_current_weather")
def test_city_not_found_renders_error_page(mock_weather, client):
    # OpenWeather returns cod "404" (a string) for unknown cities.
    # server.py checks `if not weather_data['cod'] == 200`, so this branch
    # renders the city-not-found template.
    mock_weather.return_value = {"cod": "404", "message": "city not found"}

    resp = client.get("/weather?city=jibberish")

    assert resp.status_code == 200
    assert b"City Not Found" in resp.data


@patch("server.get_current_weather")
def test_missing_city_param_defaults_to_kansas_city(mock_weather, client):
    # Previously this was a bug: a MISSING ?city= param made request.args.get('city')
    # return None, and None.strip() crashed with AttributeError (500 error).
    # After the fix (request.args.get('city', '')), a missing param defaults to ''
    # and is handled by the same blank-check as a whitespace city -> "Kansas City".
    mock_weather.return_value = FAKE_WEATHER

    resp = client.get("/weather")  # no ?city=... at all

    assert resp.status_code == 200
    mock_weather.assert_called_once_with("Kansas City")
