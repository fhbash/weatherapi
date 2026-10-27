from concurrent.futures import ThreadPoolExecutor, as_completed

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import WEATHER_SERVICES, WeatherReading

VALID_UNITS = frozenset({"celsius", "fahrenheit"})


def _parse_coordinates(params: dict) -> tuple[tuple[float, float] | None, list[str]]:
    errors: list[str] = []
    lat_raw = params.get("lat") or params.get("latitude")
    lon_raw = params.get("lon") or params.get("longitude")

    if lat_raw is None:
        errors.append("'lat' / 'latitude' is required")
    if lon_raw is None:
        errors.append("'lon' / 'longitude' is required")
    if errors:
        return None, errors

    lat = lon = None
    try:
        lat = float(lat_raw)
    except (ValueError, TypeError):
        errors.append("'lat' must be a number")

    try:
        lon = float(lon_raw)
    except (ValueError, TypeError):
        errors.append("'lon' must be a number")

    if errors:
        return None, errors

    if not -90 <= lat <= 90:
        errors.append("'lat' must be between -90 and 90")
    if not -180 <= lon <= 180:
        errors.append("'lon' must be between -180 and 180")

    if errors:
        return None, errors

    return (lat, lon), []


class TemperatureView(APIView):
    def get(self, request: Request) -> Response:
        params = request.query_params
        service_map = {s.name: s for s in WEATHER_SERVICES}

        coords, errors = _parse_coordinates(params)
        if errors:
            return Response({"error": "; ".join(errors)}, status=status.HTTP_400_BAD_REQUEST)
        lat, lon = coords

        unit = params.get("unit")
        if unit is not None and unit not in VALID_UNITS:
            return Response(
                {"error": f"'unit' must be one of: {', '.join(sorted(VALID_UNITS))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        services_raw = params.get("services")
        if services_raw is not None:
            names = list(dict.fromkeys(n.strip() for n in services_raw.split(",") if n.strip()))
            if not names:
                return Response(
                    {"error": "'services' must not be empty"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            invalid = [n for n in names if n not in service_map]
            if invalid:
                return Response(
                    {
                        "error": (
                            f"Unknown services: {', '.join(invalid)}. "
                            f"Valid: {', '.join(sorted(service_map))}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            selected = [service_map[n] for n in names]
        else:
            selected = list(WEATHER_SERVICES)

        readings: list[WeatherReading] = []
        failed: list[str] = []
        used: list[str] = []

        with ThreadPoolExecutor(max_workers=len(selected)) as executor:
            futures = {executor.submit(svc.fetch, lat, lon): svc.name for svc in selected}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    readings.append(future.result())
                    used.append(name)
                except Exception:
                    failed.append(name)

        if not readings:
            return Response(
                {"error": "All weather services failed"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        avg_c = round(sum(r.celsius for r in readings) / len(readings), 2)
        avg_f = round(sum(r.fahrenheit for r in readings) / len(readings), 2)

        temperature: dict[str, float] = {}
        if unit == "celsius":
            temperature["celsius"] = avg_c
        elif unit == "fahrenheit":
            temperature["fahrenheit"] = avg_f
        else:
            temperature["celsius"] = avg_c
            temperature["fahrenheit"] = avg_f

        return Response(
            {
                "temperature": temperature,
                "services_used": sorted(used),
                "services_failed": sorted(failed),
            }
        )
