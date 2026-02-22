import os
import re

from google import genai


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _condition_instruction(condition):
    normalized = (condition or "general").strip().lower()

    if normalized == "neurology":
        return (
            "Condition-specific instruction: Generate neurological-specific questions "
            "focusing on cognitive fatigue, headaches, concentration, neurological "
            "function, and coordination. Do not use generic stress-only questions."
        )

    if normalized == "cardiology":
        return (
            "Condition-specific instruction: Focus on chest discomfort patterns, "
            "breathlessness, exertion tolerance, and stress-triggered cardiac symptoms."
        )

    if normalized == "diabetes":
        return (
            "Condition-specific instruction: Focus on energy dips, weakness, dizziness, "
            "hydration/thirst signals, and day-to-day glucose stability indicators."
        )

    return (
        "Condition-specific instruction: Keep questions aligned with the diagnosed "
        "condition and recent clinical trend changes."
    )


def get_condition_fallback_questions(condition):
    normalized = (condition or "general").strip().lower()

    condition_map = {
        "neurology": [
            "Have your headaches increased in frequency or intensity today?",
            "Did you notice more difficulty concentrating on simple tasks today?",
            "Have you experienced unusual imbalance or reduced coordination today?",
        ],
        "cardiology": [
            "Did you feel chest discomfort during stress or light activity today?",
            "Did you feel more shortness of breath than usual today?",
            "Did fatigue or palpitations limit your routine activities today?",
        ],
        "diabetes": [
            "Did you experience sudden weakness or shakiness today?",
            "Did stress make you feel dizzy or physically drained today?",
            "Was your energy level less stable than yesterday?",
        ],
        "general": [
            "Have symptoms worsened today?",
            "How is your energy level compared to yesterday?",
            "Do you feel more or less stressed today?",
        ],
    }

    return condition_map.get(normalized, condition_map["general"])


def _format_list_for_prompt(items, default="None"):
    if not items:
        return default
    return "\n".join(f"- {str(item).strip()}" for item in items if str(item).strip()) or default


def _parse_question_lines(text):
    questions = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^\s*(?:\d+[\.)]|[-*])\s*", "", line).strip()
        line = line.strip('"').strip()
        if line:
            questions.append(line)
    return questions


def generate_adaptive_questions(patient_data):
    condition = (patient_data.get("condition") or "general").strip().lower()
    stress_score = patient_data.get("stress_score")
    energy_score = patient_data.get("energy_score")
    adherence_score = patient_data.get("adherence_score")
    trend = patient_data.get("trend")
    risk_level = patient_data.get("risk_level")
    medication_list = patient_data.get("medication_list") or []
    adherence_history = patient_data.get("adherence_history") or []
    assessment_history = patient_data.get("assessment_history") or []
    health_summary = patient_data.get("health_summary") or "Not available"
    question_history = patient_data.get("question_history") or []

    condition_instruction = _condition_instruction(condition)

    prompt = f"""
You are an advanced clinical assessment AI for chronic-condition monitoring.

FULL PATIENT CLINICAL CONTEXT
Condition: {condition}
Stress score (0-100): {stress_score}
Energy score (0-100): {energy_score}
Adherence score (0-100): {adherence_score}
Trend: {trend}
Risk level: {risk_level}

Medication list:
{_format_list_for_prompt(medication_list)}

Adherence history:
{_format_list_for_prompt(adherence_history)}

Assessment history:
{_format_list_for_prompt(assessment_history)}

Health summary:
{health_summary}

Previously asked questions (DO NOT REPEAT):
{_format_list_for_prompt(question_history)}

{condition_instruction}

TASK:
Generate exactly 3 personalized, condition-specific adaptive questions for the next daily check-in.

STRICT RULES:
- Output exactly 3 lines, each line one question.
- No numbering, no bullets, no extra explanation.
- Do NOT repeat previous questions.
- Make questions clinically meaningful and tailored to this patient's condition + current risk/trend.
"""

    try:
        client = _get_client()
        if not client:
            raise ValueError("GEMINI_API_KEY is not configured")

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={"temperature": 0.9},
        )

        text = (response.text or "").strip()
        history_set = {
            str(h).strip().lower()
            for h in question_history
            if h and str(h).strip()
        }

        cleaned = []
        for question in _parse_question_lines(text):
            normalized = question.lower()
            if normalized in history_set:
                continue
            if normalized in {q.lower() for q in cleaned}:
                continue
            cleaned.append(question)

        fallback_questions = get_condition_fallback_questions(condition)
        fallback_iter = [
            q for q in fallback_questions if q.strip().lower() not in history_set
        ]
        for fallback_question in fallback_iter:
            if len(cleaned) >= 3:
                break
            if fallback_question.lower() not in {q.lower() for q in cleaned}:
                cleaned.append(fallback_question)

        while len(cleaned) < 3:
            cleaned.append(get_condition_fallback_questions(condition)[len(cleaned) % 3])

        return cleaned[:3]
    except Exception:
        return get_condition_fallback_questions(condition)[:3]
