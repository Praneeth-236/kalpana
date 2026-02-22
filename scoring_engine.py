from financial_engine import calculate_financial_compatibility


def _normalize_experience(doctors):
    if not doctors:
        return 0.0
    max_reasonable_experience = 20
    avg_experience = sum(d["experience_years"] for d in doctors) / len(doctors)
    return min(1.0, avg_experience / max_reasonable_experience)


def _calculate_distance_score(user_location, hospital_location):
    # Hackathon-friendly approximation:
    # same city = 1.0, different city = 0.5
    if str(user_location).strip().lower() == str(hospital_location).strip().lower():
        return 1.0
    return 0.5


def score_hospital(user, hospital, doctors):
    """
    Score formula:

    score =
    0.30 specialization_match +
    0.20 doctor_experience_score +
    0.15 distance_score +
    0.15 rating_score +
    0.20 financial_compatibility
    """
    specialization_match = (
        1.0
        if str(user["condition"]).strip().lower()
        == str(hospital["specialization"]).strip().lower()
        else 0.4
    )

    doctor_experience_score = _normalize_experience(doctors)
    distance_score = _calculate_distance_score(user["location"], hospital["location"])
    rating_score = min(1.0, float(hospital["rating"]) / 5.0)
    financial_compatibility = calculate_financial_compatibility(
        float(user["budget_preference"]), float(hospital["avg_cost"])
    )

    final_score = (
        0.30 * specialization_match
        + 0.20 * doctor_experience_score
        + 0.15 * distance_score
        + 0.15 * rating_score
        + 0.20 * financial_compatibility
    )

    return {
        "hospital_id": hospital["id"],
        "hospital_name": hospital["name"],
        "location": hospital["location"],
        "specialization": hospital["specialization"],
        "rating": hospital["rating"],
        "avg_cost": hospital["avg_cost"],
        "score": round(final_score, 4),
        "components": {
            "specialization_match": round(specialization_match, 4),
            "doctor_experience_score": round(doctor_experience_score, 4),
            "distance_score": round(distance_score, 4),
            "rating_score": round(rating_score, 4),
            "financial_compatibility": round(financial_compatibility, 4),
        },
    }


def rank_hospitals(user, hospitals, doctors_by_hospital):
    ranked = []
    for hospital in hospitals:
        doctors = doctors_by_hospital.get(hospital["id"], [])
        ranked.append(score_hospital(user, hospital, doctors))
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked
