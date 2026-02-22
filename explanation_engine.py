def generate_hospital_explanation(score_result):
    """Create human-readable recommendation reasons for a hospital."""
    components = score_result.get("score_components") or score_result.get("components") or {}
    reasons = []

    specialization_match = components.get(
        "specialization_match", components.get("specialty_match", 0.0)
    )
    doctor_experience = components.get("doctor_experience_score", 0.0)
    financial_compatibility = components.get("financial_compatibility", 0.0)
    rating_score = components.get("rating_score", components.get("rating", 0.0))
    distance_score = components.get("distance_score", components.get("distance", 0.0))
    emergency_capability = components.get("emergency_capability", 0.0)

    if specialization_match >= 0.9:
        reasons.append("Strong specialization match")
    if doctor_experience >= 0.6:
        reasons.append("Experienced doctors")
    if financial_compatibility >= 0.9:
        reasons.append("Within your budget")
    if rating_score >= 0.85:
        reasons.append("Highly rated")
    if distance_score >= 0.9:
        reasons.append("Convenient location")
    if emergency_capability >= 0.9:
        reasons.append("Strong emergency capability")

    if not reasons:
        reasons.append("Balanced option based on your profile")

    explanation_lines = ["This hospital is recommended because:"]
    explanation_lines.extend([f"- {reason}" for reason in reasons])
    return "\n".join(explanation_lines)


def generate_doctor_recommendation_explanation(risk, recommendation):
    lines = ["Doctor Recommendation Summary:"]
    lines.append(f"- Current risk level: {risk}")
    lines.append(f"- Suggested action: {recommendation}")

    if risk == "LOW":
        lines.append("- Continue medication adherence and daily monitoring")
    elif risk == "MODERATE":
        lines.append("- Book an appointment and review symptoms soon")
    else:
        lines.append("- Contact doctor or emergency services immediately")

    return "\n".join(lines)
