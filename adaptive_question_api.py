import os

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


def generate_adaptive_questions(
    condition,
    stress_score,
    energy_score,
    trend,
    adherence_score,
    history,
):
    history_text = "\n".join(history) if history else "None"
    condition_instruction = _condition_instruction(condition)

    prompt = f"""
You are an advanced clinical assessment AI.

Patient condition: {condition}
Stress score: {stress_score}
Energy score: {energy_score}
Trend: {trend}
Adherence score: {adherence_score}

Previously asked questions:
{history_text}

{condition_instruction}

Generate exactly 3 NEW clinically relevant adaptive questions.

STRICT RULES:
- DO NOT repeat any previously asked questions
- Questions must be specific to condition and current declining areas
- Focus on stress, fatigue, neurological, or physical deterioration
- Each question must be unique
- Each question must be on a new line
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
        history_set = {h.strip().lower() for h in (history or []) if h and h.strip()}

        cleaned = []
        for line in text.split("\n"):
            question = line.strip("- ").strip()
            if not question:
                continue
            normalized = question.lower()
            if normalized in history_set:
                continue
            if normalized in {q.lower() for q in cleaned}:
                continue
            cleaned.append(question)

        final_questions = cleaned[:3]
        if not final_questions:
            return get_condition_fallback_questions(condition)

        return final_questions
    except Exception:
        return get_condition_fallback_questions(condition)
