from typing import List, Optional
from pydantic import BaseModel

class EducationIn(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    gpa: Optional[str] = None
    status: Optional[str] = None
    expected_graduation_date: Optional[str] = None


class ExperienceIn(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    dates: Optional[str] = None
    employment_status: Optional[str] = None
    description: Optional[str] = None


class CandidateIn(BaseModel):
    phone: str | None = None
    raw_paragraph: str
    cv_text: str | None = None


class CandidateOut(BaseModel):
    id: int
    phone: str | None
    email: str | None
    full_name: str | None
    location_city: str | None
    education: List[EducationIn] = []
    experiences: List[ExperienceIn] = []

    class Config:
        from_attributes = True
