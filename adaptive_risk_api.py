import json
import os

from google import genai


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def parse_json_response(text):
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    parsed = json.loads(cleaned)
    risk_level = str(parsed.get("risk_level", "MODERATE")).upper()
    if risk_level not in {"LOW", "MODERATE", "HIGH"}:
        risk_level = "MODERATE"

    probability = int(round(float(parsed.get("risk_probability", 50))))
    probability = max(0, min(100, probability))

    return {
        "risk_level": risk_level,
        "risk_probability": probability,
        "reason": str(parsed.get("reason", "Risk estimated from patient state.")).strip(),
        "recommendation": str(
            parsed.get("recommendation", "Continue monitoring and follow clinical guidance.")
        ).strip(),
    }


def estimate_patient_risk(
    condition,
    stress_score,
    energy_score,
    adherence_score,
    trend,
    history,
):
    history_text = "\n".join(history) if history else "None"

    prompt = f"""
You are an advanced clinical triage AI.

Patient condition: {condition}
Stress score: {stress_score}
Energy score: {energy_score}
Adherence score: {adherence_score}
Trend: {trend}

Assessment history:
{history_text}

Analyze patient risk.

Return STRICT JSON format:

{{
  "risk_level": "LOW or MODERATE or HIGH",
  "risk_probability": number between 0 and 100,
  "reason": short explanation,
  "recommendation": short clinical recommendation
}}
"""

    client = _get_client()
    if not client:
        raise ValueError("GEMINI_API_KEY is not configured")

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
        config={"temperature": 0.3},
    )

    text = (response.text or "").strip()
    return parse_json_response(text)
