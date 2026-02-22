from geolocation_service import distance_score_from_km, haversine_distance_km


def _calculate_distance_score(user_lat, user_lon, hospital_lat, hospital_lon):
    if None in (user_lat, user_lon, hospital_lat, hospital_lon):
        return 0.5
    distance_km = haversine_distance_km(user_lat, user_lon, hospital_lat, hospital_lon)
    return distance_score_from_km(distance_km)


def _calculate_specialty_match_score(user_condition, hospital_specialties):
    normalized_condition = str(user_condition).strip().lower()
    normalized_specialties = str(hospital_specialties).strip().lower()

    if normalized_condition == normalized_specialties:
        return 1.0
    if normalized_specialties == "general":
        return 0.65
    return 0.4


def _calculate_rating_score(hospital_rating):
    return min(1.0, max(0.0, float(hospital_rating) / 5.0))


def _calculate_emergency_capability_score(hospital):
    return 1.0 if int(hospital["emergency_capable"] or 0) == 1 else 0.0


def _calculate_doctor_availability_score(doctors):
    return 1.0 if doctors else 0.0


def calculate_hospital_score(
    user,
    hospital,
    doctors=None,
    user_lat=None,
    user_lon=None,
    hospital_lat=None,
    hospital_lon=None,
):
    """
    Multi-factor hospital score based on:
    - distance
    - specialty match
    - rating
    - emergency capability
    """
    distance_score = _calculate_distance_score(user_lat, user_lon, hospital_lat, hospital_lon)
    distance_km = None
    if None not in (user_lat, user_lon, hospital_lat, hospital_lon):
        distance_km = haversine_distance_km(user_lat, user_lon, hospital_lat, hospital_lon)
    hospital_specialties = hospital.get("specialties") or hospital.get("specialization") or "general"
    specialty_match_score = _calculate_specialty_match_score(user["condition"], hospital_specialties)
    rating_score = _calculate_rating_score(hospital["rating"])
    emergency_capability_score = _calculate_emergency_capability_score(hospital)
    doctor_availability_score = _calculate_doctor_availability_score(doctors or [])

    final_score = (
        0.30 * distance_score
        + 0.30 * specialty_match_score
        + 0.25 * rating_score
        + 0.15 * emergency_capability_score
    )

    return {
        "hospital_id": hospital["id"],
        "hospital_name": hospital["name"],
        "location": hospital["location"],
        "specialization": hospital.get("specialization") or hospital_specialties,
        "specialties": hospital_specialties,
        "rating": hospital["rating"],
        "avg_cost": hospital["avg_cost"],
        "emergency_capable": int(hospital["emergency_capable"] or 0),
        "source": hospital.get("source", "database"),
        "distance_km": round(distance_km, 2) if distance_km is not None else hospital.get("distance_km"),
        "score": round(final_score, 4),
        "score_components": {
            "distance": round(distance_score, 4),
            "specialization_match": round(specialty_match_score, 4),
            "emergency_capability": round(emergency_capability_score, 4),
            "doctor_availability": round(doctor_availability_score, 4),
            "rating": round(rating_score, 4),
        },
        "components": {
            "distance": round(distance_score, 4),
            "specialization_match": round(specialty_match_score, 4),
            "emergency_capability": round(emergency_capability_score, 4),
            "doctor_availability": round(doctor_availability_score, 4),
            "rating": round(rating_score, 4),
        },
    }


def rank_hospitals(user, hospitals, doctors_by_hospital):
    return rank_hospitals_with_location(
        user,
        hospitals,
        doctors_by_hospital,
        user_lat=None,
        user_lon=None,
        hospital_coords_by_id=None,
    )


def rank_hospitals_with_location(
    user,
    hospitals,
    doctors_by_hospital,
    user_lat,
    user_lon,
    hospital_coords_by_id,
):
    ranked = []
    hospital_coords_by_id = hospital_coords_by_id or {}
    for hospital in hospitals:
        doctors = doctors_by_hospital.get(hospital["id"], [])
        hospital_lat, hospital_lon = hospital_coords_by_id.get(hospital["id"], (None, None))
        ranked.append(
            calculate_hospital_score(
                user,
                hospital,
                doctors=doctors,
                user_lat=user_lat,
                user_lon=user_lon,
                hospital_lat=hospital_lat,
                hospital_lon=hospital_lon,
            )
        )
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked
