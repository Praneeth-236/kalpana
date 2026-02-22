from models import list_emergency_hospitals
from scoring_engine import _calculate_distance_score


def recommend_emergency_hospital(user_location):
    """
    Emergency scoring formula:
    score =
    0.40 distance +
    0.30 emergency_capable +
    0.20 ambulance_available +
    0.10 rating
    """
    hospitals = list_emergency_hospitals()
    if not hospitals:
        return None

    ranked = []
    for hospital in hospitals:
        distance_score = _calculate_distance_score(user_location, hospital["location"])
        emergency_capable_score = 1.0 if hospital["emergency_capable"] else 0.0
        ambulance_available_score = 1.0 if hospital["ambulance_available"] else 0.0
        rating_score = min(1.0, float(hospital["rating"]) / 5.0)

        score = (
            0.40 * distance_score
            + 0.30 * emergency_capable_score
            + 0.20 * ambulance_available_score
            + 0.10 * rating_score
        )

        ranked.append(
            {
                "hospital_id": hospital["id"],
                "name": hospital["name"],
                "location": hospital["location"],
                "rating": hospital["rating"],
                "ambulance_number": hospital["ambulance_number"] or "Not Available",
                "ambulance_available": bool(hospital["ambulance_available"]),
                "score": round(score, 4),
            }
        )

    ranked.sort(key=lambda h: h["score"], reverse=True)
    return ranked[0]
