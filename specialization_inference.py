import os

from google import genai


_ALLOWED_SPECIALTIES = {
    "general",
    "cardiology",
    "neurology",
    "orthopedics",
    "oncology",
    "psychiatry",
    "pediatrics",
    "multispecialty",
}

_specialization_cache = {}


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _normalize_specialty(value):
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "multi_specialty": "multispecialty",
        "multi_speciality": "multispecialty",
        "orthopaedics": "orthopedics",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in _ALLOWED_SPECIALTIES:
        return "general"
    return normalized


def infer_specialization_with_gemini(hospital_name):
    cache_key = (hospital_name or "").strip().lower()
    if not cache_key:
        return "general"

    if cache_key in _specialization_cache:
        return _specialization_cache[cache_key]

    prompt = f"""
Classify the hospital into exactly one specialization from this strict list:
- general
- cardiology
- neurology
- orthopedics
- oncology
- psychiatry
- pediatrics
- multispecialty

Hospital name: {hospital_name}

Return ONLY one word from the list.
"""

    try:
        client = _get_client()
        if not client:
            raise ValueError("GEMINI_API_KEY not configured")

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={"temperature": 0.1},
        )
        specialization = _normalize_specialty((response.text or "").strip())
    except Exception:
        specialization = "general"

    _specialization_cache[cache_key] = specialization
    return specialization
