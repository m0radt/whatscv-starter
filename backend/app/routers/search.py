from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Candidate, Experience

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/search")
def search_candidates(
    skills: Optional[str] = None,
    education_level: Optional[str] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Candidate)
    if education_level:
        q = q.filter(Candidate.education_level.ilike(f"%{education_level}%"))
    if city:
        q = q.filter(Candidate.location_city.ilike(f"%{city}%"))

    results = q.all()

    # Simple skills filter: check experiences text fields for keywords
    if skills:
        keys = [k.strip() for k in skills.split(",") if k.strip()]
        filtered = []
        for c in results:
            blob = (c.cv_text or "") + "\n" + (c.raw_paragraph or "")
            exp_concat = "\n".join((e.title or "") + " " + (e.description or "") for e in c.experiences)
            text = (blob + "\n" + exp_concat).lower()
            if all(k.lower() in text for k in keys):
                filtered.append(c)
        results = filtered

    return {
        "count": len(results),
        "items": [
            {
                "id": c.id,
                "full_name": c.full_name,
                "education": {
                    "institution": c.education_institution,
                    "level": c.education_level,
                    "year_of_study": c.year_of_study,
                },
                "city": c.location_city,
                "phone": c.phone,
            }
            for c in results
        ],
    }