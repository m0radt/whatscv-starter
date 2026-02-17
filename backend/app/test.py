from backend.app.db import SessionLocal
from backend.app.models import Candidate
from backend.app.extract.llm import CLIENT, MODEL, SYSTEM, SCHEMA, _build_user_content
import json

db = SessionLocal()
c = db.query(Candidate).order_by(Candidate.id.desc()).first()
db.close()

print("candidate_id:", c.id)
print("cv_text_len:", len(c.cv_text or ""))

resp = CLIENT.models.generate_content(
    model=MODEL,
    contents=f"{SYSTEM}\n\n{_build_user_content(c.raw_paragraph or '', c.cv_text or '')}",
    config={
        "response_mime_type": "application/json",
        "response_schema": SCHEMA,
    },
)

text = getattr(resp, "text", "") or ""
print("\nRAW RESPONSE:\n", text)

try:
    data = json.loads(text)
    print("\nJSON OK. keys:", list(data.keys()) if isinstance(data, dict) else type(data))
except Exception as e:
    print("\nJSON ERROR:", type(e).__name__, str(e))
