from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from weather.services import WeatherReading, WeatherService

BASE = "/api/temperature/"

R1 = WeatherReading(celsius=20.0, fahrenheit=68.0)
R2 = WeatherReading(celsius=22.0, fahrenheit=71.6)


def ok_service(name: str, reading: WeatherReading) -> WeatherService:
    return WeatherService(name=name, fetch=lambda lat, lon: reading)


def failing_service(name: str) -> WeatherService:
    def _fail(lat, lon):
        raise ConnectionError("service down")

    return WeatherService(name=name, fetch=_fail)


TWO_SERVICES = [ok_service("accuweather", R1), ok_service("noaa", R2)]


class CoordinateValidationTests(APITestCase):
    def get(self, params):
        return self.client.get(BASE, params)

    def test_missing_lat_returns_400(self):
        r = self.get({"lon": 33})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("lat", r.data["error"])

    def test_missing_lon_returns_400(self):
        r = self.get({"lat": 44})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("lon", r.data["error"])

    def test_missing_both_returns_400(self):
        r = self.get({})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_numeric_lat_returns_400(self):
        r = self.get({"lat": "abc", "lon": 33})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_numeric_lon_returns_400(self):
        r = self.get({"lat": 44, "lon": "xyz"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lat_above_90_returns_400(self):
        r = self.get({"lat": 90.1, "lon": 0})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lat_below_minus_90_returns_400(self):
        r = self.get({"lat": -90.1, "lon": 0})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lon_above_180_returns_400(self):
        r = self.get({"lat": 0, "lon": 180.1})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lon_below_minus_180_returns_400(self):
        r = self.get({"lat": 0, "lon": -180.1})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("weather.views.WEATHER_SERVICES", TWO_SERVICES)
    def test_boundary_lat_90_is_valid(self):
        r = self.get({"lat": 90, "lon": 0})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    @patch("weather.views.WEATHER_SERVICES", TWO_SERVICES)
    def test_boundary_lat_minus_90_is_valid(self):
        r = self.get({"lat": -90, "lon": 0})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    @patch("weather.views.WEATHER_SERVICES", TWO_SERVICES)
    def test_boundary_lon_180_is_valid(self):
        r = self.get({"lat": 0, "lon": 180})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    @patch("weather.views.WEATHER_SERVICES", TWO_SERVICES)
    def test_boundary_lon_minus_180_is_valid(self):
        r = self.get({"lat": 0, "lon": -180})
        self.assertEqual(r.status_code, status.HTTP_200_OK)


class UnitValidationTests(APITestCase):
    def get(self, params):
        return self.client.get(BASE, params)

    def test_invalid_unit_returns_400(self):
        r = self.get({"lat": 44, "lon": 33, "unit": "kelvin"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unit", r.data["error"])

    def test_unit_case_sensitive(self):
        r = self.get({"lat": 44, "lon": 33, "unit": "Celsius"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


class ServiceValidationTests(APITestCase):
    def get(self, params):
        return self.client.get(BASE, params)

    def test_unknown_service_returns_400(self):
        r = self.get({"lat": 44, "lon": 33, "services": "accuweather,bogus"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("bogus", r.data["error"])

    def test_empty_services_param_returns_400(self):
        r = self.get({"lat": 44, "lon": 33, "services": ""})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_whitespace_only_services_returns_400(self):
        r = self.get({"lat": 44, "lon": 33, "services": "  , , "})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


class TemperatureResponseTests(APITestCase):
    def get(self, params):
        return self.client.get(BASE, params)

    @patch("weather.views.WEATHER_SERVICES", TWO_SERVICES)
    def test_no_unit_returns_both(self):
        r = self.get({"lat": 44, "lon": 33})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("celsius", r.data["temperature"])
        self.assertIn("fahrenheit", r.data["temperature"])

    @patch("weather.views.WEATHER_SERVICES", TWO_SERVICES)
    def test_unit_celsius_omits_fahrenheit(self):
        r = self.get({"lat": 44, "lon": 33, "unit": "celsius"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("celsius", r.data["temperature"])
        self.assertNotIn("fahrenheit", r.data["temperature"])

    @patch("weather.views.WEATHER_SERVICES", TWO_SERVICES)
    def test_unit_fahrenheit_omits_celsius(self):
        r = self.get({"lat": 44, "lon": 33, "unit": "fahrenheit"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("fahrenheit", r.data["temperature"])
        self.assertNotIn("celsius", r.data["temperature"])

    @patch("weather.views.WEATHER_SERVICES", TWO_SERVICES)
    def test_averages_across_services(self):
        r = self.get({"lat": 44, "lon": 33})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["temperature"]["celsius"], round((20.0 + 22.0) / 2, 2))
        self.assertEqual(r.data["temperature"]["fahrenheit"], round((68.0 + 71.6) / 2, 2))

    @patch("weather.views.WEATHER_SERVICES", TWO_SERVICES)
    def test_response_includes_services_used_and_failed(self):
        r = self.get({"lat": 44, "lon": 33})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("services_used", r.data)
        self.assertIn("services_failed", r.data)
        self.assertEqual(r.data["services_failed"], [])

    @patch("weather.views.WEATHER_SERVICES", TWO_SERVICES)
    def test_single_service_selection(self):
        r = self.get({"lat": 44, "lon": 33, "services": "accuweather"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["services_used"], ["accuweather"])
        self.assertEqual(r.data["temperature"]["celsius"], 20.0)

    @patch("weather.views.WEATHER_SERVICES", TWO_SERVICES)
    def test_duplicate_service_names_deduplicated(self):
        r = self.get({"lat": 44, "lon": 33, "services": "accuweather,accuweather"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["temperature"]["celsius"], 20.0)

    def test_partial_failure_averages_remaining(self):
        services = [ok_service("accuweather", R1), failing_service("noaa")]
        with patch("weather.views.WEATHER_SERVICES", services):
            r = self.get({"lat": 44, "lon": 33})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["temperature"]["celsius"], 20.0)
        self.assertIn("accuweather", r.data["services_used"])
        self.assertIn("noaa", r.data["services_failed"])

    def test_all_services_fail_returns_503(self):
        services = [failing_service("accuweather"), failing_service("noaa")]
        with patch("weather.views.WEATHER_SERVICES", services):
            r = self.get({"lat": 44, "lon": 33})
        self.assertEqual(r.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("error", r.data)
