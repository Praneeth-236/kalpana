import json
from urllib.request import Request, urlopen

from geolocation_service import haversine_distance_km
from specialization_inference import infer_specialization_with_gemini


_OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]


def _display_specialization(value):
    normalized = str(value or "general").strip().lower()
    if normalized == "multispecialty":
        return "Multi Speciality"
    if normalized == "general":
        return "General Medicine"
    return normalized.replace("_", " ").title()


def _run_overpass_query(query, timeout_seconds=12):
    for endpoint in _OVERPASS_ENDPOINTS:
        request = Request(
            endpoint,
            data=query.encode("utf-8"),
            headers={
                "User-Agent": "CareMatchAI/1.0",
                "Content-Type": "text/plain; charset=utf-8",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, dict):
                    return payload
        except Exception:
            continue

    return {"elements": []}


def fetch_nearest_hospitals_overpass(user_lat, user_lon, radius_m=15000, limit=25, preferred_condition=None):
    payload = {"elements": []}
    for search_radius in [int(radius_m), int(radius_m * 2), int(radius_m * 3)]:
        query = f"""
        [out:json][timeout:20];
        (
          node["amenity"="hospital"](around:{search_radius},{user_lat},{user_lon});
          way["amenity"="hospital"](around:{search_radius},{user_lat},{user_lon});
          relation["amenity"="hospital"](around:{search_radius},{user_lat},{user_lon});
          node["healthcare"="hospital"](around:{search_radius},{user_lat},{user_lon});
          way["healthcare"="hospital"](around:{search_radius},{user_lat},{user_lon});
          relation["healthcare"="hospital"](around:{search_radius},{user_lat},{user_lon});
        );
        out center tags;
        """
        payload = _run_overpass_query(query)
        if payload.get("elements"):
            break

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

        emergency_capable = 1 if tags.get("emergency") == "yes" else 0
        distance_km = haversine_distance_km(float(user_lat), float(user_lon), float(lat), float(lon))

        hospitals.append(
            {
                "id": int(element.get("id", 0)) + 900000000,
                "name": name,
                "location": location_text,
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
    selected = hospitals[: int(limit)]

    for hospital in selected:
        specialization = infer_specialization_with_gemini(hospital["name"]) or "general"
        hospital["specialties"] = specialization
        hospital["specialization"] = specialization
        hospital["specialization_display"] = _display_specialization(specialization)

    return selected
