from unittest.mock import MagicMock, patch

from django.test import TestCase

from weather.services import (
    WeatherReading,
    fetch_accuweather,
    fetch_noaa,
    fetch_weatherdotcom,
)

ACCU_RESPONSE = {
    "simpleforecast": {
        "forecastday": [{"current": {"fahrenheit": "68", "celsius": "20"}}]
    }
}

NOAA_RESPONSE = {"today": {"current": {"fahrenheit": "55", "celsius": "12"}}}

WDC_RESPONSE = {
    "query": {"results": {"channel": {"condition": {"temp": "68"}}}}
}


def mock_response(json_data: dict) -> MagicMock:
    m = MagicMock()
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    return m


class FetchAccuweatherTests(TestCase):
    @patch("weather.services.requests.get")
    def test_returns_correct_reading(self, mock_get):
        mock_get.return_value = mock_response(ACCU_RESPONSE)
        reading = fetch_accuweather(44.0, 33.0)
        self.assertEqual(reading.celsius, 20.0)
        self.assertEqual(reading.fahrenheit, 68.0)

    @patch("weather.services.requests.get")
    def test_passes_lat_lon_as_separate_params(self, mock_get):
        mock_get.return_value = mock_response(ACCU_RESPONSE)
        fetch_accuweather(44.0, 33.0)
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["latitude"], 44.0)
        self.assertEqual(kwargs["params"]["longitude"], 33.0)

    @patch("weather.services.requests.get")
    def test_uses_configured_timeout(self, mock_get):
        mock_get.return_value = mock_response(ACCU_RESPONSE)
        fetch_accuweather(44.0, 33.0)
        _, kwargs = mock_get.call_args
        self.assertIn("timeout", kwargs)

    @patch("weather.services.requests.get")
    def test_raises_on_http_error(self, mock_get):
        mock_get.return_value = mock_response({})
        mock_get.return_value.raise_for_status.side_effect = Exception("HTTP 500")
        with self.assertRaises(Exception):
            fetch_accuweather(44.0, 33.0)


class FetchNoaaTests(TestCase):
    @patch("weather.services.requests.get")
    def test_returns_correct_reading(self, mock_get):
        mock_get.return_value = mock_response(NOAA_RESPONSE)
        reading = fetch_noaa(44.0, 33.0)
        self.assertEqual(reading.celsius, 12.0)
        self.assertEqual(reading.fahrenheit, 55.0)

    @patch("weather.services.requests.get")
    def test_formats_latlon_as_comma_separated(self, mock_get):
        mock_get.return_value = mock_response(NOAA_RESPONSE)
        fetch_noaa(44.0, 33.0)
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["latlon"], "44.0,33.0")

    @patch("weather.services.requests.get")
    def test_raises_on_http_error(self, mock_get):
        mock_get.return_value = mock_response({})
        mock_get.return_value.raise_for_status.side_effect = Exception("HTTP 500")
        with self.assertRaises(Exception):
            fetch_noaa(44.0, 33.0)


class FetchWeatherdotcomTests(TestCase):
    @patch("weather.services.requests.post")
    def test_returns_fahrenheit_and_derived_celsius(self, mock_post):
        mock_post.return_value = mock_response(WDC_RESPONSE)
        reading = fetch_weatherdotcom(44.0, 33.0)
        self.assertEqual(reading.fahrenheit, 68.0)
        expected_c = round((68.0 - 32) * 5 / 9, 2)
        self.assertAlmostEqual(reading.celsius, expected_c, places=2)

    @patch("weather.services.requests.post")
    def test_sends_json_body_with_lat_lon(self, mock_post):
        mock_post.return_value = mock_response(WDC_RESPONSE)
        fetch_weatherdotcom(44.0, 33.0)
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"], {"lat": 44.0, "lon": 33.0})

    @patch("weather.services.requests.post")
    def test_raises_on_http_error(self, mock_post):
        mock_post.return_value = mock_response({})
        mock_post.return_value.raise_for_status.side_effect = Exception("HTTP 500")
        with self.assertRaises(Exception):
            fetch_weatherdotcom(44.0, 33.0)
