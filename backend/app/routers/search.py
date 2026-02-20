from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Candidate, Education
from ..schemas import CandidateSearchOut

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/search", response_model=CandidateSearchOut)
def search_candidates(
    skills: Optional[str] = None,
    education_level: Optional[str] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Candidate)
    if education_level:
        q = q.outerjoin(Education).filter(Education.degree.ilike(f"%{education_level}%"))
    if city:
        q = q.filter(Candidate.location_city.ilike(f"%{city}%"))

    results = q.distinct().all()

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

    return {"count": len(results), "items": results}
