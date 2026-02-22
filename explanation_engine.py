def generate_hospital_explanation(score_result):
    """Create human-readable recommendation reasons for a hospital."""
    components = score_result["components"]
    reasons = []

    if components["specialization_match"] >= 0.9:
        reasons.append("Strong specialization match")
    if components["doctor_experience_score"] >= 0.6:
        reasons.append("Experienced doctors")
    if components["financial_compatibility"] >= 0.9:
        reasons.append("Within your budget")
    if components["rating_score"] >= 0.85:
        reasons.append("Highly rated")
    if components["distance_score"] >= 0.9:
        reasons.append("Convenient location")

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
