import os
import json
from typing import Any, Dict, Optional
from google import genai

# --- JSON schema for structured output ---
SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "full_name": {"type": "string", "nullable": True},
        "email": {"type": "string", "nullable": True},
        "phone": {"type": "string", "nullable": True},
        "id_number": {"type": "string", "nullable": True},
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": "string", "nullable": True},
                    "degree": {"type": "string", "nullable": True},
                    "major": {"type": "string", "nullable": True},
                    "gpa": {"type": "string", "nullable": True},
                    "status": {"type": "string", "enum": ["graduated", "attending"], "nullable": True},
                    "expected_graduation_date": {"type": "string", "nullable": True},
                },
            },
        },
        "location_city": {"type": "string", "nullable": True},
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string", "nullable": True},
                    "organization": {"type": "string", "nullable": True},
                    "title": {"type": "string", "nullable": True},
                    "dates": {"type": "string", "nullable": True},
                    "employment_status": {"type": "string", "enum": ["working", "finished"], "nullable": True},
                    "description": {"type": "string", "nullable": True},
                },
            },
        },
    },
    "required": ["experiences", "education"],
}

SYSTEM = (
    "You are an expert HR parsing assistant. Extract structured JSON only. "
    "Do not invent facts. If a field is missing, set it to null."
)


def _build_user_content(paragraph: Optional[str], cv_text: Optional[str]) -> str:
    paragraph = (paragraph or "").strip()
    cv_text = (cv_text or "").strip()

    parts = [f"Paragraph:\n{paragraph}"]
    if cv_text:
        parts += ["", f"CV Text:\n{cv_text}"]  # blank line separator

    return "\n".join(parts)

# --- Configure Gemini ---
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set. Edit your .env.")

CLIENT = genai.Client(api_key=API_KEY)
GENERATION_CONFIG = {
    "response_mime_type": "application/json",
    "response_schema": SCHEMA,
}


def extract_structured(paragraph: str, cv_text: Optional[str] = None) -> Dict[str, Any]:
    """Return a dict matching SCHEMA keys using Gemini structured output."""
    try:
        resp = CLIENT.models.generate_content(
            model=MODEL,
            contents=f"{SYSTEM}\n\n{_build_user_content(paragraph, cv_text)}",
            config=GENERATION_CONFIG,
        )
    except Exception:
        return {"experiences": [], "education": []}

    text = getattr(resp, "text", None) or "{}"
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            experiences = data.setdefault("experiences", [])
            if isinstance(experiences, list):
                for exp in experiences:
                    if isinstance(exp, dict):
                        exp["company"] = exp.get("company") if exp.get("company") else exp.get("organization")
                        exp.pop("organization", None)
            data.setdefault("education", [])
            return data
        return {"experiences": [], "education": []}
    except json.JSONDecodeError:
        return {"experiences": [], "education": []}
