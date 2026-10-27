from dataclasses import dataclass
from typing import Callable

import requests
from django.conf import settings


@dataclass
class WeatherReading:
    celsius: float
    fahrenheit: float


@dataclass
class WeatherService:
    name: str
    fetch: Callable[[float, float], "WeatherReading"]


def fetch_accuweather(lat: float, lon: float) -> WeatherReading:
    response = requests.get(
        f"{settings.WEATHER_SERVICE_BASE_URL}/accuweather",
        params={"latitude": lat, "longitude": lon},
        timeout=settings.WEATHER_SERVICE_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    current = data["simpleforecast"]["forecastday"][0]["current"]
    return WeatherReading(
        celsius=float(current["celsius"]),
        fahrenheit=float(current["fahrenheit"]),
    )


def fetch_noaa(lat: float, lon: float) -> WeatherReading:
    response = requests.get(
        f"{settings.WEATHER_SERVICE_BASE_URL}/noaa",
        params={"latlon": f"{lat},{lon}"},
        timeout=settings.WEATHER_SERVICE_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    current = data["today"]["current"]
    return WeatherReading(
        celsius=float(current["celsius"]),
        fahrenheit=float(current["fahrenheit"]),
    )


def fetch_weatherdotcom(lat: float, lon: float) -> WeatherReading:
    response = requests.post(
        f"{settings.WEATHER_SERVICE_BASE_URL}/weatherdotcom",
        json={"lat": lat, "lon": lon},
        timeout=settings.WEATHER_SERVICE_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    temp_f = float(data["query"]["results"]["channel"]["condition"]["temp"])
    temp_c = round((temp_f - 32) * 5 / 9, 2)
    return WeatherReading(celsius=temp_c, fahrenheit=temp_f)


WEATHER_SERVICES: list[WeatherService] = [
    WeatherService(name="accuweather", fetch=fetch_accuweather),
    WeatherService(name="noaa", fetch=fetch_noaa),
    WeatherService(name="weatherdotcom", fetch=fetch_weatherdotcom),
]
