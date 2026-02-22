def _clamp_0_1(value):
    return max(0.0, min(1.0, value))


def compute_health_stability(sleep_hours, stress_level, energy_level, adherence_score):
    """
    Inputs:
    - sleep_hours (0-12 expected)
    - stress_level (1-10, lower is better)
    - energy_level (1-10)
    - adherence_score (0-1)

    health_score =
    0.30 adherence_score +
    0.25 sleep_score +
    0.20 stress_score +
    0.15 energy_score +
    0.10 activity_score

    activity_score is estimated from sleep and energy as a proxy,
    since explicit activity input is not part of required form inputs.
    """
    sleep_score = _clamp_0_1(float(sleep_hours) / 8.0)
    stress_score = _clamp_0_1((10.0 - float(stress_level)) / 9.0)
    energy_score = _clamp_0_1((float(energy_level) - 1.0) / 9.0)
    adherence_component = _clamp_0_1(float(adherence_score))

    activity_score = _clamp_0_1((sleep_score + energy_score) / 2.0)

    health_score = (
        0.30 * adherence_component
        + 0.25 * sleep_score
        + 0.20 * stress_score
        + 0.15 * energy_score
        + 0.10 * activity_score
    )

    if health_score >= 0.75:
        status = "Stable"
    elif health_score >= 0.5:
        status = "Moderate Risk"
    else:
        status = "High Risk"

    return {
        "health_score": round(health_score, 4),
        "health_percentage": round(health_score * 100, 2),
        "status": status,
        "components": {
            "sleep_score": round(sleep_score, 4),
            "stress_score": round(stress_score, 4),
            "energy_score": round(energy_score, 4),
            "activity_score": round(activity_score, 4),
            "adherence_score": round(adherence_component, 4),
        },
    }
