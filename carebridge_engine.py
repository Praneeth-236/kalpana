from adherence_tracker import calculate_adherence_score
from health_monitor import compute_health_stability
from models import get_answers_for_user, get_latest_health_log


def _calculate_health_percentage(user_id, adherence_ratio):
    latest_log = get_latest_health_log(user_id)
    if not latest_log:
        return 0.0

    summary = compute_health_stability(
        sleep_hours=latest_log["sleep_hours"],
        stress_level=latest_log["stress_level"],
        energy_level=latest_log["energy_level"],
        adherence_score=adherence_ratio,
    )
    return float(summary["health_percentage"])


def calculate_patient_risk(user_id):
    """
    Fetch adherence score, health score, and questionnaire answers,
    then return LOW / MODERATE / HIGH risk level.
    """
    adherence = calculate_adherence_score(user_id)
    adherence_percentage = float(adherence["percentage"])
    adherence_ratio = float(adherence["ratio"])

    health_percentage = _calculate_health_percentage(user_id, adherence_ratio)

    # Answers are fetched for remote monitoring context and audit trail.
    answers = get_answers_for_user(user_id)

    if health_percentage > 80 and adherence_percentage > 80:
        risk = "LOW"
    elif health_percentage > 60:
        risk = "MODERATE"
    else:
        risk = "HIGH"

    return {
        "risk": risk,
        "adherence_score": round(adherence_percentage, 2),
        "health_score": round(health_percentage, 2),
        "answer_count": len(answers),
    }


def generate_doctor_recommendation(risk):
    if risk == "LOW":
        return "Continue current treatment"
    if risk == "MODERATE":
        return "Schedule appointment soon"
    return "Immediate medical consultation required"
