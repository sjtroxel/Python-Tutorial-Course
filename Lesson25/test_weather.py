"""
Tests for weather.py — specifically the get_current_weather() function.

The big idea here: get_current_weather() calls a REAL external API
(requests.get(...) hits openweathermap.org). We do NOT want our tests
making real network calls — they'd be slow, need a live API key, and
fail when the internet or the API is down. A test should check OUR code,
not someone else's server.

So we "mock" requests.get: we swap in a fake stand-in that returns
whatever we tell it to. Then we can ask: given a fake API response,
does our function behave correctly? And: did our function build the
right URL and call the API the way we expect?

@patch("weather.requests.get") replaces requests.get *as seen inside
weather.py* with a fake (a MagicMock) for the duration of one test.
That fake is handed to the test as the `mock_get` argument.
"""
from unittest.mock import patch

import weather


@patch("weather.requests.get")
def test_returns_the_parsed_json(mock_get):
    # Arrange: tell the fake what .json() should return when called.
    # (weather.py does `requests.get(url).json()`, so we set the
    #  return value of .json() on the fake response object.)
    mock_get.return_value.json.return_value = {"cod": 200, "name": "London"}

    # Act
    result = weather.get_current_weather("London")

    # Assert: the function should hand back exactly what .json() gave it.
    assert result == {"cod": 200, "name": "London"}


@patch("weather.requests.get")
def test_city_is_placed_into_the_request_url(mock_get):
    mock_get.return_value.json.return_value = {"cod": 200}

    weather.get_current_weather("London")

    # mock_get.call_args.args[0] = the first positional arg requests.get
    # was called with, i.e. the URL our function built.
    called_url = mock_get.call_args.args[0]
    assert "q=London" in called_url
    assert "units=imperial" in called_url
    assert called_url.startswith("https://api.openweathermap.org")


@patch("weather.requests.get")
def test_default_city_is_kansas_city(mock_get):
    # get_current_weather has a default arg: def get_current_weather(city="Kansas City")
    # Calling with no argument should use that default in the URL.
    mock_get.return_value.json.return_value = {"cod": 200}

    weather.get_current_weather()

    called_url = mock_get.call_args.args[0]
    assert "q=Kansas City" in called_url
