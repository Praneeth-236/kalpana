from adherence_tracker import calculate_adherence_score
from health_summary_api import generate_health_summary
from models import get_patient_state_row, get_recent_patient_answers, get_user


def _format_answer_history(rows, category):
    filtered = [r for r in rows if r["category"] == category]
    if not filtered:
        return "No recent data"

    values = [str(r["answer_value"]) for r in filtered[:10]]
    return ", ".join(values)


def _build_adherence_history(user_id):
    adherence = calculate_adherence_score(user_id)
    return f"Current adherence: {adherence['percentage']}% ({adherence['taken']}/{adherence['total']} doses)"


def generate_patient_summary(user_id):
    user = get_user(user_id)
    if not user:
        return "Patient summary unavailable: user not found."

    state = get_patient_state_row(user_id)
    trend = state["trend"] if state and state["trend"] else "stable"

    recent_answers = get_recent_patient_answers(user_id, limit=20)
    stress_history = _format_answer_history(recent_answers, "stress")
    energy_history = _format_answer_history(recent_answers, "energy")
    adherence_history = _build_adherence_history(user_id)

    return generate_health_summary(
        condition=user["condition"],
        stress_history=stress_history,
        energy_history=energy_history,
        adherence_history=adherence_history,
        trend=trend,
    )
