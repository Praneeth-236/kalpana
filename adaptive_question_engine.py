from datetime import datetime, timedelta

from adherence_tracker import calculate_adherence_score
from adaptive_question_api import generate_adaptive_questions
from adaptive_risk_api import estimate_patient_risk
from carebridge_engine import calculate_patient_risk
from models import (
    add_assessment_history,
    get_assessment_history_entries,
    get_assessment_history_questions,
    get_patient_state_row,
    get_question_bank_item,
    get_recent_patient_answers,
    get_user,
    list_question_bank,
    save_patient_answer,
    upsert_patient_state,
)


def _clamp_0_100(value):
    return max(0, min(100, int(round(value))))


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def get_patient_state(user_id):
    """
    Return patient state; initialize default when missing.
    """
    row = get_patient_state_row(user_id)
    if row:
        return {
            "user_id": row["user_id"],
            "stress_score": row["stress_score"],
            "energy_score": row["energy_score"],
            "trend": row["trend"],
            "last_updated": row["last_updated"],
            "last_assessment_at": row["last_assessment_at"],
            "next_assessment_due": row["next_assessment_due"],
            "risk_level": row["risk_level"],
            "risk_probability": row["risk_probability"],
            "risk_reason": row["risk_reason"],
            "recommendation": row["recommendation"],
        }

    default_state = {
        "user_id": user_id,
        "stress_score": 50,
        "energy_score": 50,
        "trend": "stable",
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "last_assessment_at": None,
        "next_assessment_due": None,
        "risk_level": None,
        "risk_probability": None,
        "risk_reason": None,
        "recommendation": None,
    }
    upsert_patient_state(
        user_id=user_id,
        stress_score=default_state["stress_score"],
        energy_score=default_state["energy_score"],
        trend=default_state["trend"],
        last_updated=default_state["last_updated"],
        last_assessment_at=default_state["last_assessment_at"],
        next_assessment_due=default_state["next_assessment_due"],
        risk_level=default_state["risk_level"],
        risk_probability=default_state["risk_probability"],
        risk_reason=default_state["risk_reason"],
        recommendation=default_state["recommendation"],
    )
    return default_state


def is_assessment_due(user_id):
    state = get_patient_state(user_id)
    next_due = _parse_datetime(state.get("next_assessment_due"))
    if not next_due:
        return True
    return datetime.now() >= next_due


def select_adaptive_questions(user_id):
    """
    Select 3-5 adaptive questions based on condition, state, previous answers, and trend.
    """
    user = get_user(user_id)
    if not user:
        return []

    condition = (user["condition"] or "general").strip().lower()
    state = get_patient_state(user_id)
    recent_answers = get_recent_patient_answers(user_id)

    stress_avg = 0
    energy_avg = 0
    stress_values = [a["answer_value"] for a in recent_answers if a["category"] == "stress"]
    energy_values = [a["answer_value"] for a in recent_answers if a["category"] == "energy"]
    if stress_values:
        stress_avg = sum(stress_values) / len(stress_values)
    if energy_values:
        energy_avg = sum(energy_values) / len(energy_values)

    condition_questions = list_question_bank(condition=condition)
    general_questions = list_question_bank(condition="general")

    candidate_map = {}

    def add_candidate(question, boost=0):
        qid = question["id"]
        base_score = int(question["weight"])
        score = base_score + boost
        if qid not in candidate_map or score > candidate_map[qid]["priority"]:
            candidate_map[qid] = {"question": question, "priority": score}

    for q in condition_questions:
        add_candidate(q, boost=6)

    for q in general_questions:
        add_candidate(q, boost=2)

    if state["stress_score"] > 60:
        for q in list_question_bank(condition=condition, category="stress"):
            add_candidate(q, boost=5)
        for q in list_question_bank(condition="general", category="stress"):
            add_candidate(q, boost=3)

    if state["energy_score"] < 50:
        for q in list_question_bank(condition=condition, category="energy"):
            add_candidate(q, boost=5)
        for q in list_question_bank(condition="general", category="energy"):
            add_candidate(q, boost=3)

    if state["trend"] == "declining":
        for item in candidate_map.values():
            if item["question"]["weight"] >= 7:
                item["priority"] += 4

    if stress_avg >= 4:
        for item in candidate_map.values():
            if item["question"]["category"] == "stress":
                item["priority"] += 2

    if energy_avg >= 4:
        for item in candidate_map.values():
            if item["question"]["category"] == "energy":
                item["priority"] += 2

    sorted_candidates = sorted(
        candidate_map.values(),
        key=lambda item: (item["priority"], item["question"]["weight"]),
        reverse=True,
    )

    selected = [item["question"] for item in sorted_candidates[:5]]

    # Ensure at least 3 questions by filling from general bank if needed.
    if len(selected) < 3:
        selected_ids = {q["id"] for q in selected}
        for q in general_questions:
            if q["id"] not in selected_ids:
                selected.append(q)
                selected_ids.add(q["id"])
            if len(selected) >= 3:
                break

    return selected[:5]


def _infer_category(question_text):
    normalized = (question_text or "").lower()
    energy_keywords = ["fatigue", "weak", "energy", "tired", "exhausted"]
    if any(word in normalized for word in energy_keywords):
        return "energy"
    return "stress"


def _normalize_db_questions(questions):
    normalized = []
    for q in questions:
        normalized.append(
            {
                "id": str(q["id"]),
                "question_text": q["question_text"],
                "category": q["category"],
                "weight": int(q["weight"]),
                "source": "db",
            }
        )
    return normalized


def get_question_history(user_id, limit=10):
    return get_assessment_history_questions(user_id, limit=limit)


def get_fallback_questions():
    return [
        "Have symptoms worsened today?",
        "How is your energy level compared to yesterday?",
        "Do you feel more or less stressed today?",
    ]


def _normalize_fallback_monitoring_questions():
    normalized = []
    for idx, question_text in enumerate(get_fallback_questions(), start=1):
        normalized.append(
            {
                "id": f"fallback_{idx}",
                "question_text": question_text,
                "category": _infer_category(question_text),
                "weight": 6,
                "source": "fallback",
            }
        )
    return normalized


def get_db_fallback_questions(user_id, history=None):
    history_set = {
        q.strip().lower() for q in (history or []) if q and str(q).strip()
    }

    selected = _normalize_db_questions(select_adaptive_questions(user_id))
    filtered = [
        q for q in selected if q["question_text"].strip().lower() not in history_set
    ]

    if len(filtered) >= 3:
        return filtered[:5]

    user = get_user(user_id)
    condition = (user["condition"] or "general").strip().lower() if user else "general"
    extra_pool = list_question_bank(condition=condition) + list_question_bank(condition="general")

    used = {q["question_text"].strip().lower() for q in filtered}
    for row in extra_pool:
        text = row["question_text"].strip().lower()
        if text in history_set or text in used:
            continue
        filtered.append(
            {
                "id": str(row["id"]),
                "question_text": row["question_text"],
                "category": row["category"],
                "weight": int(row["weight"]),
                "source": "db",
            }
        )
        used.add(text)
        if len(filtered) >= 5:
            break

    return filtered if filtered else _normalize_fallback_monitoring_questions()


def get_adaptive_questions(user_id):
    user = get_user(user_id)
    if not user:
        return _normalize_fallback_monitoring_questions()

    if not is_assessment_due(user_id):
        return "Next assessment available tomorrow"

    state = get_patient_state(user_id)
    adherence = calculate_adherence_score(user_id)
    history = get_question_history(user_id, limit=10)

    try:
        ai_questions = generate_adaptive_questions(
            condition=user["condition"],
            stress_score=state["stress_score"],
            energy_score=state["energy_score"],
            trend=state["trend"],
            adherence_score=adherence["percentage"],
            history=history,
        )

        cleaned = [q for q in ai_questions if q and q.strip()]
        if cleaned:
            normalized = []
            history_set = {q.strip().lower() for q in history if q and q.strip()}
            for idx, question_text in enumerate(cleaned, start=1):
                normalized_text = question_text.strip().lower()
                if normalized_text in history_set:
                    continue
                normalized.append(
                    {
                        "id": f"ai_{idx}",
                        "question_text": question_text,
                        "category": _infer_category(question_text),
                        "weight": 6,
                        "source": "ai",
                    }
                )
            if normalized:
                return normalized[:3]
    except Exception:
        pass

    db_fallback = get_db_fallback_questions(user_id, history=history)
    if db_fallback:
        return db_fallback

    return _normalize_fallback_monitoring_questions()


def update_patient_state(user_id, answers, question_context=None):
    """
    Update stress/energy scores and trend based on submitted adaptive answers.
    """
    state = get_patient_state(user_id)
    prev_stress = float(state["stress_score"])
    prev_energy = float(state["energy_score"])

    new_stress = prev_stress
    new_energy = prev_energy

    timestamp = datetime.now().isoformat(timespec="seconds")
    next_due_timestamp = (datetime.now() + timedelta(days=1)).isoformat(timespec="seconds")

    context = question_context or {}

    for question_key, answer_value in answers.items():
        value = int(answer_value)

        question = None
        if str(question_key).isdigit():
            question = get_question_bank_item(int(question_key))

        if question:
            weight = int(question["weight"])
            category = question["category"]
            question_text = question["question_text"]
            save_patient_answer(
                user_id=user_id,
                question_id=int(question_key),
                answer_value=value,
                timestamp=timestamp,
            )
        else:
            metadata = context.get(str(question_key), {})
            weight = int(metadata.get("weight", 6))
            category = metadata.get("category", "stress")
            question_text = metadata.get("question_text", "Adaptive assessment question")

        add_assessment_history(
            user_id=user_id,
            question=question_text,
            answer=value,
        )

        weight_factor = float(weight) / 10.0

        if category == "stress":
            new_stress += value * weight_factor
        elif category == "energy":
            new_energy -= value * weight_factor

    new_stress = _clamp_0_100(new_stress)
    new_energy = _clamp_0_100(new_energy)

    if new_stress > prev_stress and new_energy < prev_energy:
        trend = "declining"
    elif new_stress < prev_stress and new_energy > prev_energy:
        trend = "improving"
    else:
        trend = "stable"

    user = get_user(user_id)
    adherence = calculate_adherence_score(user_id)
    history_entries = get_assessment_history_entries(user_id, limit=10)

    try:
        risk_result = estimate_patient_risk(
            condition=(user["condition"] if user else "general"),
            stress_score=new_stress,
            energy_score=new_energy,
            adherence_score=adherence["percentage"],
            trend=trend,
            history=history_entries,
        )
    except Exception:
        fallback = calculate_patient_risk(user_id)
        fallback_level = fallback["risk"]
        fallback_probability = {
            "LOW": 25,
            "MODERATE": 60,
            "HIGH": 85,
        }.get(fallback_level, 60)
        fallback_recommendation = {
            "LOW": "Continue current treatment",
            "MODERATE": "Schedule appointment soon",
            "HIGH": "Immediate medical consultation required",
        }.get(fallback_level, "Schedule appointment soon")
        risk_result = {
            "risk_level": fallback_level,
            "risk_probability": fallback_probability,
            "reason": "Fallback rule-based risk from adherence and health stability.",
            "recommendation": fallback_recommendation,
        }

    upsert_patient_state(
        user_id=user_id,
        stress_score=new_stress,
        energy_score=new_energy,
        trend=trend,
        last_updated=timestamp,
        last_assessment_at=timestamp,
        next_assessment_due=next_due_timestamp,
        risk_level=risk_result["risk_level"],
        risk_probability=risk_result["risk_probability"],
        risk_reason=risk_result["reason"],
        recommendation=risk_result["recommendation"],
    )

    return {
        "user_id": user_id,
        "stress_score": new_stress,
        "energy_score": new_energy,
        "trend": trend,
        "last_updated": timestamp,
        "last_assessment_at": timestamp,
        "next_assessment_due": next_due_timestamp,
        "risk_level": risk_result["risk_level"],
        "risk_probability": risk_result["risk_probability"],
        "risk_reason": risk_result["reason"],
        "recommendation": risk_result["recommendation"],
    }
