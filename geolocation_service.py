import json
from math import asin, cos, radians, sin, sqrt
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


_geo_cache = {}


_SPECIALTY_KEYWORDS = {
    "cardiology": ["cardio", "heart", "cardiac"],
    "neurology": ["neuro", "brain", "stroke"],
    "orthopedics": ["ortho", "bone", "joint", "spine"],
    "oncology": ["onco", "cancer", "tumor"],
    "pediatrics": ["pediatric", "children", "child"],
    "gynecology": ["gyn", "obstetric", "maternity", "women"],
    "pulmonology": ["pulmo", "lung", "respiratory"],
    "nephrology": ["nephro", "kidney", "renal"],
    "dermatology": ["derma", "skin"],
    "psychiatry": ["psychi", "mental"],
}


def _normalize_specialty_label(value):
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _is_generic_specialty(value):
    normalized = _normalize_specialty_label(value)
    generic_tokens = {
        "",
        "general",
        "hospital",
        "medicine",
        "multi_speciality",
        "multispeciality",
        "multispecialty",
        "multi_specialty",
        "speciality",
        "specialty",
    }
    return normalized in generic_tokens


def _normalize_condition_category(value):
    normalized = _normalize_specialty_label(value)
    aliases = {
        "cardiac": "cardiology",
        "heart": "cardiology",
        "neuro": "neurology",
        "ortho": "orthopedics",
        "oncology_care": "oncology",
        "pediatric": "pediatrics",
        "gynaecology": "gynecology",
        "obs_gyn": "gynecology",
        "respiratory": "pulmonology",
        "renal": "nephrology",
    }
    if normalized in aliases:
        return aliases[normalized]
    return normalized


def _infer_specialization(tags, name, preferred_condition=None):
    candidate_fields = [
        tags.get("healthcare:speciality"),
        tags.get("speciality"),
        tags.get("specialty"),
        tags.get("department"),
        tags.get("healthcare"),
    ]

    for raw in candidate_fields:
        if not raw:
            continue
        for part in str(raw).split(";"):
            value = _normalize_specialty_label(part)
            if not _is_generic_specialty(value):
                return _normalize_condition_category(value)

    name_text = str(name or "").strip().lower()
    for canonical, keywords in _SPECIALTY_KEYWORDS.items():
        if any(keyword in name_text for keyword in keywords):
            return canonical

    preferred = _normalize_condition_category(preferred_condition)
    if preferred and not _is_generic_specialty(preferred):
        return preferred

    return "general_medicine"


def _display_specialization(value):
    normalized = _normalize_specialty_label(value)
    if normalized in {"general", "general_medicine"}:
        return "General Medicine"
    return normalized.replace("_", " ").title()


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


def fetch_nearest_hospitals_overpass(
    user_lat,
    user_lon,
    radius_m=15000,
    limit=25,
    preferred_condition=None,
):
    query = f"""
    [out:json][timeout:20];
    (
      node["amenity"="hospital"](around:{int(radius_m)},{user_lat},{user_lon});
      way["amenity"="hospital"](around:{int(radius_m)},{user_lat},{user_lon});
      relation["amenity"="hospital"](around:{int(radius_m)},{user_lat},{user_lon});
    );
    out center tags;
    """

    request = Request(
        "https://overpass-api.de/api/interpreter",
        data=query.encode("utf-8"),
        headers={
            "User-Agent": "CareMatchAI/1.0",
            "Content-Type": "text/plain; charset=utf-8",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []

    hospitals = []
    for element in payload.get("elements", []):
        tags = element.get("tags", {})

        lat = element.get("lat")
        lon = element.get("lon")
        if lat is None or lon is None:
            center = element.get("center", {})
            lat = center.get("lat")
            lon = center.get("lon")
        if lat is None or lon is None:
            continue

        name = tags.get("name") or "Nearby Hospital"
        address = ", ".join(
            [
                part
                for part in [
                    tags.get("addr:street"),
                    tags.get("addr:city"),
                    tags.get("addr:state"),
                ]
                if part
            ]
        )
        location_text = address or "Near your location"

        speciality_text = _infer_specialization(tags, name, preferred_condition=preferred_condition)

        emergency_capable = 1 if tags.get("emergency") == "yes" else 0
        distance_km = haversine_distance_km(float(user_lat), float(user_lon), float(lat), float(lon))

        hospitals.append(
            {
                "id": int(element.get("id", 0)) + 900000000,
                "name": name,
                "location": location_text,
                "specialization": speciality_text,
                "specialization_display": _display_specialization(speciality_text),
                "rating": 4.0,
                "avg_cost": 3000,
                "emergency_capable": emergency_capable,
                "latitude": float(lat),
                "longitude": float(lon),
                "distance_km": round(distance_km, 2),
                "source": "overpass",
            }
        )

    hospitals.sort(key=lambda row: row["distance_km"])
    return hospitals[: int(limit)]
