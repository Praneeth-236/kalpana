import json
from math import asin, cos, radians, sin, sqrt
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


_geo_cache = {}


def geocode_location(location_name):
    key = (location_name or "").strip().lower()
    if not key:
        return None

    if key in _geo_cache:
        return _geo_cache[key]

    url = (
        "https://nominatim.openstreetmap.org/search?"
        f"q={quote_plus(location_name)}&format=json&limit=1"
    )
    request = Request(url, headers={"User-Agent": "CareMatchAI/1.0"})

    try:
        with urlopen(request, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if payload:
                lat = float(payload[0]["lat"])
                lon = float(payload[0]["lon"])
                _geo_cache[key] = (lat, lon)
                return _geo_cache[key]
    except Exception:
        pass

    _geo_cache[key] = None
    return None


def haversine_distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)

    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return r * c


def distance_score_from_km(distance_km):
    if distance_km <= 2:
        return 1.0
    if distance_km <= 10:
        return 0.9
    if distance_km <= 25:
        return 0.75
    if distance_km <= 50:
        return 0.6
    return 0.4
