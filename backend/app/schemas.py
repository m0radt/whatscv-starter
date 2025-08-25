from typing import List, Optional
from pydantic import BaseModel

class ExperienceIn(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    description: Optional[str] = None

class CandidateIn(BaseModel):
    phone: str | None = None
    raw_paragraph: str
    cv_text: str | None = None

class CandidateOut(BaseModel):
    id: int
    phone: str | None
    full_name: str | None
    education_institution: str | None
    education_level: str | None
    year_of_study: str | None
    location_city: str | None
    experiences: List[ExperienceIn] = []

    class Config:
        from_attributes = True