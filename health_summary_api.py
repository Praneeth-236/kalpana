import os

from google import genai


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def generate_health_summary(condition, stress_history, energy_history, adherence_history, trend):
    prompt = f"""
You are a clinical health analysis AI.

Patient condition: {condition}

Stress history:
{stress_history}

Energy history:
{energy_history}

Adherence history:
{adherence_history}

Trend: {trend}

Generate a concise clinical summary.

Include:

- overall progression
- risk pattern
- clinical interpretation
- recommendation

Limit to 4 sentences.
"""

    client = _get_client()
    if not client:
        return "Health summary unavailable: GEMINI_API_KEY is not configured. Continue monitoring adherence, stress, and energy trends daily."

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        text = (response.text or "").strip()
        if not text:
            return "Clinical summary unavailable from AI response. Continue current monitoring and follow-up plan."
        return text
    except Exception:
        return "Clinical summary temporarily unavailable. Use current risk level, adherence score, and trend for immediate decisions."
