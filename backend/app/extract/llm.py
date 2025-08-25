import os
import json
from typing import Any, Dict, Optional
import google.generativeai as genai

# --- JSON schema for structured output ---
SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "full_name": {"type": "string", "nullable": True},
        "id_number": {"type": "string", "nullable": True},
        "education_institution": {"type": "string", "nullable": True},
        "education_level": {"type": "string", "nullable": True},
        "year_of_study": {"type": "string", "nullable": True},
        "location_city": {"type": "string", "nullable": True},
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string", "nullable": True},
                    "title": {"type": "string", "nullable": True},
                    "start": {"type": "string", "nullable": True},
                    "end": {"type": "string", "nullable": True},
                    "description": {"type": "string", "nullable": True},
                },
                "additionalProperties": False,
            },
        },
    },
    "required": ["experiences"],
    "additionalProperties": False,
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
MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set. Edit your .env.")

genai.configure(api_key=API_KEY)
GENERATION_CONFIG = {
    "response_mime_type": "application/json",
    "response_schema": SCHEMA,
}


def extract_structured(paragraph: str, cv_text: Optional[str] = None) -> Dict[str, Any]:
    """Return a dict matching SCHEMA keys using Gemini structured output."""
    model = genai.GenerativeModel(MODEL, generation_config=GENERATION_CONFIG)
    resp = model.generate_content(_build_user_content(paragraph, cv_text))
    text = getattr(resp, "text", None) or "{}"
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"experiences": []}